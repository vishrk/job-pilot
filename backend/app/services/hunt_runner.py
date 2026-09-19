"""Scheduled Hunt execution on the Postgres SKIP LOCKED queue (§2.6 — Postgres is
the queue, no Redis/Kafka). One row = one hunt; FOR UPDATE SKIP LOCKED lets
multiple worker processes poll the same table without double-processing a hunt.

# ponytail: discovery.discover_jobs / score_jobs_for_profile commit as they go,
# so the row lock claimed below is only held until their first inner commit, not
# for the whole run. Fine for a single worker loop (our Phase 1 deployment target,
# §2.6); revisit with per-hunt advisory locks if a second worker process is added.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.llm.embeddings import embed
from app.models import Company, Hunt, Profile
from app.schemas.profile import MasterProfile
from app.services import discovery

logger = logging.getLogger(__name__)

SCHEDULE_INTERVALS = {"hourly": timedelta(hours=1), "daily": timedelta(days=1)}


def _matches_filters(job_title: str, job_location: str | None, hunt: Hunt) -> bool:
    if hunt.roles and not any(role.lower() in job_title.lower() for role in hunt.roles):
        return False
    if hunt.locations and job_location:
        if not any(loc.lower() in job_location.lower() for loc in hunt.locations):
            return False
    return True


def _profile_text(profile: MasterProfile) -> str:
    title = profile.experience[0].title if profile.experience else ""
    domains = ", ".join(f"{e.title} at {e.company}" for e in profile.experience)
    return f"{title} — {domains}"


def run_hunt(db: Session, hunt: Hunt) -> list[dict]:
    profile_row = (
        db.query(Profile).filter_by(user_id=hunt.user_id).order_by(Profile.created_at.desc()).first()
    )
    if not profile_row:
        logger.error("hunt %s has no profile for user %s, skipping", hunt.id, hunt.user_id)
        return []
    profile = MasterProfile.model_validate(profile_row.master_json)
    [profile_vec] = embed([_profile_text(profile)], input_type="query")

    all_results = []
    for company_id in hunt.company_ids:
        company = db.get(Company, company_id)
        if not company:
            continue
        try:
            jobs = discovery.discover_jobs(db, company)
        except Exception:
            logger.exception("adapter failed for company %s on hunt %s", company.name, hunt.id)
            continue

        filtered = [j for j in jobs if _matches_filters(j.title, j.location, hunt)]
        results = discovery.score_jobs_for_profile(
            db, filtered, user_id=hunt.user_id, profile=profile, profile_vec=profile_vec
        )
        for r in results:
            all_results.append({**r, "company": company.name})

    return all_results


def run_due_hunts(db: Session, limit: int = 10) -> int:
    now = datetime.now(timezone.utc)
    due = (
        db.query(Hunt)
        .filter(Hunt.next_run_at <= now)
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    for hunt in due:
        try:
            run_hunt(db, hunt)
        except Exception:
            logger.exception("hunt %s failed entirely", hunt.id)
        hunt.last_run_at = now
        hunt.next_run_at = now + SCHEDULE_INTERVALS.get(hunt.schedule, timedelta(days=1))
        db.commit()
    return len(due)
