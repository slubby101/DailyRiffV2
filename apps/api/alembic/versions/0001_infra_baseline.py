"""Stage 0 infra baseline: user_push_subscriptions, notification_preferences, realtime_outbox.

Revision ID: 0001_infra_baseline
Revises:
Create Date: 2026-04-14

PRD §5: three infra tables, all with RLS enabled. FKs into `auth.users`
ON DELETE CASCADE. `realtime_outbox` is included unconditionally so
slice `d` (NotificationService) never needs to amend migration 0001.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_infra_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- user_push_subscriptions ---------------------------------------
    op.create_table(
        "user_push_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("keys", postgresql.JSONB(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "channel IN ('expo', 'webpush')",
            name="user_push_subscriptions_channel_check",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="user_push_subscriptions_user_id_fkey",
        ),
    )
    op.create_index(
        "user_push_subscriptions_user_channel_token_key",
        "user_push_subscriptions",
        ["user_id", "channel", "token"],
        unique=True,
    )

    op.execute("ALTER TABLE user_push_subscriptions ENABLE ROW LEVEL SECURITY")
    for action, using, with_check in (
        ("select", "user_id = auth.uid()", None),
        ("insert", None, "user_id = auth.uid()"),
        ("update", "user_id = auth.uid()", "user_id = auth.uid()"),
        ("delete", "user_id = auth.uid()", None),
    ):
        clauses = [f"FOR {action.upper()}", "TO authenticated"]
        if using is not None:
            clauses.append(f"USING ({using})")
        if with_check is not None:
            clauses.append(f"WITH CHECK ({with_check})")
        op.execute(
            f'CREATE POLICY "{action}_own" ON user_push_subscriptions '
            + " ".join(clauses)
        )

    # ---- notification_preferences --------------------------------------
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "realtime_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "expo_push_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "web_push_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="notification_preferences_user_id_fkey",
        ),
    )

    op.execute("ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY")
    for action, using, with_check in (
        ("select", "user_id = auth.uid()", None),
        ("insert", None, "user_id = auth.uid()"),
        ("update", "user_id = auth.uid()", "user_id = auth.uid()"),
        ("delete", "user_id = auth.uid()", None),
    ):
        clauses = [f"FOR {action.upper()}", "TO authenticated"]
        if using is not None:
            clauses.append(f"USING ({using})")
        if with_check is not None:
            clauses.append(f"WITH CHECK ({with_check})")
        op.execute(
            f'CREATE POLICY "{action}_own" ON notification_preferences '
            + " ".join(clauses)
        )

    # ---- realtime_outbox -----------------------------------------------
    op.create_table(
        "realtime_outbox",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="realtime_outbox_user_id_fkey",
        ),
    )
    op.execute("ALTER TABLE realtime_outbox ENABLE ROW LEVEL SECURITY")
    # PRD §5: select_own only; writes are service-role only (no policies
    # for INSERT/UPDATE/DELETE → authenticated role cannot write).
    op.execute(
        'CREATE POLICY "select_own" ON realtime_outbox '
        "FOR SELECT TO authenticated USING (user_id = auth.uid())"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS realtime_outbox")
    op.execute("DROP TABLE IF EXISTS notification_preferences")
    op.execute("DROP TABLE IF EXISTS user_push_subscriptions")
