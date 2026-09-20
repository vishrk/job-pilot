"""Answer library (§7 Phase 3 — "saves more user time than resume tailoring, treat
it as first-class"). A screening question is fingerprinted on its normalized text
and reused across every employer that asks a matching question. A cache miss falls
through to the essay answerer; the draft is always returned for the user to edit,
never auto-filled silently (enforced by the extension's review panel, not here).
"""

import re

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.models import Answer
from app.schemas.profile import MasterProfile

SYSTEM_PROMPT = """You draft a short answer to a job application screening question,
grounded only in the candidate's profile. For factual questions (years of experience
with a tool, work authorization, notice period) answer directly and concisely. For
open-ended questions ("why this company", "describe a challenge") write 2-4 sentences
using only real experience from the profile — never invent an example."""

_PUNCT = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")


class _DraftAnswer(BaseModel):
    answer: str


def normalize_question(text: str) -> str:
    lowered = _PUNCT.sub(" ", text.lower())
    return _WS.sub(" ", lowered).strip()


def _profile_text(profile: MasterProfile) -> str:
    lines = [f"Total years of experience: {profile.total_years_experience}"]
    if profile.experience:
        lines.append(f"Current role: {profile.experience[0].title} at {profile.experience[0].company}")
    lines.append(f"Work authorization: {profile.work_authorization.status}")
    lines.append("Skills: " + ", ".join(s.canonical for s in profile.skills))
    for b in profile.bullets:
        lines.append(f"- {b.text}")
    return "\n".join(lines)


def resolve_answer(db: Session, *, user_id: str, question_text: str, profile: MasterProfile) -> dict:
    fingerprint = normalize_question(question_text)
    cached = db.query(Answer).filter_by(user_id=user_id, question_fingerprint=fingerprint).first()
    if cached:
        return {"answer": cached.answer, "from_cache": True}

    draft = call_structured(
        db,
        node="essay_answerer",
        model="claude-opus-5",
        effort="high",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Question: {question_text}\n\nCandidate profile:\n{_profile_text(profile)}"}],
        output_schema=_DraftAnswer,
        user_id=user_id,
    )

    db.add(Answer(user_id=user_id, question_fingerprint=fingerprint, question_text=question_text, answer=draft.answer))
    db.commit()
    return {"answer": draft.answer, "from_cache": False}
