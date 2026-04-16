"""Stage 1 / Slice 26 — Beta rollout scaffolding.

Revision ID: 0020_beta_feedback
Revises: 0019_lessons_attendance
Create Date: 2026-04-16

PRD §Slice 26: beta_feedback table for controlled-beta feedback collection.
studios.beta_cohort already exists from 0002_studios.
"""
from __future__ import annotations

from alembic import op

revision = "0020_beta_feedback"
down_revision = "0019_lessons_attendance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- ENUM type ------------------------------------------------------------
    op.execute(
        "CREATE TYPE beta_feedback_category AS ENUM "
        "('bug', 'feature_request', 'usability', 'performance', 'other');"
    )
    op.execute(
        "CREATE TYPE beta_feedback_severity AS ENUM "
        "('critical', 'high', 'medium', 'low');"
    )

    # ---- beta_feedback table --------------------------------------------------
    op.execute("""
        CREATE TABLE beta_feedback (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            studio_id     UUID NOT NULL REFERENCES studios(id),
            submitted_by  UUID NOT NULL,
            category      beta_feedback_category NOT NULL DEFAULT 'other',
            severity      beta_feedback_severity NOT NULL DEFAULT 'medium',
            body          TEXT NOT NULL,
            submitted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at   TIMESTAMPTZ,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ---- RLS ------------------------------------------------------------------
    op.execute("ALTER TABLE beta_feedback ENABLE ROW LEVEL SECURITY;")

    # Members of beta studios can read their own studio's feedback
    op.execute("""
        CREATE POLICY beta_feedback_select ON beta_feedback
            FOR SELECT
            USING (
                studio_id IN (
                    SELECT sm.studio_id FROM studio_members sm
                    WHERE sm.user_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::uuid
                )
                AND studio_id IN (
                    SELECT s.id FROM studios s WHERE s.beta_cohort = true
                )
            );
    """)

    # Members of beta studios can insert feedback
    op.execute("""
        CREATE POLICY beta_feedback_insert ON beta_feedback
            FOR INSERT
            WITH CHECK (
                studio_id IN (
                    SELECT sm.studio_id FROM studio_members sm
                    WHERE sm.user_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::uuid
                )
                AND studio_id IN (
                    SELECT s.id FROM studios s WHERE s.beta_cohort = true
                )
            );
    """)

    # ---- beta_landing_tokens table -------------------------------------------
    op.execute("""
        CREATE TABLE beta_landing_tokens (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token       TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_by  UUID NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # ---- Indexes --------------------------------------------------------------
    op.execute(
        "CREATE INDEX idx_beta_feedback_studio_id ON beta_feedback(studio_id);"
    )
    op.execute(
        "CREATE INDEX idx_beta_feedback_submitted_at ON beta_feedback(submitted_at DESC);"
    )

    # ---- Seed beta onboarding notification templates -------------------------
    op.execute("""
        INSERT INTO notification_templates
            (event_type, category, persona, title_template, body_template, channels, trigger_source)
        VALUES
            ('beta.welcome', 'beta_onboarding', 'teacher',
             'Welcome to the DailyRiff Beta!',
             'Hi {owner_name}, your studio {studio_name} has been accepted into the DailyRiff beta program. We''re excited to have you on board!',
             '["web_push"]'::jsonb, 'fastapi_handler'),
            ('beta.getting_started', 'beta_onboarding', 'teacher',
             'Getting started with DailyRiff',
             'Hi {owner_name}, here are some tips to get the most out of your DailyRiff beta experience: invite your teachers, set up your studio profile, and create your first assignment.',
             '["web_push"]'::jsonb, 'fastapi_handler'),
            ('beta.feedback_reminder', 'beta_onboarding', 'teacher',
             'How''s your DailyRiff experience?',
             'Hi {owner_name}, we''d love to hear your feedback on DailyRiff. Submit feedback from your studio dashboard or contact us at support@dailyriff.com.',
             '["web_push"]'::jsonb, 'fastapi_handler')
        ON CONFLICT (event_type) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS beta_landing_tokens;")
    op.execute("DROP TABLE IF EXISTS beta_feedback;")
    op.execute("DROP TYPE IF EXISTS beta_feedback_severity;")
    op.execute("DROP TYPE IF EXISTS beta_feedback_category;")
