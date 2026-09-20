"""Entailment check on every factual claim in a generated document, against the
master profile. Unsupported claims are returned, not dropped — the UI flags them
inline and the user decides (§2.4.3)."""

from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.schemas.document import VerifyReport
from app.schemas.profile import MasterProfile

SYSTEM_PROMPT = """You verify a generated job-application document against a candidate's
master profile. First extract every factual claim from the document — numbers, dates,
job titles, tools/technologies, and scope statements (team size, budget, users served,
etc). Then, for each claim, decide if the master profile entails it: supported=true only
if the profile states that fact or a strict superset of it; supported=false if the profile
doesn't mention it, contradicts it, or only loosely resembles it. Be strict — a similar
sounding claim is not the same claim."""


def _profile_text(profile: MasterProfile) -> str:
    lines = [f"Total years of experience: {profile.total_years_experience}"]
    for exp in profile.experience:
        lines.append(f"{exp.title} at {exp.company} ({exp.start_date}–{exp.end_date or 'present'})")
    for b in profile.bullets:
        lines.append(f"- {b.text}")
    lines.append("Skills: " + ", ".join(s.canonical for s in profile.skills))
    return "\n".join(lines)


def verify(db: Session, *, document_text: str, profile: MasterProfile, user_id: str | None = None) -> VerifyReport:
    prompt = f"MASTER PROFILE:\n{_profile_text(profile)}\n\nDOCUMENT TO VERIFY:\n{document_text}"
    return call_structured(
        db,
        node="verifier",
        model="claude-sonnet-5",
        effort="medium",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_schema=VerifyReport,
        user_id=user_id,
    )


def resume_text(content: dict) -> str:
    parts = [content["summary"]]
    for section in content["sections"]:
        for bullet in section["bullets"]:
            parts.append(bullet["text"])
    return "\n".join(parts)


def cover_letter_text(content: dict) -> str:
    parts = [content["greeting"], *[p["text"] for p in content["paragraphs"]], content["closing"]]
    return "\n".join(parts)
