"""Add retention cleanup functions + pg_cron jobs for mfa_failure_log and idempotency_log.

Revision ID: 0015_log_retention_cleanup
Revises: 0014_coppa_consents
Create Date: 2026-04-16

Adversarial review finding: both tables grow unboundedly.
  - mfa_failure_log: delete rows older than 30 days
  - idempotency_log: delete rows older than 90 days

Creates SQL functions callable independently of pg_cron so they can be
tested and invoked manually. pg_cron schedules them daily at 03:00 UTC.
"""
from __future__ import annotations

from alembic import op

revision = "0015_log_retention_cleanup"
down_revision = "0014_coppa_consents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Cleanup functions -------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION public.cleanup_mfa_failure_log()
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            deleted_count integer;
        BEGIN
            DELETE FROM public.mfa_failure_log
            WHERE created_at < now() - interval '30 days';
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.cleanup_idempotency_log()
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            deleted_count integer;
        BEGIN
            DELETE FROM public.idempotency_log
            WHERE created_at < now() - interval '90 days';
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$
    """)

    # ---- pg_cron schedules -------------------------------------------------------
    # pg_cron is available by default in Supabase. Enable the extension in case
    # it hasn't been activated yet, then schedule daily runs at 03:00 UTC.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron SCHEMA pg_catalog")

    op.execute("""
        SELECT cron.schedule(
            'cleanup-mfa-failure-log',
            '0 3 * * *',
            'SELECT public.cleanup_mfa_failure_log()'
        )
    """)

    op.execute("""
        SELECT cron.schedule(
            'cleanup-idempotency-log',
            '0 3 * * *',
            'SELECT public.cleanup_idempotency_log()'
        )
    """)

    # ---- Expand category check to include 'retention' ----------------------------
    op.execute("ALTER TABLE platform_settings DROP CONSTRAINT platform_settings_category_check")
    op.execute(
        "ALTER TABLE platform_settings ADD CONSTRAINT platform_settings_category_check "
        "CHECK (category IN ('rate_limits', 'business_rule_caps', "
        "'notification_delays', 'coppa_grace_windows', 'retention'))"
    )

    # ---- Seed retention platform_settings for visibility -------------------------
    op.execute(
        "INSERT INTO platform_settings (key, value_json, description, category) VALUES "
        "('retention_mfa_failure_log_days', '30', "
        "'Days to retain mfa_failure_log rows before cleanup', 'retention'), "
        "('retention_idempotency_log_days', '90', "
        "'Days to retain idempotency_log rows before cleanup', 'retention') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("SELECT cron.unschedule('cleanup-mfa-failure-log')")
    op.execute("SELECT cron.unschedule('cleanup-idempotency-log')")
    op.execute("DROP FUNCTION IF EXISTS public.cleanup_mfa_failure_log()")
    op.execute("DROP FUNCTION IF EXISTS public.cleanup_idempotency_log()")
    op.execute(
        "DELETE FROM platform_settings WHERE key IN ("
        "'retention_mfa_failure_log_days', 'retention_idempotency_log_days')"
    )
    op.execute("ALTER TABLE platform_settings DROP CONSTRAINT platform_settings_category_check")
    op.execute(
        "ALTER TABLE platform_settings ADD CONSTRAINT platform_settings_category_check "
        "CHECK (category IN ('rate_limits', 'business_rule_caps', "
        "'notification_delays', 'coppa_grace_windows'))"
    )
    op.execute(
        "DELETE FROM platform_settings WHERE key IN ("
        "'retention_mfa_failure_log_days', "
        "'retention_idempotency_log_days'"
        ")"
    )
