"""Core loop tables: assignments, recordings, acknowledgements, auto-ack trigger.

Revision ID: 0011_assignments_recordings
Revises: 0010_invitations
Create Date: 2026-04-16

PRD §Slice 11: The product's pivot — assign → record → auto-ack → review.
Ports Polymet's auto_acknowledge_assignment trigger verbatim.
Duration CHECK 300–3600 seconds on recordings preserved from Polymet.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_assignments_recordings"
down_revision = "0010_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- assignments -----------------------------------------------------------
    op.create_table(
        "assignments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pieces", postgresql.JSONB(), nullable=True),
        sa.Column("techniques", postgresql.JSONB(), nullable=True),
        sa.Column(
            "due_date",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("feedback_rating", sa.SmallInteger(), nullable=True),
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
            "status IN ('active', 'completed', 'overdue')",
            name="assignments_status_check",
        ),
        sa.CheckConstraint(
            "feedback_rating IS NULL OR (feedback_rating >= 1 AND feedback_rating <= 5)",
            name="assignments_feedback_rating_check",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="assignments_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="assignments_teacher_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="assignments_student_id_fkey",
        ),
    )
    op.create_index(
        "assignments_studio_id_idx",
        "assignments",
        ["studio_id"],
    )
    op.create_index(
        "assignments_teacher_id_idx",
        "assignments",
        ["teacher_id"],
    )
    op.create_index(
        "assignments_student_id_idx",
        "assignments",
        ["student_id"],
    )
    op.create_index(
        "assignments_status_idx",
        "assignments",
        ["status"],
    )

    # ---- recordings ------------------------------------------------------------
    op.create_table(
        "recordings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("r2_object_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        # Polymet duration CHECK: 300–3600 seconds (5–60 minutes)
        sa.CheckConstraint(
            "duration_seconds >= 300 AND duration_seconds <= 3600",
            name="recordings_duration_check",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="recordings_studio_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            name="recordings_student_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="SET NULL",
            name="recordings_assignment_id_fkey",
        ),
    )
    op.create_index(
        "recordings_studio_id_idx",
        "recordings",
        ["studio_id"],
    )
    op.create_index(
        "recordings_student_id_idx",
        "recordings",
        ["student_id"],
    )
    op.create_index(
        "recordings_assignment_id_idx",
        "recordings",
        ["assignment_id"],
    )

    # ---- assignment_acknowledgements -------------------------------------------
    op.create_table(
        "assignment_acknowledgements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recording_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'acknowledged')",
            name="acks_status_check",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="CASCADE",
            name="acks_assignment_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recordings.id"],
            ondelete="SET NULL",
            name="acks_recording_id_fkey",
        ),
    )
    op.create_index(
        "acks_assignment_id_idx",
        "assignment_acknowledgements",
        ["assignment_id"],
    )
    op.create_index(
        "acks_status_idx",
        "assignment_acknowledgements",
        ["status"],
    )

    # ---- auto_acknowledge_assignment trigger (ported from Polymet) --------------
    # Fires on recordings UPDATE: when uploaded_at transitions NULL → non-NULL,
    # flips matching ack rows from pending → acknowledged.
    op.execute("""
        CREATE OR REPLACE FUNCTION auto_acknowledge_assignment()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.uploaded_at IS NULL AND NEW.uploaded_at IS NOT NULL
               AND NEW.assignment_id IS NOT NULL THEN
                UPDATE assignment_acknowledgements
                SET status = 'acknowledged',
                    acknowledged_at = NEW.uploaded_at,
                    recording_id = NEW.id
                WHERE assignment_id = NEW.assignment_id
                  AND status = 'pending';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_auto_acknowledge_assignment
        AFTER UPDATE ON recordings
        FOR EACH ROW
        EXECUTE FUNCTION auto_acknowledge_assignment();
    """)

    # ---- RLS policies ----------------------------------------------------------
    # assignments: studio members can read; teacher who created can write
    op.execute("ALTER TABLE assignments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY assignments_select ON assignments FOR SELECT
        USING (
            studio_id IN (
                SELECT sm.studio_id FROM studio_members sm
                WHERE sm.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY assignments_insert ON assignments FOR INSERT
        WITH CHECK (
            teacher_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            AND studio_id IN (
                SELECT sm.studio_id FROM studio_members sm
                WHERE sm.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY assignments_update ON assignments FOR UPDATE
        USING (
            teacher_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
        )
    """)

    # recordings: studio members can read; student who recorded can insert
    op.execute("ALTER TABLE recordings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY recordings_select ON recordings FOR SELECT
        USING (
            studio_id IN (
                SELECT sm.studio_id FROM studio_members sm
                WHERE sm.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY recordings_insert ON recordings FOR INSERT
        WITH CHECK (
            student_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            AND studio_id IN (
                SELECT sm.studio_id FROM studio_members sm
                WHERE sm.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY recordings_update ON recordings FOR UPDATE
        USING (
            student_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
        )
    """)

    # assignment_acknowledgements: readable by assignment's studio members
    op.execute("ALTER TABLE assignment_acknowledgements ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY acks_select ON assignment_acknowledgements FOR SELECT
        USING (
            assignment_id IN (
                SELECT a.id FROM assignments a
                JOIN studio_members sm ON sm.studio_id = a.studio_id
                WHERE sm.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
    """)
    op.execute("""
        CREATE POLICY acks_insert ON assignment_acknowledgements FOR INSERT
        WITH CHECK (
            assignment_id IN (
                SELECT a.id FROM assignments a
                WHERE a.teacher_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid
            )
        )
    """)

    # ---- platform_settings seeds for rate limits --------------------------------
    op.execute("""
        INSERT INTO platform_settings (key, value_json, description, category)
        VALUES
            ('recordings_per_student_per_day', '10', 'Max recordings a student can upload per day', 'business_rule_caps'),
            ('assignments_per_teacher_per_day', '20', 'Max assignments a teacher can create per day', 'business_rule_caps')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_auto_acknowledge_assignment ON recordings")
    op.execute("DROP FUNCTION IF EXISTS auto_acknowledge_assignment()")
    op.execute("DROP TABLE IF EXISTS assignment_acknowledgements")
    op.execute("DROP TABLE IF EXISTS recordings")
    op.execute("DROP TABLE IF EXISTS assignments")
    op.execute(
        "DELETE FROM platform_settings WHERE key IN "
        "('recordings_per_student_per_day', 'assignments_per_teacher_per_day')"
    )
