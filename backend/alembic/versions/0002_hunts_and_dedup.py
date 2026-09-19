"""hunts, cross-board job dedup, match inbox fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("jobs_company_id_ats_job_id_key", "jobs", type_="unique")
    op.add_column("jobs", sa.Column("ats_kind", sa.String, nullable=False, server_default="greenhouse"))
    op.add_column("jobs", sa.Column("normalized_title", sa.String, nullable=False, server_default=""))
    op.alter_column("jobs", "ats_kind", server_default=None)
    op.alter_column("jobs", "normalized_title", server_default=None)
    op.create_unique_constraint("uq_jobs_source_listing", "jobs", ["company_id", "ats_kind", "ats_job_id"])
    op.create_unique_constraint("uq_jobs_dedup_key", "jobs", ["company_id", "normalized_title", "location"])

    op.add_column("matches", sa.Column("prep_plan_json", JSONB, nullable=True))
    op.add_column("matches", sa.Column("dismissed", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("matches", sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "hunts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("roles", JSONB, nullable=False, server_default="[]"),
        sa.Column("locations", JSONB, nullable=False, server_default="[]"),
        sa.Column("comp_floor", sa.Float, nullable=True),
        sa.Column("company_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("schedule", sa.String, nullable=False, server_default="daily"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("hunts")
    op.drop_column("matches", "seen_at")
    op.drop_column("matches", "dismissed")
    op.drop_column("matches", "prep_plan_json")
    op.drop_constraint("uq_jobs_dedup_key", "jobs", type_="unique")
    op.drop_constraint("uq_jobs_source_listing", "jobs", type_="unique")
    op.drop_column("jobs", "normalized_title")
    op.drop_column("jobs", "ats_kind")
    op.create_unique_constraint("jobs_company_id_ats_job_id_key", "jobs", ["company_id", "ats_job_id"])
