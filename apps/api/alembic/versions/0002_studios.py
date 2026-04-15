"""Stage 1 studios + studio_members tables with membership-based RLS.

Revision ID: 0002_studios
Revises: 0001_infra_baseline
Create Date: 2026-04-15

PRD §Slice 3: multi-tenant foundation. studios table with state enum,
studio_members join table for membership-based RLS.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_studios"
down_revision = "0001_infra_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- studios ----------------------------------------------------------
    op.create_table(
        "studios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.Text(), nullable=True),
        sa.Column(
            "timezone", sa.Text(), nullable=False, server_default=sa.text("'America/New_York'")
        ),
        sa.Column(
            "beta_cohort",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
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
            "state IN ('pending', 'active', 'suspended')",
            name="studios_state_check",
        ),
    )

    op.execute("ALTER TABLE studios ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "select_member" ON studios '
        "FOR SELECT TO authenticated "
        "USING ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = studios.id"
        "    AND sm.user_id = auth.uid()"
        "  )"
        ")"
    )
    op.execute(
        'CREATE POLICY "insert_authenticated" ON studios '
        "FOR INSERT TO authenticated "
        "WITH CHECK (true)"
    )
    op.execute(
        'CREATE POLICY "update_member" ON studios '
        "FOR UPDATE TO authenticated "
        "USING ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = studios.id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role IN ('owner', 'teacher')"
        "  )"
        ") "
        "WITH CHECK ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = studios.id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role IN ('owner', 'teacher')"
        "  )"
        ")"
    )
    op.execute(
        'CREATE POLICY "delete_owner" ON studios '
        "FOR DELETE TO authenticated "
        "USING ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = studios.id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role = 'owner'"
        "  )"
        ")"
    )

    # ---- studio_members ---------------------------------------------------
    op.create_table(
        "studio_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'teacher', 'student', 'parent')",
            name="studio_members_role_check",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="studio_members_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="studio_members_user_id_fkey",
        ),
    )
    op.create_index(
        "studio_members_studio_user_key",
        "studio_members",
        ["studio_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "studio_members_user_id_idx",
        "studio_members",
        ["user_id"],
    )

    op.execute("ALTER TABLE studio_members ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "select_own" ON studio_members '
        "FOR SELECT TO authenticated "
        "USING (user_id = auth.uid())"
    )
    op.execute(
        'CREATE POLICY "insert_authenticated" ON studio_members '
        "FOR INSERT TO authenticated "
        "WITH CHECK (user_id = auth.uid())"
    )
    op.execute(
        'CREATE POLICY "delete_own" ON studio_members '
        "FOR DELETE TO authenticated "
        "USING (user_id = auth.uid())"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS studio_members")
    op.execute("DROP TABLE IF EXISTS studios")
