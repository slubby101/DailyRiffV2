"""Event-type-aware notification dispatch.

Extends the Stage 0 NotificationService with:
- 15 event types mapped to notification templates
- Per-category/channel preference gating
- Template variable rendering

Stage 0's NotificationService.send() surface is preserved unchanged.
"""

from __future__ import annotations

import enum
import logging
from uuid import UUID

from dailyriff_api.db import get_pool
from dailyriff_api.services.notifications import NotificationPayload, NotificationService

logger = logging.getLogger(__name__)


class _SafeFormatMap(dict):
    """Restricts str.format_map to simple key lookup only — no attribute or index access."""

    def __getitem__(self, key: str) -> str:
        if not isinstance(key, str) or not key.isidentifier():
            raise KeyError(key)
        return super().__getitem__(key)

    def __getattr__(self, name: str) -> None:
        raise AttributeError(name)


class EventType(str, enum.Enum):
    # Teacher events
    TEACHER_NEW_RECORDING = "teacher.new_recording"
    TEACHER_NEW_MESSAGE = "teacher.new_message"
    TEACHER_PENDING_CODE_JOIN = "teacher.pending_code_join"
    TEACHER_ATTENDANCE_NEEDING_MARK = "teacher.attendance_needing_mark"
    TEACHER_WEEKLY_OVERDUE_DIGEST = "teacher.weekly_overdue_digest"
    # Parent events
    PARENT_TEACHER_MESSAGE = "parent.teacher_message"
    PARENT_ASSIGNMENT_DUE_24H = "parent.assignment_due_24h"
    PARENT_ASSIGNMENT_ACKNOWLEDGED = "parent.assignment_acknowledged"
    PARENT_LESSON_REMINDER = "parent.lesson_reminder"
    PARENT_STREAK_MILESTONE = "parent.streak_milestone"
    # Student-13+ events
    STUDENT_TEACHER_MESSAGE = "student.teacher_message"
    STUDENT_NEW_ASSIGNMENT = "student.new_assignment"
    STUDENT_ASSIGNMENT_DUE_24H = "student.assignment_due_24h"
    STUDENT_ASSIGNMENT_ACKNOWLEDGED = "student.assignment_acknowledged"
    STUDENT_LESSON_1H_BEFORE = "student.lesson_1h_before"
    # Note: student streak milestone shares parent.streak_milestone template logic
    # but fires separately — kept as distinct event for preference independence
    STUDENT_STREAK_MILESTONE = "student.streak_milestone"
    # Superadmin events
    SUPERADMIN_DAILY_WAITLIST_DIGEST = "superadmin.daily_waitlist_digest"
    SUPERADMIN_VERIFICATION_QUEUE_OVERDUE = "superadmin.verification_queue_overdue"


class NotificationEventService:
    """Resolves event types to templates, renders variables, checks preferences, dispatches."""

    def __init__(self, *, notification_service: NotificationService) -> None:
        self._notification_service = notification_service

    async def fire_event(
        self,
        event_type: EventType,
        user_id: UUID,
        context: dict[str, str] | None = None,
    ) -> None:
        template = await self._get_template(event_type)
        if template is None or not template["enabled"]:
            logger.info("No enabled template for %s — skipping", event_type.value)
            return

        ctx = context or {}
        try:
            title = template["title_template"].format_map(
                _SafeFormatMap(ctx)
            )
            body = template["body_template"].format_map(
                _SafeFormatMap(ctx)
            )
        except (KeyError, ValueError, IndexError) as exc:
            logger.error("Template render failed for %s: %s", event_type.value, exc)
            return

        category = template["category"]
        channels = template["channels"]

        prefs = await self._get_category_preferences(user_id, category)

        enabled_channels = self._filter_channels(channels, prefs)
        if not enabled_channels:
            logger.info("All channels disabled for %s/%s — skipping", event_type.value, category)
            return

        payload = NotificationPayload(
            title=title,
            body=body,
            data={"event_type": event_type.value, **(ctx)},
        )

        await self._notification_service.send(user_id, payload)

    async def _get_template(self, event_type: EventType) -> dict | None:
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT event_type, category, title_template, body_template, "
            "channels, enabled FROM notification_templates WHERE event_type = $1",
            event_type.value,
        )
        return dict(row) if row else None

    async def _get_category_preferences(
        self, user_id: UUID, category: str
    ) -> dict[str, bool]:
        pool = get_pool()
        rows = await pool.fetch(
            "SELECT channel, enabled FROM notification_category_preferences "
            "WHERE user_id = $1 AND category = $2",
            user_id,
            category,
        )
        return {row["channel"]: row["enabled"] for row in rows}

    @staticmethod
    def _filter_channels(
        template_channels: list[str], prefs: dict[str, bool]
    ) -> list[str]:
        """Return channels enabled by both template and user preferences.

        If no per-category preference exists for a channel, it defaults to enabled.
        """
        return [ch for ch in template_channels if prefs.get(ch, True)]
