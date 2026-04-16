"""waitlist_entries and waitlist_messages tables for studio onboarding pipeline.

Revision ID: 0009_waitlist
Revises: 0008_dailyriff_employees
Create Date: 2026-04-16

PRD §Slice 8: waitlist + studio onboarding. waitlist_entries tracks studio
interest submissions from the marketing homepage. waitlist_messages stores
admin-to-applicant communications. Bypass tokens allow personal-network
direct invites that skip the waitlist queue.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_waitlist"
down_revision = "0008_dailyriff_employees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- waitlist_entries ----------------------------------------------------
    op.create_table(
        "waitlist_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("studio_name", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("hcaptcha_token", sa.Text(), nullable=True),
        sa.Column("bypass_token", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'invited')",
            name="waitlist_entries_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="waitlist_entries_reviewed_by_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="SET NULL",
            name="waitlist_entries_studio_id_fkey",
        ),
    )
    op.create_index(
        "waitlist_entries_email_idx",
        "waitlist_entries",
        ["email"],
    )
    op.create_index(
        "waitlist_entries_status_idx",
        "waitlist_entries",
        ["status"],
    )
    op.create_index(
        "waitlist_entries_bypass_token_idx",
        "waitlist_entries",
        ["bypass_token"],
        unique=True,
        postgresql_where=sa.text("bypass_token IS NOT NULL"),
    )

    # ---- waitlist_messages ---------------------------------------------------
    # Admin-to-applicant communication thread per waitlist entry.
    op.create_table(
        "waitlist_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("waitlist_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["waitlist_entry_id"],
            ["waitlist_entries.id"],
            ondelete="CASCADE",
            name="waitlist_messages_entry_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="waitlist_messages_sender_id_fkey",
        ),
    )
    op.create_index(
        "waitlist_messages_entry_id_idx",
        "waitlist_messages",
        ["waitlist_entry_id"],
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS waitlist_messages")
    op.execute("DROP TABLE IF EXISTS waitlist_entries")
