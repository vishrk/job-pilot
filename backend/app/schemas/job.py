from typing import Literal

from pydantic import BaseModel


class SkillRequirement(BaseModel):
    canonical: str
    weight: Literal["required", "preferred"]


class HardGates(BaseModel):
    work_authorization: list[str] | None = None
    onsite_policy: Literal["remote", "hybrid", "onsite", "unspecified"] = "unspecified"
    locations: list[str] | None = None
    required_license: str | None = None
    required_clearance: str | None = None
    min_years_experience: float | None = None


class JobRequirements(BaseModel):
    jd_hash: str
    title_normalized: str
    seniority_level: Literal[
        "intern", "junior", "mid", "senior", "staff", "principal", "exec"
    ]
    domain_tags: list[str] = []
    skills: list[SkillRequirement] = []
    gates: HardGates
    raw_title: str
    extracted_at: str
