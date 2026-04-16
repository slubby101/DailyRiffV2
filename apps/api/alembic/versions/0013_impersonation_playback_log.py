"""Impersonation playback audit log for recording access.

Revision ID: 0013_impersonation_playback_log
Revises: 0012_loans
Create Date: 2026-04-16

PRD §Slice 19: Audit trail when superadmin accesses recording playback
via an impersonation session. Written by the playback-url endpoint when
CurrentUser.impersonation_session_id is not None.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_impersonation_playback_log"
down_revision = "0012_loans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "impersonation_playback_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recording_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "minted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recordings.id"],
            ondelete="CASCADE",
            name="imp_playback_log_recording_id_fkey",
        ),
    )
    op.create_index(
        "imp_playback_log_session_id_idx",
        "impersonation_playback_log",
        ["session_id"],
    )
    op.create_index(
        "imp_playback_log_recording_id_idx",
        "impersonation_playback_log",
        ["recording_id"],
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS impersonation_playback_log")
