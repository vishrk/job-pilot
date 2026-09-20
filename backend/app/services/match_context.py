from sqlalchemy.orm import Session

from app.models import Job, JobRequirements as JobRequirementsRow, Match, Profile
from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile


def load(db: Session, match_id: str) -> tuple[Match, MasterProfile, JobRequirements] | None:
    match_row = db.get(Match, match_id)
    if not match_row:
        return None
    job_row = db.get(Job, match_row.job_id)
    req_row = db.get(JobRequirementsRow, job_row.jd_hash)
    profile_row = (
        db.query(Profile).filter_by(user_id=match_row.user_id).order_by(Profile.created_at.desc()).first()
    )
    if not req_row or not profile_row:
        return None
    profile = MasterProfile.model_validate(profile_row.master_json)
    job = JobRequirements.model_validate(req_row.parsed_json)
    return match_row, profile, job
