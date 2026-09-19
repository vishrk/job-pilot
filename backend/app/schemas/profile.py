from typing import Literal

from pydantic import BaseModel


class ContactInfo(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None


class WorkAuthorization(BaseModel):
    status: Literal[
        "citizen", "permanent_resident", "visa_holder", "needs_sponsorship", "unspecified"
    ]
    visa_type: str | None = None


class ProfileBullet(BaseModel):
    id: str
    experience_id: str | None = None
    text: str
    tags: list[str] = []


class ExperienceEntry(BaseModel):
    id: str
    company: str
    title: str
    start_date: str  # "YYYY-MM"
    end_date: str | None = None
    location: str | None = None


class EducationEntry(BaseModel):
    id: str
    institution: str
    degree: str | None = None
    field: str | None = None
    end_date: str | None = None


class SkillEntry(BaseModel):
    canonical: str
    last_used: str | None = None  # "YYYY-MM"
    months_experience: int | None = None


class MasterProfile(BaseModel):
    version: int = 1
    contact: ContactInfo
    work_authorization: WorkAuthorization
    experience: list[ExperienceEntry] = []
    education: list[EducationEntry] = []
    bullets: list[ProfileBullet] = []
    skills: list[SkillEntry] = []
    total_years_experience: float = 0.0
