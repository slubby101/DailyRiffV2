"""Stage 1 / Slice 27 — Lessons + attendance + absences + makeups.

Revision ID: 0019_lessons_attendance
Revises: 0018_impersonation_sessions
Create Date: 2026-04-16

PRD §Slice 27: Lesson scheduling with studio-local TZ canon,
attendance tracking, absence reporting, makeup scheduling.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019_lessons_attendance"
down_revision = "0018_impersonation_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- ENUM types ---------------------------------------------------------
    op.execute(
        "CREATE TYPE lesson_cadence AS ENUM "
        "('weekly', 'biweekly', 'monthly', 'one_time');"
    )
    op.execute(
        "CREATE TYPE attendance_status AS ENUM "
        "('scheduled', 'present', 'absent', 'late', 'excused', 'cancelled');"
    )
    op.execute(
        "CREATE TYPE absence_status AS ENUM "
        "('reported', 'acknowledged', 'makeup_requested', 'makeup_scheduled', 'resolved');"
    )

    # ---- lessons ------------------------------------------------------------
    # Schedule stored against studio-local TZ (not UTC offset) for DST safety.
    # Recurrence rules use cadence + day_of_week; instances materialized by
    # lesson_service.generate_occurrences().
    op.execute("""
        CREATE TABLE lessons (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            studio_id       UUID NOT NULL REFERENCES studios(id) ON DELETE CASCADE,
            teacher_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            student_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            description     TEXT,
            -- Schedule (stored in studio-local TZ)
            start_time      TIME NOT NULL,
            duration_minutes INTEGER NOT NULL CHECK (duration_minutes BETWEEN 15 AND 180),
            start_date      DATE NOT NULL,
            end_date        DATE,
            is_recurring     BOOLEAN NOT NULL DEFAULT false,
            cadence         lesson_cadence NOT NULL DEFAULT 'one_time',
            day_of_week     INTEGER CHECK (day_of_week BETWEEN 0 AND 6),
            -- Cost
            cost            NUMERIC(10,2),
            is_paid         BOOLEAN NOT NULL DEFAULT false,
            is_trial        BOOLEAN NOT NULL DEFAULT false,
            -- Metadata
            created_by      UUID NOT NULL REFERENCES auth.users(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX lessons_studio_id_idx ON lessons (studio_id);")
    op.execute("CREATE INDEX lessons_teacher_id_idx ON lessons (teacher_id);")
    op.execute("CREATE INDEX lessons_student_id_idx ON lessons (student_id);")
    op.execute("CREATE INDEX lessons_start_date_idx ON lessons (start_date);")
    op.execute("ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;")
    # Studio members can read lessons in their studio
    op.execute("""
        CREATE POLICY "select_studio_member" ON lessons FOR SELECT TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members WHERE user_id = auth.uid()
            )
        );
    """)
    # Only owner/teacher can write
    op.execute("""
        CREATE POLICY "insert_teacher_owner" ON lessons FOR INSERT TO authenticated
        WITH CHECK (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = auth.uid() AND role IN ('owner', 'teacher')
            )
        );
    """)
    op.execute("""
        CREATE POLICY "update_teacher_owner" ON lessons FOR UPDATE TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = auth.uid() AND role IN ('owner', 'teacher')
            )
        );
    """)
    op.execute("""
        CREATE POLICY "delete_teacher_owner" ON lessons FOR DELETE TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = auth.uid() AND role IN ('owner', 'teacher')
            )
        );
    """)

    # ---- lesson_occurrences -------------------------------------------------
    # Materialized individual lesson dates from recurring templates.
    # Each occurrence can have independent attendance, notes, and cost tracking.
    op.execute("""
        CREATE TABLE lesson_occurrences (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lesson_id       UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            studio_id       UUID NOT NULL REFERENCES studios(id) ON DELETE CASCADE,
            occurrence_date DATE NOT NULL,
            start_time      TIME NOT NULL,
            duration_minutes INTEGER NOT NULL,
            -- Attendance
            attendance_status attendance_status NOT NULL DEFAULT 'scheduled',
            marked_by       UUID REFERENCES auth.users(id),
            marked_at       TIMESTAMPTZ,
            -- Notes (per-occurrence)
            teacher_notes   TEXT,
            progress_notes  TEXT,
            improvement_areas TEXT,
            strengths       TEXT,
            next_focus      TEXT,
            -- Cost (inherits from lesson but can be overridden)
            cost            NUMERIC(10,2),
            is_paid         BOOLEAN NOT NULL DEFAULT false,
            -- Makeup tracking
            is_makeup       BOOLEAN NOT NULL DEFAULT false,
            makeup_for_id   UUID REFERENCES lesson_occurrences(id),
            -- Metadata
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (lesson_id, occurrence_date)
        );
    """)
    op.execute("CREATE INDEX lo_studio_id_idx ON lesson_occurrences (studio_id);")
    op.execute("CREATE INDEX lo_lesson_id_idx ON lesson_occurrences (lesson_id);")
    op.execute("CREATE INDEX lo_occurrence_date_idx ON lesson_occurrences (occurrence_date);")
    op.execute("ALTER TABLE lesson_occurrences ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "select_studio_member" ON lesson_occurrences FOR SELECT TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members WHERE user_id = auth.uid()
            )
        );
    """)
    op.execute("""
        CREATE POLICY "modify_teacher_owner" ON lesson_occurrences FOR ALL TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = auth.uid() AND role IN ('owner', 'teacher')
            )
        );
    """)

    # ---- absences -----------------------------------------------------------
    op.execute("""
        CREATE TABLE absences (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            occurrence_id   UUID NOT NULL REFERENCES lesson_occurrences(id) ON DELETE CASCADE,
            studio_id       UUID NOT NULL REFERENCES studios(id) ON DELETE CASCADE,
            reported_by     UUID NOT NULL REFERENCES auth.users(id),
            reason          TEXT,
            status          absence_status NOT NULL DEFAULT 'reported',
            makeup_requested BOOLEAN NOT NULL DEFAULT false,
            makeup_occurrence_id UUID REFERENCES lesson_occurrences(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX absences_occurrence_id_idx ON absences (occurrence_id);")
    op.execute("CREATE INDEX absences_studio_id_idx ON absences (studio_id);")
    op.execute("ALTER TABLE absences ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "select_studio_member" ON absences FOR SELECT TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members WHERE user_id = auth.uid()
            )
        );
    """)
    op.execute("""
        CREATE POLICY "insert_any_member" ON absences FOR INSERT TO authenticated
        WITH CHECK (
            studio_id IN (
                SELECT studio_id FROM studio_members WHERE user_id = auth.uid()
            )
        );
    """)
    op.execute("""
        CREATE POLICY "update_teacher_owner" ON absences FOR UPDATE TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = auth.uid() AND role IN ('owner', 'teacher')
            )
        );
    """)

    # ---- studio_absence_policies --------------------------------------------
    op.execute("""
        CREATE TABLE studio_absence_policies (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            studio_id       UUID NOT NULL REFERENCES studios(id) ON DELETE CASCADE UNIQUE,
            max_absences_per_term INTEGER NOT NULL DEFAULT 3,
            makeup_window_days INTEGER NOT NULL DEFAULT 30,
            auto_notify_after_absences INTEGER NOT NULL DEFAULT 2,
            cancellation_notice_hours INTEGER NOT NULL DEFAULT 24,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("ALTER TABLE studio_absence_policies ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "select_studio_member" ON studio_absence_policies FOR SELECT TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members WHERE user_id = auth.uid()
            )
        );
    """)
    op.execute("""
        CREATE POLICY "modify_teacher_owner" ON studio_absence_policies FOR ALL TO authenticated
        USING (
            studio_id IN (
                SELECT studio_id FROM studio_members
                WHERE user_id = auth.uid() AND role IN ('owner', 'teacher')
            )
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS studio_absence_policies;")
    op.execute("DROP TABLE IF EXISTS absences;")
    op.execute("DROP TABLE IF EXISTS lesson_occurrences;")
    op.execute("DROP TABLE IF EXISTS lessons;")
    op.execute("DROP TYPE IF EXISTS absence_status;")
    op.execute("DROP TYPE IF EXISTS attendance_status;")
    op.execute("DROP TYPE IF EXISTS lesson_cadence;")
