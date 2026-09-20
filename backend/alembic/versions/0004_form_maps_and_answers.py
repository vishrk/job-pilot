"""form_maps and answers, for the extension (Phase 3)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "form_maps",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("domain", sa.String, nullable=False),
        sa.Column("form_fingerprint", sa.String, nullable=False),
        sa.Column("mapping_json", JSONB, nullable=False),
        sa.Column("health", sa.String, nullable=False, server_default="untested"),
        sa.Column("last_ok_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("domain", "form_fingerprint"),
    )

    op.create_table(
        "answers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question_fingerprint", sa.String, nullable=False),
        sa.Column("question_text", sa.String, nullable=False),
        sa.Column("answer", sa.String, nullable=False),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "question_fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("answers")
    op.drop_table("form_maps")
