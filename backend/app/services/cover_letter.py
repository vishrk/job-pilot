"""Cover letter generation, same provenance discipline as the resume (§2.4): each
paragraph must cite the source_bullet_id(s) its specifics come from. Citations to
unknown bullets are stripped before render; the verifier pass (services/verifier.py)
is the real backstop against fabricated prose, since free text can't be truncated
bullet-by-bullet the way a resume can.
"""

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.schemas.document import CoverLetter, CoverLetterParagraph
from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile

SYSTEM_PROMPT = """You write a 3-paragraph cover letter for a candidate applying to a job.
Use only facts from the candidate's bullets — you're given each with its id. For every
paragraph, list the source_bullet_id(s) whose facts you drew on (empty list only for the
opening/closing paragraphs, which should not contain specific claims). Do not invent
achievements, numbers, or scope not present in the cited bullets."""


class _DraftParagraph(BaseModel):
    text: str
    source_bullet_ids: list[str] = []


class _DraftLetter(BaseModel):
    greeting: str
    paragraphs: list[_DraftParagraph]
    closing: str


def strip_unknown_citations(draft: _DraftLetter, profile: MasterProfile) -> dict:
    """Pure function — no LLM/DB — so it's directly testable against adversarial
    drafts. Drops any citation to a bullet id that isn't in the master profile."""
    valid_ids = {b.id for b in profile.bullets}

    rejected = []
    paragraphs = []
    for p in draft.paragraphs:
        kept_ids = [bid for bid in p.source_bullet_ids if bid in valid_ids]
        dropped_ids = [bid for bid in p.source_bullet_ids if bid not in valid_ids]
        for bid in dropped_ids:
            rejected.append({"source_bullet_id": bid, "text": p.text, "reason": "unknown source_bullet_id — not in master profile"})
        paragraphs.append(CoverLetterParagraph(text=p.text, source_bullet_ids=kept_ids))

    letter = CoverLetter(greeting=draft.greeting, paragraphs=paragraphs, closing=draft.closing)
    # each paragraph already carries its own source_bullet_ids (one-to-many); no
    # separate provenance_map needed the way the resume's output-bullet-id map is.
    return {"content": letter.model_dump(), "provenance_map": {}, "rejected_bullets": rejected}


def generate_cover_letter(db: Session, *, profile: MasterProfile, job: JobRequirements, user_id: str | None = None, notes: str = "") -> dict:
    bullet_lines = "\n".join(f"({b.id}) {b.text}" for b in profile.bullets)
    prompt = f"Job: {job.raw_title} at seniority {job.seniority_level}\n\nCandidate bullets:\n{bullet_lines}"
    if notes:
        prompt += f"\n\nUser feedback on the previous draft, apply it: {notes}"

    draft = call_structured(
        db,
        node="cover_letter",
        model="claude-opus-5",
        effort="high",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_schema=_DraftLetter,
        user_id=user_id,
    )
    return strip_unknown_citations(draft, profile)
