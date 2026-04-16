"""Stage 1 / Slice 31 — Soft-delete + COPPA 15-day grace deletion + hard-delete worker.

Revision ID: 0021_soft_delete_coppa_deletion
Revises: 0020_beta_feedback
Create Date: 2026-04-16

PRD §Slice 31:
  - Tier 2: soft-delete on all recording delete paths (deleted_at column already exists)
  - COPPA 15-day grace deletion: parent-initiated, email-confirmed, with reminders
  - pg_cron hard-delete worker at T-0: removes student data + writes PII-free log
  - R2 credential scoping: separate env vars for API (read/write) vs worker (delete)
"""
from __future__ import annotations

from alembic import op

revision = "0021_soft_delete_coppa_deletion"
down_revision = "0020_beta_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- coppa_deletion_requests table -------------------------------------------
    op.execute("""
        CREATE TYPE coppa_deletion_status AS ENUM (
            'pending_confirmation',
            'scheduled',
            'cancelled',
            'completed'
        )
    """)

    op.execute("""
        CREATE TABLE coppa_deletion_requests (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parent_id       UUID NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
            child_id        UUID NOT NULL,
            studio_id       UUID NOT NULL REFERENCES studios(id) ON DELETE CASCADE,
            status          coppa_deletion_status NOT NULL DEFAULT 'pending_confirmation',
            confirmation_token_hash TEXT,
            email_confirmed_at     TIMESTAMP WITH TIME ZONE,
            scheduled_delete_at    TIMESTAMP WITH TIME ZONE,
            t7_reminder_sent_at    TIMESTAMP WITH TIME ZONE,
            t1_reminder_sent_at    TIMESTAMP WITH TIME ZONE,
            completed_at           TIMESTAMP WITH TIME ZONE,
            cancelled_at           TIMESTAMP WITH TIME ZONE,
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX coppa_deletion_requests_parent_id_idx
            ON coppa_deletion_requests(parent_id)
    """)
    op.execute("""
        CREATE INDEX coppa_deletion_requests_status_idx
            ON coppa_deletion_requests(status)
    """)

    # ---- coppa_deletion_log table (NO PII) --------------------------------------
    op.execute("""
        CREATE TABLE coppa_deletion_log (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            deletion_request_id UUID NOT NULL REFERENCES coppa_deletion_requests(id),
            studio_id           UUID NOT NULL,
            child_age_class     TEXT,
            recordings_deleted  INTEGER NOT NULL DEFAULT 0,
            messages_deleted    INTEGER NOT NULL DEFAULT 0,
            assignments_deleted INTEGER NOT NULL DEFAULT 0,
            acks_deleted        INTEGER NOT NULL DEFAULT 0,
            r2_objects_queued   INTEGER NOT NULL DEFAULT 0,
            completed_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)

    # ---- r2_deletion_queue table ------------------------------------------------
    # Decouples DB deletion from R2 object deletion so the worker credential
    # can process deletions asynchronously.
    op.execute("""
        CREATE TABLE r2_deletion_queue (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            r2_object_key   TEXT NOT NULL,
            reason          TEXT NOT NULL DEFAULT 'coppa_deletion',
            queued_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            processed_at    TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("""
        CREATE INDEX r2_deletion_queue_pending_idx
            ON r2_deletion_queue(queued_at) WHERE processed_at IS NULL
    """)

    # ---- Hard-delete worker SQL function ----------------------------------------
    # Called by pg_cron daily. Finds scheduled deletion requests past their
    # scheduled_delete_at, hard-deletes student data from DB, queues R2 objects
    # for deletion, and writes a PII-free log entry.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.coppa_hard_delete_worker()
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            req RECORD;
            rec_count integer;
            msg_count integer;
            asgn_count integer;
            ack_count integer;
            r2_count integer;
            processed integer := 0;
        BEGIN
            FOR req IN
                SELECT id, child_id, studio_id
                FROM coppa_deletion_requests
                WHERE status = 'scheduled'
                  AND scheduled_delete_at <= now()
            LOOP
                -- Queue R2 objects for async deletion
                INSERT INTO r2_deletion_queue (r2_object_key, reason)
                SELECT r2_object_key, 'coppa_deletion'
                FROM recordings
                WHERE student_id = req.child_id
                  AND studio_id = req.studio_id
                  AND r2_object_key IS NOT NULL
                  AND r2_object_key != 'placeholder';
                GET DIAGNOSTICS r2_count = ROW_COUNT;

                -- Delete assignment acknowledgements
                DELETE FROM assignment_acknowledgements
                WHERE assignment_id IN (
                    SELECT id FROM assignments
                    WHERE student_id = req.child_id AND studio_id = req.studio_id
                );
                GET DIAGNOSTICS ack_count = ROW_COUNT;

                -- Hard-delete recordings (DB rows)
                DELETE FROM recordings
                WHERE student_id = req.child_id AND studio_id = req.studio_id;
                GET DIAGNOSTICS rec_count = ROW_COUNT;

                -- Delete messages authored by the child
                DELETE FROM messages
                WHERE sender_id = req.child_id
                  AND conversation_id IN (
                      SELECT c.id FROM conversations c WHERE c.studio_id = req.studio_id
                  );
                GET DIAGNOSTICS msg_count = ROW_COUNT;

                -- Delete assignments for the child
                DELETE FROM assignments
                WHERE student_id = req.child_id AND studio_id = req.studio_id;
                GET DIAGNOSTICS asgn_count = ROW_COUNT;

                -- Remove studio membership
                DELETE FROM studio_members
                WHERE user_id = req.child_id AND studio_id = req.studio_id;

                -- Remove parent-child link for this studio
                DELETE FROM parent_children
                WHERE child_id = req.child_id;

                -- Write PII-free deletion log
                INSERT INTO coppa_deletion_log
                    (deletion_request_id, studio_id, recordings_deleted,
                     messages_deleted, assignments_deleted, acks_deleted,
                     r2_objects_queued)
                VALUES
                    (req.id, req.studio_id, rec_count, msg_count,
                     asgn_count, ack_count, r2_count);

                -- Mark request completed
                UPDATE coppa_deletion_requests
                SET status = 'completed', completed_at = now(), updated_at = now()
                WHERE id = req.id;

                -- Write activity log
                INSERT INTO activity_logs (action, entity_type, entity_id, details)
                VALUES (
                    'coppa_hard_delete',
                    'coppa_deletion_request',
                    req.id,
                    jsonb_build_object(
                        'studio_id', req.studio_id,
                        'recordings_deleted', rec_count,
                        'messages_deleted', msg_count,
                        'assignments_deleted', asgn_count,
                        'r2_objects_queued', r2_count
                    )
                );

                processed := processed + 1;
            END LOOP;

            RETURN processed;
        END;
        $$
    """)

    # ---- Reminder function: sends T-7 and T-1 flags ----------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION public.coppa_deletion_send_reminders()
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            reminded integer := 0;
        BEGIN
            -- T-7 reminder
            UPDATE coppa_deletion_requests
            SET t7_reminder_sent_at = now(), updated_at = now()
            WHERE status = 'scheduled'
              AND t7_reminder_sent_at IS NULL
              AND scheduled_delete_at <= now() + interval '7 days';
            GET DIAGNOSTICS reminded = ROW_COUNT;

            -- T-1 reminder
            UPDATE coppa_deletion_requests
            SET t1_reminder_sent_at = now(), updated_at = now()
            WHERE status = 'scheduled'
              AND t1_reminder_sent_at IS NULL
              AND scheduled_delete_at <= now() + interval '1 day';

            RETURN reminded;
        END;
        $$
    """)

    # ---- pg_cron schedules ------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron SCHEMA pg_catalog")

    op.execute("""
        SELECT cron.schedule(
            'coppa-hard-delete-worker',
            '0 4 * * *',
            'SELECT public.coppa_hard_delete_worker()'
        )
    """)

    op.execute("""
        SELECT cron.schedule(
            'coppa-deletion-reminders',
            '0 10 * * *',
            'SELECT public.coppa_deletion_send_reminders()'
        )
    """)

    # ---- Seed platform_settings for COPPA deletion ------------------------------
    op.execute(
        "INSERT INTO platform_settings (key, value_json, description, category) VALUES "
        "('coppa_deletion_grace_days', '15', "
        "'Days between email confirmation and hard-delete for COPPA child data', 'coppa_grace_windows'), "
        "('coppa_deletion_t7_reminder_enabled', 'true', "
        "'Send T-7 day reminder email before COPPA hard-delete', 'coppa_grace_windows'), "
        "('coppa_deletion_t1_reminder_enabled', 'true', "
        "'Send T-1 day reminder email before COPPA hard-delete', 'coppa_grace_windows') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("SELECT cron.unschedule('coppa-hard-delete-worker')")
    op.execute("SELECT cron.unschedule('coppa-deletion-reminders')")
    op.execute("DROP FUNCTION IF EXISTS public.coppa_deletion_send_reminders()")
    op.execute("DROP FUNCTION IF EXISTS public.coppa_hard_delete_worker()")
    op.execute("DROP TABLE IF EXISTS r2_deletion_queue")
    op.execute("DROP TABLE IF EXISTS coppa_deletion_log")
    op.execute("DROP TABLE IF EXISTS coppa_deletion_requests")
    op.execute("DROP TYPE IF EXISTS coppa_deletion_status")
    op.execute(
        "DELETE FROM platform_settings WHERE key IN ("
        "'coppa_deletion_grace_days', "
        "'coppa_deletion_t7_reminder_enabled', "
        "'coppa_deletion_t1_reminder_enabled')"
    )
