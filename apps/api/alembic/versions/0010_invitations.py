"""Invitations, parents, and parent_children tables for student↔studio onboarding.

Revision ID: 0010_invitations
Revises: 0009_waitlist
Create Date: 2026-04-16

PRD §Slice 9: teacher-initiated and parent-self-serve invitation pipeline.
invitations tracks hashed tokens with 14-day expiry, single-use, regenerable,
persona-typed. parents + parent_children tables model the guardian↔child
relationship with per-child permission flags.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_invitations"
down_revision = "0009_waitlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- invitations --------------------------------------------------------
    op.create_table(
        "invitations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_email", sa.Text(), nullable=False),
        sa.Column("invited_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "persona",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("redeemed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("redeemed_by", postgresql.UUID(as_uuid=True), nullable=True),
        # For age-based routing
        sa.Column(
            "age_class",
            sa.Text(),
            nullable=True,
        ),
        # For parent-self-serve with studio code
        sa.Column("auto_approve", sa.Boolean(), nullable=False, server_default=sa.false()),
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
            "persona IN ('studio-owner', 'teacher', 'parent', 'student')",
            name="invitations_persona_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'expired', 'revoked')",
            name="invitations_status_check",
        ),
        sa.CheckConstraint(
            "age_class IS NULL OR age_class IN ('minor', 'teen', 'adult')",
            name="invitations_age_class_check",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="invitations_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="invitations_invited_by_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["invited_user_id"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="invitations_invited_user_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["redeemed_by"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="invitations_redeemed_by_fkey",
        ),
    )
    op.create_index(
        "invitations_studio_status_idx",
        "invitations",
        ["studio_id", "status"],
    )
    op.create_index(
        "invitations_email_status_idx",
        "invitations",
        ["invited_email", "status"],
    )
    op.create_index(
        "invitations_token_hash_idx",
        "invitations",
        ["token_hash"],
        unique=True,
    )

    # ---- parents ------------------------------------------------------------
    op.create_table(
        "parents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            name="parents_user_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="parents_studio_id_fkey",
        ),
    )
    op.create_index(
        "parents_studio_id_idx",
        "parents",
        ["studio_id"],
    )

    # ---- parent_children ----------------------------------------------------
    op.create_table(
        "parent_children",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_primary_contact",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "can_manage_payments",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "can_view_progress",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "can_communicate_with_teacher",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["parents.id"],
            ondelete="CASCADE",
            name="parent_children_parent_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["child_user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="parent_children_child_user_id_fkey",
        ),
    )
    op.create_index(
        "parent_children_parent_child_key",
        "parent_children",
        ["parent_id", "child_user_id"],
        unique=True,
    )
    op.create_index(
        "parent_children_child_user_id_idx",
        "parent_children",
        ["child_user_id"],
    )

    # ---- auto_approve toggle on studios -------------------------------------
    op.add_column(
        "studios",
        sa.Column(
            "auto_approve_parents",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("studios", "auto_approve_parents")
    op.execute("DROP TABLE IF EXISTS parent_children")
    op.execute("DROP TABLE IF EXISTS parents")
    op.execute("DROP TABLE IF EXISTS invitations")
