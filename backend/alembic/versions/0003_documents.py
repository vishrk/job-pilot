"""documents table for tailored resumes/cover letters

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("match_id", sa.String, sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("content_json", JSONB, nullable=False),
        sa.Column("provenance_map", JSONB, nullable=False),
        sa.Column("verify_report", JSONB, nullable=True),
        sa.Column("rejected_bullets", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String, nullable=False, server_default="draft"),
        sa.Column("approved_bullet_ids", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("documents")
