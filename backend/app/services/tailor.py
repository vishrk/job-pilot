"""Resume tailoring, constrained per §2.4: every bullet traces to a source_bullet_id
in the master profile (no source id -> rejected before the user ever sees it), and
the skills section is a Python-computed subset of master skills — the model never
writes that field.
"""

import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.schemas.document import SkillEntryOut, TailoredBullet, TailoredResume, TailoredSection
from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile

SYSTEM_PROMPT = """You tailor a resume for a specific job by selecting and lightly rewording
(tightening phrasing, leading with the most job-relevant detail) a subset of the candidate's
EXISTING bullets. You are given each bullet with its id. For every bullet you include, return
that exact source_bullet_id. Do not invent bullets, numbers, tools, or scope that isn't in the
source bullet's text — you may cut words but never add a fact. Prioritize bullets whose content
matches the job's required skills and seniority level; you may omit irrelevant bullets. Write a
2-3 sentence professional summary using only facts present in the candidate's experience."""


class _DraftBullet(BaseModel):
    source_bullet_id: str
    text: str


class _DraftSection(BaseModel):
    experience_id: str
    bullets: list[_DraftBullet]


class _TailorDraft(BaseModel):
    summary: str
    sections: list[_DraftSection]


def _bullet_prompt(profile: MasterProfile) -> str:
    lines = []
    for exp in profile.experience:
        lines.append(f"\n[{exp.id}] {exp.title} at {exp.company} ({exp.start_date}–{exp.end_date or 'present'})")
        for b in profile.bullets:
            if b.experience_id == exp.id:
                lines.append(f"  ({b.id}) {b.text}")
    return "\n".join(lines)


def _ranked_skills(profile: MasterProfile, job: JobRequirements) -> list[SkillEntryOut]:
    job_skill_names = {s.canonical for s in job.skills}
    matched = [s for s in profile.skills if s.canonical in job_skill_names]
    rest = [s for s in profile.skills if s.canonical not in job_skill_names]
    return [SkillEntryOut(canonical=s.canonical) for s in (matched + rest)]


def enforce_provenance(draft: _TailorDraft, profile: MasterProfile, job: JobRequirements) -> dict:
    """The anti-fabrication gate (§2.4.1): every kept bullet must cite a
    source_bullet_id that (a) exists in the master profile and (b) belongs to the
    experience entry the model claims it's under. Pure function — no LLM/DB — so
    it's directly testable against adversarial drafts, not just trusted output."""
    valid_bullets = {b.id: b.experience_id for b in profile.bullets}

    sections: list[TailoredSection] = []
    provenance_map: dict[str, str] = {}
    rejected: list[dict] = []

    for draft_section in draft.sections:
        kept_bullets = []
        for b in draft_section.bullets:
            true_experience_id = valid_bullets.get(b.source_bullet_id)
            if true_experience_id is None:
                rejected.append({"source_bullet_id": b.source_bullet_id, "text": b.text, "reason": "unknown source_bullet_id — not in master profile"})
                continue
            if true_experience_id != draft_section.experience_id:
                rejected.append({"source_bullet_id": b.source_bullet_id, "text": b.text, "reason": "source bullet belongs to a different experience entry"})
                continue
            output_id = f"obl_{uuid.uuid4().hex[:8]}"
            kept_bullets.append(TailoredBullet(id=output_id, source_bullet_id=b.source_bullet_id, text=b.text))
            provenance_map[output_id] = b.source_bullet_id
        if kept_bullets:
            sections.append(TailoredSection(experience_id=draft_section.experience_id, bullets=kept_bullets))

    resume = TailoredResume(summary=draft.summary, sections=sections, skills=_ranked_skills(profile, job))

    return {
        "content": resume.model_dump(),
        "provenance_map": provenance_map,
        "rejected_bullets": rejected,
    }


def tailor_resume(db: Session, *, profile: MasterProfile, job: JobRequirements, user_id: str | None = None, notes: str = "") -> dict:
    prompt = f"Job: {job.raw_title} ({job.seniority_level})\nRequired skills: {[s.canonical for s in job.skills if s.weight == 'required']}\n\nCandidate bullets:\n{_bullet_prompt(profile)}"
    if notes:
        prompt += f"\n\nUser feedback on the previous draft, apply it: {notes}"

    draft = call_structured(
        db,
        node="tailor",
        model="claude-opus-5",
        effort="xhigh",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_schema=_TailorDraft,
        user_id=user_id,
    )
    return enforce_provenance(draft, profile, job)
