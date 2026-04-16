"""Rate limiting infrastructure: idempotency_log + rate limit platform_settings seeds.

Revision ID: 0005_rate_limiting
Revises: 0004_resources
Create Date: 2026-04-16

PRD §Slice 14: four-layer defense-in-depth. idempotency_log for webhook
replay defense, platform_settings seeds for Layer B + D tunables.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_rate_limiting"
down_revision = "0004_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- idempotency_log --------------------------------------------------------
    op.create_table(
        "idempotency_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("provider", "event_id", name="idempotency_log_provider_event_id_uniq"),
    )
    op.create_index("idempotency_log_created_at_idx", "idempotency_log", ["created_at"])

    # ---- Seed rate limit platform_settings --------------------------------------
    op.execute(
        "INSERT INTO platform_settings (key, value_json, description, category) VALUES "
        "('rate_limit_overrides', "
        "'{}', "
        "'Per-route rate limit overrides (key=route_key, value=rate string like 10/minute)', "
        "'rate_limits'), "
        "('cap_recordings_per_student_per_day', "
        "'50', "
        "'Max recordings a student can submit per day', "
        "'business_rule_caps'), "
        "('cap_messages_per_user_per_day', "
        "'200', "
        "'Max messages a user can send per day', "
        "'business_rule_caps'), "
        "('cap_waitlist_per_email_lifetime', "
        "'1', "
        "'Max waitlist submissions per email (lifetime)', "
        "'business_rule_caps'), "
        "('cap_waitlist_per_ip_lifetime', "
        "'3', "
        "'Max waitlist submissions per IP (lifetime)', "
        "'business_rule_caps'), "
        "('cap_push_per_user_per_day', "
        "'20', "
        "'Max push notifications per user per day', "
        "'business_rule_caps'), "
        "('cap_coppa_vpc_per_parent_per_day', "
        "'3', "
        "'Max COPPA VPC charge attempts per parent per 24h', "
        "'business_rule_caps') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM platform_settings WHERE key IN ("
        "'rate_limit_overrides', "
        "'cap_recordings_per_student_per_day', "
        "'cap_messages_per_user_per_day', "
        "'cap_waitlist_per_email_lifetime', "
        "'cap_waitlist_per_ip_lifetime', "
        "'cap_push_per_user_per_day', "
        "'cap_coppa_vpc_per_parent_per_day'"
        ")"
    )
    op.execute("DROP TABLE IF EXISTS idempotency_log")
