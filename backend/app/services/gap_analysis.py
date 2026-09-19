from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.schemas.job import JobRequirements
from app.schemas.profile import MasterProfile

SYSTEM_PROMPT = """You write a prep plan for a candidate applying to a job, given their
missing required/preferred skills and any seniority gap. For each gap, classify it:
- "closeable": a specific tool, certification, or shallow-depth skill the candidate could
  plausibly learn or demonstrate before applying or interviewing. Give a concrete action.
- "structural": a gap that cannot realistically close on this timeline — a large
  years-of-experience or seniority gap, a fundamentally different domain. Say so plainly;
  do not invent a fast path to seniority. Give no action, just the honest reasoning.
Do not sugar-coat structural gaps to make the candidate feel better."""


class GapItem(BaseModel):
    requirement: str
    kind: Literal["closeable", "structural"]
    reasoning: str
    action: str | None = None


class PrepPlan(BaseModel):
    summary: str
    gaps: list[GapItem]


def generate(
    db: Session,
    *,
    profile: MasterProfile,
    job: JobRequirements,
    components: dict,
    gates: dict,
    user_id: str | None = None,
) -> PrepPlan:
    profile_skills = {s.canonical for s in profile.skills}
    missing_required = [s.canonical for s in job.skills if s.weight == "required" and s.canonical not in profile_skills]
    missing_preferred = [s.canonical for s in job.skills if s.weight == "preferred" and s.canonical not in profile_skills]

    prompt = (
        f"Job: {job.raw_title} ({job.seniority_level})\n"
        f"Candidate years of experience: {profile.total_years_experience}\n"
        f"Missing required skills: {missing_required}\n"
        f"Missing preferred skills: {missing_preferred}\n"
        f"Seniority fit component (0..1, asymmetric — low means under-qualified): {components.get('seniority_fit')}\n"
        f"Gate checks: {gates.get('checks')}\n"
    )

    return call_structured(
        db,
        node="gap_prep_plan",
        model="claude-opus-5",
        effort="high",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_schema=PrepPlan,
        user_id=user_id,
    )
