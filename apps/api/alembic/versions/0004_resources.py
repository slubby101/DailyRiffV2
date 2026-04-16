"""Stage 1 resources table with studio-scoped RLS.

Revision ID: 0004_resources
Revises: 0003_platform_settings
Create Date: 2026-04-16

PRD §Slice 12: studio-scoped external link library. Smallest tenant-scoped
feature — demonstrates the full membership-based RLS pattern.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_resources"
down_revision = "0003_platform_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            name="resources_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="resources_created_by_fkey",
        ),
    )
    op.create_index("resources_studio_id_idx", "resources", ["studio_id"])
    op.create_index(
        "resources_studio_category_idx", "resources", ["studio_id", "category"]
    )

    op.execute("ALTER TABLE resources ENABLE ROW LEVEL SECURITY")

    op.execute(
        'CREATE POLICY "select_member" ON resources '
        "FOR SELECT TO authenticated "
        "USING ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = resources.studio_id"
        "    AND sm.user_id = auth.uid()"
        "  )"
        ")"
    )
    op.execute(
        'CREATE POLICY "insert_member" ON resources '
        "FOR INSERT TO authenticated "
        "WITH CHECK ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = resources.studio_id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role IN ('owner', 'teacher')"
        "  )"
        ")"
    )
    op.execute(
        'CREATE POLICY "update_member" ON resources '
        "FOR UPDATE TO authenticated "
        "USING ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = resources.studio_id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role IN ('owner', 'teacher')"
        "  )"
        ") "
        "WITH CHECK ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = resources.studio_id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role IN ('owner', 'teacher')"
        "  )"
        ")"
    )
    op.execute(
        'CREATE POLICY "delete_member" ON resources '
        "FOR DELETE TO authenticated "
        "USING ("
        "  EXISTS ("
        "    SELECT 1 FROM studio_members sm"
        "    WHERE sm.studio_id = resources.studio_id"
        "    AND sm.user_id = auth.uid()"
        "    AND sm.role IN ('owner', 'teacher')"
        "  )"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS resources")
