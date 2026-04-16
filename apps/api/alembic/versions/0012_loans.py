"""Loans table for teacher payment ledger tracking.

Revision ID: 0012_loans
Revises: 0011_assignments_recordings
Create Date: 2026-04-16

PRD §Slice 21: studio-scoped loan tracking per student.
Teachers record instrument loans; parents see read-only view.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_loans"
down_revision = "0011_assignments_recordings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("loaned_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("returned_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="loans_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["student_user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="loans_student_user_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="loans_created_by_fkey",
        ),
    )
    op.create_index(
        "loans_studio_student_idx",
        "loans",
        ["studio_id", "student_user_id"],
    )

    # RLS: only studio members can read loans, only owner/teacher can write
    op.execute("ALTER TABLE loans ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY loans_select ON loans FOR SELECT TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY loans_insert ON loans FOR INSERT TO authenticated
        WITH CHECK (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
                  AND role IN ('owner', 'teacher')
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY loans_update ON loans FOR UPDATE TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
                  AND role IN ('owner', 'teacher')
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY loans_delete ON loans FOR DELETE TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
                  AND role IN ('owner', 'teacher')
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS loans")
