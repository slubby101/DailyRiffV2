"""Notification templates + per-category/channel preferences.

Revision ID: 0007_notification_templates
Revises: 0006_messaging
Create Date: 2026-04-16

PRD §Slice 23: 15-event notification taxonomy on top of Stage 0's
3-channel NotificationService. notification_templates table drives copy,
channels, and target persona. notification_category_preferences extends
the existing notification_preferences with per-category + per-channel
toggles (defaults all on except weekly digests email-only).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_notification_templates"
down_revision = "0006_messaging"
branch_labels = None
depends_on = None


# 18 event types (15 unique events, some per-persona variants)
SEED_TEMPLATES = [
    # Teacher events
    {
        "event_type": "teacher.new_recording",
        "category": "recordings",
        "persona": "teacher",
        "title_template": "New recording from {student_name}",
        "body_template": "{student_name} uploaded a recording for {assignment_title}",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "postgres_trigger",
    },
    {
        "event_type": "teacher.new_message",
        "category": "messages",
        "persona": "teacher",
        "title_template": "New message from {sender_name}",
        "body_template": "{sender_name}: {message_preview}",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    {
        "event_type": "teacher.pending_code_join",
        "category": "studio_management",
        "persona": "teacher",
        "title_template": "New join request",
        "body_template": "{requester_name} wants to join {studio_name} via studio code",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    {
        "event_type": "teacher.attendance_needing_mark",
        "category": "attendance",
        "persona": "teacher",
        "title_template": "Attendance needs marking",
        "body_template": "{student_name}'s lesson on {lesson_date} needs attendance marked",
        "channels": ["realtime", "web_push"],
        "trigger_source": "pg_cron",
    },
    {
        "event_type": "teacher.weekly_overdue_digest",
        "category": "digests",
        "persona": "teacher",
        "title_template": "Weekly overdue assignments",
        "body_template": "{overdue_count} assignments are overdue across your students",
        "channels": ["web_push"],
        "trigger_source": "pg_cron",
    },
    # Parent events
    {
        "event_type": "parent.teacher_message",
        "category": "messages",
        "persona": "parent",
        "title_template": "Message from {teacher_name}",
        "body_template": "{teacher_name}: {message_preview}",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    {
        "event_type": "parent.assignment_due_24h",
        "category": "assignments",
        "persona": "parent",
        "title_template": "Assignment due tomorrow",
        "body_template": "{student_name}'s assignment \"{assignment_title}\" is due tomorrow",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "pg_cron",
    },
    {
        "event_type": "parent.assignment_acknowledged",
        "category": "assignments",
        "persona": "parent",
        "title_template": "Assignment acknowledged",
        "body_template": "{student_name}'s practice for \"{assignment_title}\" was recorded",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "postgres_trigger",
    },
    {
        "event_type": "parent.lesson_reminder",
        "category": "lessons",
        "persona": "parent",
        "title_template": "Lesson reminder",
        "body_template": "{student_name}'s lesson with {teacher_name} is {time_until}",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "pg_cron",
    },
    {
        "event_type": "parent.streak_milestone",
        "category": "streaks",
        "persona": "parent",
        "title_template": "Practice streak milestone!",
        "body_template": "{student_name} hit a {streak_days}-day practice streak!",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    # Student-13+ events
    {
        "event_type": "student.teacher_message",
        "category": "messages",
        "persona": "student",
        "title_template": "Message from {teacher_name}",
        "body_template": "{teacher_name}: {message_preview}",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    {
        "event_type": "student.new_assignment",
        "category": "assignments",
        "persona": "student",
        "title_template": "New assignment",
        "body_template": "You have a new assignment: {assignment_title}",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    {
        "event_type": "student.assignment_due_24h",
        "category": "assignments",
        "persona": "student",
        "title_template": "Assignment due tomorrow",
        "body_template": "Your assignment \"{assignment_title}\" is due tomorrow",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "pg_cron",
    },
    {
        "event_type": "student.assignment_acknowledged",
        "category": "assignments",
        "persona": "student",
        "title_template": "Practice acknowledged!",
        "body_template": "Your practice for \"{assignment_title}\" has been recorded",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "postgres_trigger",
    },
    {
        "event_type": "student.lesson_1h_before",
        "category": "lessons",
        "persona": "student",
        "title_template": "Lesson in 1 hour",
        "body_template": "Your lesson with {teacher_name} starts in 1 hour",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "pg_cron",
    },
    {
        "event_type": "student.streak_milestone",
        "category": "streaks",
        "persona": "student",
        "title_template": "Streak milestone!",
        "body_template": "You hit a {streak_days}-day practice streak! Keep it up!",
        "channels": ["realtime", "expo_push", "web_push"],
        "trigger_source": "fastapi_handler",
    },
    # Superadmin events
    {
        "event_type": "superadmin.daily_waitlist_digest",
        "category": "admin_digests",
        "persona": "superadmin",
        "title_template": "Daily waitlist digest",
        "body_template": "{new_count} new waitlist entries, {total_pending} total pending",
        "channels": ["web_push"],
        "trigger_source": "pg_cron",
    },
    {
        "event_type": "superadmin.verification_queue_overdue",
        "category": "admin_digests",
        "persona": "superadmin",
        "title_template": "Verification queue overdue",
        "body_template": "{overdue_count} studios pending verification for over 48 hours",
        "channels": ["web_push"],
        "trigger_source": "pg_cron",
    },
]


def upgrade() -> None:
    # ---- notification_templates -------------------------------------------
    op.create_table(
        "notification_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.Text(), nullable=False, unique=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("persona", sa.Text(), nullable=False),
        sa.Column("title_template", sa.Text(), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("channels", postgresql.JSONB(), nullable=False),
        sa.Column("trigger_source", sa.Text(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
            "persona IN ('teacher', 'parent', 'student', 'superadmin')",
            name="notification_templates_persona_check",
        ),
        sa.CheckConstraint(
            "trigger_source IN ('postgres_trigger', 'pg_cron', 'fastapi_handler')",
            name="notification_templates_trigger_source_check",
        ),
    )
    op.create_index(
        "notification_templates_category_idx",
        "notification_templates",
        ["category"],
    )
    op.create_index(
        "notification_templates_persona_idx",
        "notification_templates",
        ["persona"],
    )

    op.execute("ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY")
    op.execute(
        'CREATE POLICY "select_authenticated" ON notification_templates '
        "FOR SELECT TO authenticated USING (true)"
    )

    # Seed all 18 templates
    for t in SEED_TEMPLATES:
        channels_json = _json_array(t["channels"])
        # Escape single quotes in template strings for SQL
        title = t["title_template"].replace("'", "''")
        body = t["body_template"].replace("'", "''")
        op.execute(
            f"INSERT INTO notification_templates "
            f"(event_type, category, persona, title_template, body_template, channels, trigger_source) "
            f"VALUES ('{t['event_type']}', '{t['category']}', '{t['persona']}', "
            f"'{title}', '{body}', '{channels_json}'::jsonb, '{t['trigger_source']}')"
        )

    # ---- notification_category_preferences ---------------------------------
    op.create_table(
        "notification_category_preferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
            name="notification_category_preferences_user_id_fkey",
        ),
    )
    op.create_index(
        "notification_category_prefs_user_category_channel_key",
        "notification_category_preferences",
        ["user_id", "category", "channel"],
        unique=True,
    )

    op.execute(
        "ALTER TABLE notification_category_preferences ENABLE ROW LEVEL SECURITY"
    )
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
            f'CREATE POLICY "{action}_own" ON notification_category_preferences '
            + " ".join(clauses)
        )


def _json_array(items: list[str]) -> str:
    """Format a Python list as a Postgres JSON array literal."""
    inner = ", ".join(f'"{item}"' for item in items)
    return f"[{inner}]"


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_category_preferences")
    op.execute("DROP TABLE IF EXISTS notification_templates")
