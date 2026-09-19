import hashlib

import httpx

from app.services.adapters.base import RawJob

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{name}"


def list_jobs(board_token: str) -> list[RawJob]:
    """Ashby job board API: api.ashbyhq.com/posting-api/job-board/{name}
    descriptionPlain is already plain text — no HTML stripping needed."""
    resp = httpx.get(BASE_URL.format(name=board_token), timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    jobs = []
    for job in payload.get("jobs", []):
        jd_text = job.get("descriptionPlain") or ""
        jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
        jobs.append(
            RawJob(
                ats_job_id=job["id"],
                title=job["title"],
                location=job.get("location"),
                jd_text=jd_text,
                jd_hash=jd_hash,
                raw=job,
            )
        )
    return jobs
