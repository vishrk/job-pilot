from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.llm.embeddings import embed
from app.models import AtsAccount, Company, Job, JobRequirements as JobRequirementsRow, Match, Profile
from app.schemas.profile import MasterProfile
from app.services import score_explainer
from app.services import scorer
from app.services.adapters import greenhouse
from app.services.jd_extractor import get_or_create as get_or_create_job_requirements

router = APIRouter()


class MatchRequest(BaseModel):
    profile_id: str
    company_ids: list[str]


def _profile_text(profile: MasterProfile) -> str:
    title = profile.experience[0].title if profile.experience else ""
    domains = ", ".join(f"{e.title} at {e.company}" for e in profile.experience)
    return f"{title} — {domains}"


@router.post("/matches")
def compute_matches(req: MatchRequest, db: Session = Depends(get_db)):
    profile_row = db.get(Profile, req.profile_id)
    if not profile_row:
        raise HTTPException(404, "profile not found")
    profile = MasterProfile.model_validate(profile_row.master_json)

    [profile_vec] = embed([_profile_text(profile)], input_type="query")

    results = []
    for company_id in req.company_ids:
        company = db.get(Company, company_id)
        ats_account = (
            db.query(AtsAccount).filter_by(company_id=company_id, ats_kind="greenhouse").first()
        )
        if not company or not ats_account:
            continue

        try:
            raw_jobs = greenhouse.list_jobs(ats_account.board_token)
        except Exception as e:
            results.append({"company": company.name, "error": str(e)})
            continue

        for raw_job in raw_jobs:
            job_row = (
                db.query(Job).filter_by(company_id=company_id, ats_job_id=raw_job.ats_job_id).first()
            )
            if not job_row:
                job_row = Job(
                    company_id=company_id,
                    ats_job_id=raw_job.ats_job_id,
                    title=raw_job.title,
                    location=raw_job.location,
                    jd_hash=raw_job.jd_hash,
                    raw=raw_job.raw,
                )
                db.add(job_row)
                db.commit()

            requirements = get_or_create_job_requirements(db, raw_job, user_id=profile_row.user_id)

            job_requirements_row = db.get(JobRequirementsRow, raw_job.jd_hash)
            job_vec = job_requirements_row.embedding if job_requirements_row else None
            # ponytail: one combined title+domain embedding per side, reused for both
            # seniority_fit's title term and domain_fit — a second, title-only embedding
            # would sharpen seniority_fit but isn't worth a second Voyage call per job yet.
            embeddings_pair = (profile_vec, list(job_vec)) if job_vec is not None else None

            outcome = scorer.score(
                profile,
                requirements,
                title_embeddings=embeddings_pair,
                domain_embeddings=embeddings_pair,
            )

            match_row = db.query(Match).filter_by(user_id=profile_row.user_id, job_id=job_row.id).first()
            if not match_row:
                match_row = Match(user_id=profile_row.user_id, job_id=job_row.id)
                db.add(match_row)
            match_row.score = outcome["score"]
            match_row.components_json = outcome["components"]
            match_row.gates_json = outcome["gates"]
            db.commit()

            results.append(
                {
                    "match_id": match_row.id,
                    "job_id": job_row.id,
                    "company": company.name,
                    "title": raw_job.title,
                    "location": raw_job.location,
                    "score": outcome["score"],
                    "components": outcome["components"],
                    "gates": outcome["gates"],
                }
            )

    results.sort(key=lambda r: (r.get("score") is None, -(r.get("score") or 0)))
    return results


@router.get("/matches/{match_id}/explain")
def explain_match(match_id: str, db: Session = Depends(get_db)):
    match_row = db.get(Match, match_id)
    if not match_row:
        raise HTTPException(404, "match not found")
    job_row = db.get(Job, match_row.job_id)
    explanation = score_explainer.explain(
        db,
        job_title=job_row.title,
        score=match_row.score,
        components=match_row.components_json,
        gates=match_row.gates_json,
        user_id=match_row.user_id,
    )
    return explanation.model_dump()
