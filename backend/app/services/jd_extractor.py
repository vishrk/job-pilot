from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.llm.embeddings import embed
from app.models import JobRequirements as JobRequirementsRow
from app.schemas.job import JobRequirements, SkillRequirement
from app.services.adapters.base import RawJob
from app.services.skill_normalize import normalize_skill

SYSTEM_PROMPT = """You extract structured hiring requirements from a job description.
Identify: normalized seniority level, industry/domain tags, required vs preferred skills
(as they appear in the text — do not normalize spelling/casing yourself), and any hard
gates: work authorization constraints, onsite/remote/hybrid policy, required locations,
required license or clearance, and minimum years of experience. Leave a gate empty/null
if the JD does not state it — do not infer gates that aren't explicit."""


class _ExtractedRequirements(JobRequirements):
    """LLM output shape — jd_hash/extracted_at are filled in by us, not the model."""

    jd_hash: str = ""
    extracted_at: str = ""


def get_or_create(db: Session, job: RawJob, user_id: str | None = None) -> JobRequirements:
    cached = db.get(JobRequirementsRow, job.jd_hash)
    if cached:
        return JobRequirements.model_validate(cached.parsed_json)

    extracted = call_structured(
        db,
        node="jd_extractor",
        model="claude-sonnet-5",
        effort="low",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Title: {job.title}\n\n{job.jd_text}"}],
        output_schema=_ExtractedRequirements,
        user_id=user_id,
    )

    normalized_skills: list[SkillRequirement] = []
    for skill in extracted.skills:
        canonical = normalize_skill(skill.canonical, db)
        if canonical:
            normalized_skills.append(SkillRequirement(canonical=canonical, weight=skill.weight))

    result = JobRequirements(
        jd_hash=job.jd_hash,
        title_normalized=extracted.title_normalized,
        seniority_level=extracted.seniority_level,
        domain_tags=extracted.domain_tags,
        skills=normalized_skills,
        gates=extracted.gates,
        raw_title=job.title,
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )

    [embedding] = embed(
        [f"{result.title_normalized} — {', '.join(result.domain_tags)}"], input_type="document"
    )

    db.add(
        JobRequirementsRow(
            jd_hash=job.jd_hash,
            parsed_json=result.model_dump(),
            embedding=embedding,
        )
    )
    db.commit()
    return result
