"""Company-level job discovery (global, no user) and per-profile scoring
(per-user). Shared by the ad hoc /matches endpoint and the Hunt runner so both
go through the same dedup + global-cache path (§2.5).
"""

from sqlalchemy.orm import Session

from app.models import AtsAccount, Company, Job, JobRequirements as JobRequirementsRow, Match
from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile
from app.services import job_dedup, scorer
from app.services.adapters import ADAPTERS
from app.services.jd_extractor import get_or_create as get_or_create_job_requirements


def discover_jobs(db: Session, company: Company) -> list[Job]:
    """Fetch a company's open roles from its detected ATS, dedup, and ensure each
    has parsed JobRequirements. Raises on adapter failure — caller decides whether
    that should fail the whole run or just be logged and skipped."""
    ats_account = db.query(AtsAccount).filter_by(company_id=company.id).first()
    if not ats_account:
        raise ValueError(f"no ATS detected for company {company.name}")

    list_jobs = ADAPTERS[ats_account.ats_kind]
    raw_jobs = list_jobs(ats_account.board_token)

    jobs = []
    for raw_job in raw_jobs:
        job_row = job_dedup.upsert_job(db, company_id=company.id, ats_kind=ats_account.ats_kind, raw_job=raw_job)
        get_or_create_job_requirements(db, raw_job)  # global cache by jd_hash, parsed once ever
        jobs.append(job_row)
    return jobs


def score_jobs_for_profile(
    db: Session,
    jobs: list[Job],
    *,
    user_id: str,
    profile: MasterProfile,
    profile_vec: list[float],
) -> list[dict]:
    results = []
    for job_row in jobs:
        req_row = db.get(JobRequirementsRow, job_row.jd_hash)
        if not req_row:
            continue
        requirements = JobRequirements.model_validate(req_row.parsed_json)
        job_vec = req_row.embedding
        # ponytail: one combined title+domain embedding per side, reused for both
        # seniority_fit's title term and domain_fit — a second, title-only embedding
        # would sharpen seniority_fit but isn't worth a second Voyage call per job yet.
        embeddings_pair = (profile_vec, list(job_vec)) if job_vec is not None else None

        outcome = scorer.score(
            profile, requirements, title_embeddings=embeddings_pair, domain_embeddings=embeddings_pair
        )

        match_row = db.query(Match).filter_by(user_id=user_id, job_id=job_row.id).first()
        is_new = match_row is None
        if not match_row:
            match_row = Match(user_id=user_id, job_id=job_row.id)
            db.add(match_row)
        match_row.score = outcome["score"]
        match_row.components_json = outcome["components"]
        match_row.gates_json = outcome["gates"]
        db.commit()

        results.append(
            {
                "match_id": match_row.id,
                "job_id": job_row.id,
                "title": job_row.title,
                "location": job_row.location,
                "score": outcome["score"],
                "components": outcome["components"],
                "gates": outcome["gates"],
                "is_new": is_new,
            }
        )
    return results
