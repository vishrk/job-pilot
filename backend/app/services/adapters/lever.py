import hashlib
import html
from html.parser import HTMLParser

import httpx

from app.services.adapters.base import RawJob

BASE_URL = "https://api.lever.co/v0/postings/{token}"


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data):
        self.chunks.append(data)


def _strip_html(raw: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(raw))
    return " ".join(chunk.strip() for chunk in parser.chunks if chunk.strip())


def list_jobs(board_token: str) -> list[RawJob]:
    """Lever postings API: api.lever.co/v0/postings/{token}?mode=json"""
    resp = httpx.get(BASE_URL.format(token=board_token), params={"mode": "json"}, timeout=30)
    resp.raise_for_status()
    postings = resp.json()

    jobs = []
    for job in postings:
        jd_text = " ".join(
            filter(
                None,
                [
                    _strip_html(job.get("descriptionPlain") or job.get("description") or ""),
                    _strip_html(job.get("additionalPlain") or job.get("additional") or ""),
                ],
            )
        )
        jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
        jobs.append(
            RawJob(
                ats_job_id=job["id"],
                title=job["text"],
                location=(job.get("categories") or {}).get("location"),
                jd_text=jd_text,
                jd_hash=jd_hash,
                raw=job,
            )
        )
    return jobs
