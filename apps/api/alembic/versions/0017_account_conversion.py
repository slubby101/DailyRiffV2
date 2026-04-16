"""Add age_class + updated_at to studio_members for account conversion.

Revision ID: 0017_account_conversion
Revises: 0016_payments
Create Date: 2026-04-16

PRD Slice 29: manual age-class account conversion (MINOR→TEEN at 13,
TEEN→ADULT at 18). Adds age_class column to studio_members to track
current classification, and updated_at for conversion timestamps.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0017_account_conversion"
down_revision = "0016_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add age_class to studio_members (nullable — only students have it)
    op.add_column(
        "studio_members",
        sa.Column("age_class", sa.Text(), nullable=True),
    )
    op.execute(
        "ALTER TABLE studio_members ADD CONSTRAINT studio_members_age_class_check "
        "CHECK (age_class IS NULL OR age_class IN ('minor', 'teen', 'adult'))"
    )

    # Add updated_at to studio_members (for conversion timestamps)
    op.add_column(
        "studio_members",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE studio_members DROP CONSTRAINT IF EXISTS studio_members_age_class_check"
    )
    op.drop_column("studio_members", "age_class")
    op.drop_column("studio_members", "updated_at")
