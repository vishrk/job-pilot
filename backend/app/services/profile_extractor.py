import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.client import call_structured
from app.schemas.profile import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    MasterProfile,
    ProfileBullet,
    SkillEntry,
    WorkAuthorization,
)
from app.services.skill_normalize import normalize_skill

SYSTEM_PROMPT = """You extract a structured profile from a resume. Every bullet point under
a role becomes one entry in that role's bullets list — copy the wording faithfully, do not
paraphrase or invent. Dates are month precision ("YYYY-MM"); if only a year is given, use
"YYYY-01". work_authorization.status should be "unspecified" unless the resume states it
explicitly. total_years_experience is computed from the experience date ranges."""


class _ExtractedBullet(BaseModel):
    text: str
    tags: list[str] = []


class _ExtractedExperience(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: str | None = None
    location: str | None = None
    bullets: list[_ExtractedBullet] = []


class _ExtractedEducation(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    end_date: str | None = None


class _ExtractedSkill(BaseModel):
    canonical: str
    last_used: str | None = None
    months_experience: int | None = None


class _ExtractedProfile(BaseModel):
    contact: ContactInfo
    work_authorization: WorkAuthorization
    experience: list[_ExtractedExperience] = []
    education: list[_ExtractedEducation] = []
    summary_bullets: list[_ExtractedBullet] = []  # bullets not tied to a role
    skills: list[_ExtractedSkill] = []
    total_years_experience: float = 0.0


def extract(db: Session, resume_text: str, user_id: str | None = None) -> MasterProfile:
    extracted = call_structured(
        db,
        node="profile_extractor",
        model="claude-opus-5",
        effort="high",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": resume_text}],
        output_schema=_ExtractedProfile,
        user_id=user_id,
    )

    experience: list[ExperienceEntry] = []
    bullets: list[ProfileBullet] = []
    for i, exp in enumerate(extracted.experience, start=1):
        exp_id = f"exp_{i:02d}"
        experience.append(
            ExperienceEntry(
                id=exp_id,
                company=exp.company,
                title=exp.title,
                start_date=exp.start_date,
                end_date=exp.end_date,
                location=exp.location,
            )
        )
        for b in exp.bullets:
            bullets.append(
                ProfileBullet(id=f"blt_{uuid.uuid4().hex[:8]}", experience_id=exp_id, text=b.text, tags=b.tags)
            )
    for b in extracted.summary_bullets:
        bullets.append(
            ProfileBullet(id=f"blt_{uuid.uuid4().hex[:8]}", experience_id=None, text=b.text, tags=b.tags)
        )

    education = [
        EducationEntry(id=f"edu_{i:02d}", institution=e.institution, degree=e.degree, field=e.field, end_date=e.end_date)
        for i, e in enumerate(extracted.education, start=1)
    ]

    skills: list[SkillEntry] = []
    seen_canonical = set()
    for s in extracted.skills:
        canonical = normalize_skill(s.canonical, db)
        if canonical and canonical not in seen_canonical:
            seen_canonical.add(canonical)
            skills.append(SkillEntry(canonical=canonical, last_used=s.last_used, months_experience=s.months_experience))

    return MasterProfile(
        contact=extracted.contact,
        work_authorization=extracted.work_authorization,
        experience=experience,
        education=education,
        bullets=bullets,
        skills=skills,
        total_years_experience=extracted.total_years_experience,
    )
