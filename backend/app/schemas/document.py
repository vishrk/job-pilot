from typing import Literal

from pydantic import BaseModel


class TailoredBullet(BaseModel):
    id: str  # output bullet id, assigned in code — what the diff/approval UI operates on
    source_bullet_id: str
    text: str


class TailoredSection(BaseModel):
    experience_id: str
    bullets: list[TailoredBullet]


class SkillEntryOut(BaseModel):
    canonical: str


class TailoredResume(BaseModel):
    summary: str
    sections: list[TailoredSection]
    skills: list[SkillEntryOut]  # always computed in Python — see services/tailor.py


class CoverLetterParagraph(BaseModel):
    text: str
    source_bullet_ids: list[str]  # bullets this paragraph draws its specifics from


class CoverLetter(BaseModel):
    greeting: str
    paragraphs: list[CoverLetterParagraph]
    closing: str


class VerifiedClaim(BaseModel):
    claim: str
    supported: bool
    reasoning: str


class VerifyReport(BaseModel):
    claims: list[VerifiedClaim]

    @property
    def unsupported(self) -> list[VerifiedClaim]:
        return [c for c in self.claims if not c.supported]


class DocumentOut(BaseModel):
    id: str
    match_id: str
    kind: Literal["resume", "cover_letter"]
    version: int
    content: dict
    provenance_map: dict[str, str]
    verify_report: VerifyReport | None
    rejected_bullets: list[dict]
    status: Literal["draft", "approved"]
