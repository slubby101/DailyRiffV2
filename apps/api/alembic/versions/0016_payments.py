"""Payments table for teacher payment ledger.

Revision ID: 0016_payments
Revises: 0015_log_retention_cleanup
Create Date: 2026-04-16

PRD Slice 28: manual teacher-entered payment ledger. No Stripe Connect,
no platform fees — DailyRiff is pure marketplace; money movement is Stage 2+.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_payments"
down_revision = "0015_log_retention_cleanup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Payment status enum
    payment_status = postgresql.ENUM(
        "pending", "paid", "refunded",
        name="payment_status",
        create_type=False,
    )
    op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'refunded')")

    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("payer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            payment_status,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("refunded_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            name="payments_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["student_user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="payments_student_user_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["payer_user_id"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="payments_payer_user_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="payments_created_by_fkey",
        ),
    )
    op.create_index(
        "payments_studio_student_idx",
        "payments",
        ["studio_id", "student_user_id"],
    )
    op.create_index(
        "payments_studio_status_idx",
        "payments",
        ["studio_id", "status"],
    )

    # RLS: only studio members can read, only owner/teacher can write
    op.execute("ALTER TABLE payments ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY payments_select ON payments FOR SELECT TO authenticated
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
        CREATE POLICY payments_insert ON payments FOR INSERT TO authenticated
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
        CREATE POLICY payments_update ON payments FOR UPDATE TO authenticated
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
        CREATE POLICY payments_delete ON payments FOR DELETE TO authenticated
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
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP TYPE IF EXISTS payment_status")
