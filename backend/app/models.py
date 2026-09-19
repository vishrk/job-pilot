import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

EMBEDDING_DIM = 512


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    master_json: Mapped[dict] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    bullets: Mapped[list["ProfileBullet"]] = relationship(back_populates="profile")


class ProfileBullet(Base):
    __tablename__ = "profile_bullets"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # stable across profile versions
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    experience_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(String)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)

    profile: Mapped[Profile] = relationship(back_populates="bullets")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)


class AtsAccount(Base):
    __tablename__ = "ats_accounts"
    __table_args__ = (UniqueConstraint("company_id", "ats_kind"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    ats_kind: Mapped[str] = mapped_column(String)  # "greenhouse", "lever", "ashby", "workday"
    board_token: Mapped[str] = mapped_column(String)


class Job(Base):
    """Global: parsed/discovered exactly once, shared across all users."""

    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("company_id", "ats_job_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    ats_job_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    jd_hash: Mapped[str] = mapped_column(String, index=True)
    raw: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class JobRequirements(Base):
    """Global: keyed by jd_hash, parsed once no matter how many jobs share the JD."""

    __tablename__ = "job_requirements"

    jd_hash: Mapped[str] = mapped_column(String, primary_key=True)
    parsed_json: Mapped[dict] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(default=_now)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # null if gated out
    components_json: Mapped[dict] = mapped_column(JSONB)
    gates_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    canonical: Mapped[str] = mapped_column(String, index=True)
    alias: Mapped[str] = mapped_column(String, unique=True)


class UnresolvedSkill(Base):
    __tablename__ = "unresolved_skills"

    token: Mapped[str] = mapped_column(String, primary_key=True)  # lowercased raw token
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(default=_now)


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    node: Mapped[str] = mapped_column(String)  # "profile_extractor", "jd_extractor", ...
    model: Mapped[str] = mapped_column(String)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=_now)
