import hashlib
import html
from html.parser import HTMLParser

import httpx

from app.services.adapters.base import RawJob

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data):
        self.chunks.append(data)


def _strip_html(raw_content: str) -> str:
    unescaped = html.unescape(raw_content)
    parser = _TextExtractor()
    parser.feed(unescaped)
    text = " ".join(chunk.strip() for chunk in parser.chunks if chunk.strip())
    return text


def list_jobs(board_token: str) -> list[RawJob]:
    """Greenhouse job board API: boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"""
    resp = httpx.get(BASE_URL.format(token=board_token), params={"content": "true"}, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    jobs = []
    for job in payload.get("jobs", []):
        jd_text = _strip_html(job.get("content") or "")
        jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
        jobs.append(
            RawJob(
                ats_job_id=str(job["id"]),
                title=job["title"],
                location=(job.get("location") or {}).get("name"),
                jd_text=jd_text,
                jd_hash=jd_hash,
                raw=job,
            )
        )
    return jobs
