"""Impersonation sessions table for superadmin user impersonation.

Revision ID: 0018_impersonation_sessions
Revises: 0017_account_conversion
Create Date: 2026-04-16

PRD Slice 30: delayed-notification impersonation with live-mode override.
Superadmin can impersonate any user with a mandatory reason, hard-enforced
scope restrictions, and full audit trail. Sessions have 3-year retention.
"""

from alembic import op

revision = "0018_impersonation_sessions"
down_revision = "0017_account_conversion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE impersonation_mode AS ENUM ('silent', 'live');
    """)

    op.execute("""
        CREATE TABLE impersonation_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            impersonator_user_id UUID NOT NULL REFERENCES auth.users(id),
            target_user_id UUID NOT NULL REFERENCES auth.users(id),
            studio_id UUID REFERENCES studios(id),
            reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
            mode impersonation_mode NOT NULL DEFAULT 'silent',
            ip_address TEXT,
            user_agent TEXT,
            started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            ended_at TIMESTAMP WITH TIME ZONE,
            notification_sent_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE INDEX impersonation_sessions_impersonator_idx
            ON impersonation_sessions (impersonator_user_id);
    """)
    op.execute("""
        CREATE INDEX impersonation_sessions_target_idx
            ON impersonation_sessions (target_user_id);
    """)
    op.execute("""
        CREATE INDEX impersonation_sessions_active_idx
            ON impersonation_sessions (impersonator_user_id)
            WHERE ended_at IS NULL;
    """)

    # Add foreign key from impersonation_playback_log.session_id
    # to impersonation_sessions.id (playback log was created in 0013
    # without a FK because the sessions table didn't exist yet)
    op.execute("""
        ALTER TABLE impersonation_playback_log
            ADD CONSTRAINT imp_playback_log_session_fk
            FOREIGN KEY (session_id) REFERENCES impersonation_sessions(id)
            ON DELETE CASCADE;
    """)

    # RLS: no user-level access — only service_transaction (superadmin endpoints)
    op.execute("ALTER TABLE impersonation_sessions ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("ALTER TABLE impersonation_playback_log DROP CONSTRAINT IF EXISTS imp_playback_log_session_fk;")
    op.execute("DROP TABLE IF EXISTS impersonation_sessions;")
    op.execute("DROP TYPE IF EXISTS impersonation_mode;")
