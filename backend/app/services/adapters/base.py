from typing import Protocol

from pydantic import BaseModel


class RawJob(BaseModel):
    ats_job_id: str
    title: str
    location: str | None
    jd_text: str          # plain text, HTML stripped
    jd_hash: str           # sha256 of jd_text, used as the global cache key
    raw: dict               # untouched original payload, kept for debugging/replay


class AtsAdapter(Protocol):
    def list_jobs(self, board_token: str) -> list[RawJob]: ...
