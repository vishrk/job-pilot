from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.llm.embeddings import embed
from app.models import Company, Job, JobRequirements as JobRequirementsRow, Match, Profile, User
from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile
from app.services import discovery, gap_analysis, score_explainer

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
        if not company:
            continue
        try:
            jobs = discovery.discover_jobs(db, company)
        except Exception as e:
            results.append({"company": company.name, "error": str(e)})
            continue

        for r in discovery.score_jobs_for_profile(
            db, jobs, user_id=profile_row.user_id, profile=profile, profile_vec=profile_vec
        ):
            results.append({**r, "company": company.name})

    results.sort(key=lambda r: (r.get("score") is None, -(r.get("score") or 0)))
    return results


@router.get("/matches/inbox")
def match_inbox(email: str, min_score: float | None = None, include_dismissed: bool = False, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=email).first()
    if not user:
        return []
    query = db.query(Match).filter_by(user_id=user.id)
    if not include_dismissed:
        query = query.filter_by(dismissed=False)
    if min_score is not None:
        query = query.filter(Match.score >= min_score)

    matches = query.all()
    results = []
    for m in matches:
        job_row = db.get(Job, m.job_id)
        company = db.get(Company, job_row.company_id)
        results.append(
            {
                "match_id": m.id,
                "job_id": m.job_id,
                "company": company.name,
                "title": job_row.title,
                "location": job_row.location,
                "score": m.score,
                "components": m.components_json,
                "gates": m.gates_json,
                "is_new": m.seen_at is None,
                "dismissed": m.dismissed,
            }
        )
        if m.seen_at is None:
            m.seen_at = datetime.now(timezone.utc)
    db.commit()

    results.sort(key=lambda r: (r.get("score") is None, -(r.get("score") or 0)))
    return results


@router.post("/matches/{match_id}/dismiss")
def dismiss_match(match_id: str, db: Session = Depends(get_db)):
    match_row = db.get(Match, match_id)
    if not match_row:
        raise HTTPException(404, "match not found")
    match_row.dismissed = True
    db.commit()
    return {"dismissed": match_id}


@router.get("/matches/{match_id}/prep-plan")
def prep_plan(match_id: str, db: Session = Depends(get_db)):
    match_row = db.get(Match, match_id)
    if not match_row:
        raise HTTPException(404, "match not found")
    if match_row.prep_plan_json:
        return match_row.prep_plan_json

    job_row = db.get(Job, match_row.job_id)
    req_row = db.get(JobRequirementsRow, job_row.jd_hash)
    profile_row = (
        db.query(Profile).filter_by(user_id=match_row.user_id).order_by(Profile.created_at.desc()).first()
    )
    if not req_row or not profile_row:
        raise HTTPException(400, "missing job requirements or profile for this match")

    plan = gap_analysis.generate(
        db,
        profile=MasterProfile.model_validate(profile_row.master_json),
        job=JobRequirements.model_validate(req_row.parsed_json),
        components=match_row.components_json,
        gates=match_row.gates_json,
        user_id=match_row.user_id,
    )
    match_row.prep_plan_json = plan.model_dump()
    db.commit()
    return match_row.prep_plan_json


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
