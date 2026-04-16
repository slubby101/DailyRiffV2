"""dailyriff_employees table for superadmin identity.

Revision ID: 0008_dailyriff_employees
Revises: 0007_notification_templates
Create Date: 2026-04-16

PRD §Slice 5: superadmin identity + security. dailyriff_employees stores
platform operator roles (owner/support/verifier). mfa_failure_log tracks
consecutive failures for the 3-in-15-min alerting policy.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_dailyriff_employees"
down_revision = "0007_notification_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- dailyriff_employees -------------------------------------------------
    op.create_table(
        "dailyriff_employees",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'support', 'verifier')",
            name="dailyriff_employees_role_check",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="dailyriff_employees_user_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="dailyriff_employees_created_by_fkey",
        ),
    )
    op.create_index(
        "dailyriff_employees_user_id_idx",
        "dailyriff_employees",
        ["user_id"],
    )

    # ---- mfa_failure_log ----------------------------------------------------
    # Tracks failed MFA attempts for the 3-in-15-min alerting policy.
    op.create_table(
        "mfa_failure_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="mfa_failure_log_user_id_fkey",
        ),
    )
    op.create_index(
        "mfa_failure_log_user_created_idx",
        "mfa_failure_log",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mfa_failure_log")
    op.execute("DROP TABLE IF EXISTS dailyriff_employees")
