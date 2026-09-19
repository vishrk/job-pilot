import re

from sqlalchemy.orm import Session

from app.models import Job
from app.services.adapters.base import RawJob

_PUNCT = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    lowered = _PUNCT.sub(" ", title.lower())
    return _WS.sub(" ", lowered).strip()


def upsert_job(db: Session, *, company_id: str, ats_kind: str, raw_job: RawJob) -> Job:
    """One row per logical job. A second listing for the same
    (company, normalized_title, location) — whether a re-fetch of the same board or
    a cross-post on a different ATS — updates the existing row instead of creating
    a duplicate."""
    normalized = normalize_title(raw_job.title)

    existing = (
        db.query(Job)
        .filter_by(company_id=company_id, normalized_title=normalized, location=raw_job.location)
        .first()
    )
    if existing:
        existing.jd_hash = raw_job.jd_hash
        existing.raw = raw_job.raw
        db.commit()
        return existing

    job = Job(
        company_id=company_id,
        ats_kind=ats_kind,
        ats_job_id=raw_job.ats_job_id,
        title=raw_job.title,
        normalized_title=normalized,
        location=raw_job.location,
        jd_hash=raw_job.jd_hash,
        raw=raw_job.raw,
    )
    db.add(job)
    db.commit()
    return job
