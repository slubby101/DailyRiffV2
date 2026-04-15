"""Stage 1 platform_settings + activity_logs tables.

Revision ID: 0003_platform_settings
Revises: 0002_studios
Create Date: 2026-04-15

PRD §Slice 4: platform-settings foundation with superadmin-only access
and append-only activity log for audit trail.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_platform_settings"
down_revision = "0002_studios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- platform_settings ---------------------------------------------------
    op.create_table(
        "platform_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("key", sa.Text(), nullable=False, unique=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "category IN ('rate_limits', 'business_rule_caps', "
            "'notification_delays', 'coppa_grace_windows')",
            name="platform_settings_category_check",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["auth.users.id"],
            ondelete="SET NULL",
            name="platform_settings_updated_by_fkey",
        ),
    )

    op.execute("ALTER TABLE platform_settings ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "select_authenticated" ON platform_settings '
        "FOR SELECT TO authenticated "
        "USING (true)"
    )

    # ---- activity_logs -------------------------------------------------------
    op.create_table(
        "activity_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
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
            name="activity_logs_user_id_fkey",
        ),
    )
    op.create_index(
        "activity_logs_user_id_idx",
        "activity_logs",
        ["user_id"],
    )
    op.create_index(
        "activity_logs_entity_idx",
        "activity_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "activity_logs_created_at_idx",
        "activity_logs",
        ["created_at"],
    )

    op.execute("ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "select_authenticated" ON activity_logs '
        "FOR SELECT TO authenticated "
        "USING (true)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activity_logs")
    op.execute("DROP TABLE IF EXISTS platform_settings")
