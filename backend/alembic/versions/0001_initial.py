"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-19

"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 512


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "profiles",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("master_json", JSONB, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "profile_bullets",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("profile_id", sa.String, sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("experience_id", sa.String, nullable=True),
        sa.Column("text", sa.String, nullable=False),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("domain", sa.String, nullable=True),
    )

    op.create_table(
        "ats_accounts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("company_id", sa.String, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("ats_kind", sa.String, nullable=False),
        sa.Column("board_token", sa.String, nullable=False),
        sa.UniqueConstraint("company_id", "ats_kind"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("company_id", sa.String, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("ats_job_id", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("location", sa.String, nullable=True),
        sa.Column("jd_hash", sa.String, nullable=False, index=True),
        sa.Column("raw", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("company_id", "ats_job_id"),
    )

    op.create_table(
        "job_requirements",
        sa.Column("jd_hash", sa.String, primary_key=True),
        sa.Column("parsed_json", JSONB, nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String, sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("components_json", JSONB, nullable=False),
        sa.Column("gates_json", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "job_id"),
    )

    op.create_table(
        "skill_aliases",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("canonical", sa.String, nullable=False, index=True),
        sa.Column("alias", sa.String, nullable=False, unique=True),
    )

    op.create_table(
        "unresolved_skills",
        sa.Column("token", sa.String, primary_key=True),
        sa.Column("count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("node", sa.String, nullable=False),
        sa.Column("model", sa.String, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("llm_calls")
    op.drop_table("unresolved_skills")
    op.drop_table("skill_aliases")
    op.drop_table("matches")
    op.drop_table("job_requirements")
    op.drop_table("jobs")
    op.drop_table("ats_accounts")
    op.drop_table("companies")
    op.drop_table("profile_bullets")
    op.drop_table("profiles")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
