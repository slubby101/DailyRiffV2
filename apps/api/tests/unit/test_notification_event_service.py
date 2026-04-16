"""NotificationEventService unit tests.

Tests event-type-aware notification dispatch: template resolution,
variable rendering, per-category/channel preference gating, and
fan-out via the Stage 0 NotificationService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from dailyriff_api.services.notification_events import (
    EventType,
    NotificationEventService,
)

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _mock_pool(template_row=None, pref_row=None):
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=template_row)
    pool.fetch = AsyncMock(return_value=[])
    return pool


@pytest.mark.asyncio
async def test_fire_event_resolves_template_and_renders_variables() -> None:
    """fire_event looks up the template by event_type and renders title/body with context variables."""
    template_row = {
        "event_type": "teacher.new_recording",
        "category": "recordings",
        "title_template": "New recording from {student_name}",
        "body_template": "{student_name} uploaded a recording for {assignment_title}",
        "channels": ["realtime", "expo_push", "web_push"],
        "enabled": True,
    }

    pool = _mock_pool(template_row=template_row)
    mock_notification_svc = AsyncMock()
    mock_notification_svc.send = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.TEACHER_NEW_RECORDING,
            user_id=USER_ID,
            context={"student_name": "Alice", "assignment_title": "Scales"},
        )

    mock_notification_svc.send.assert_called_once()
    call_args = mock_notification_svc.send.call_args
    payload = call_args[0][1]  # second positional arg
    assert payload.title == "New recording from Alice"
    assert payload.body == "Alice uploaded a recording for Scales"


@pytest.mark.asyncio
async def test_fire_event_skips_disabled_template() -> None:
    """fire_event does NOT call send when template.enabled is False."""
    template_row = {
        "event_type": "teacher.new_recording",
        "category": "recordings",
        "title_template": "New recording from {student_name}",
        "body_template": "body",
        "channels": ["realtime"],
        "enabled": False,
    }

    pool = _mock_pool(template_row=template_row)
    mock_notification_svc = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.TEACHER_NEW_RECORDING,
            user_id=USER_ID,
            context={"student_name": "Alice"},
        )

    mock_notification_svc.send.assert_not_called()


@pytest.mark.asyncio
async def test_fire_event_skips_when_no_template_found() -> None:
    """fire_event does NOT call send when no template exists for the event type."""
    pool = _mock_pool(template_row=None)
    mock_notification_svc = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.TEACHER_NEW_RECORDING,
            user_id=USER_ID,
            context={},
        )

    mock_notification_svc.send.assert_not_called()


@pytest.mark.asyncio
async def test_fire_event_skips_when_all_channels_disabled_by_prefs() -> None:
    """fire_event skips send when user has disabled all template channels for that category."""
    template_row = {
        "event_type": "teacher.new_recording",
        "category": "recordings",
        "title_template": "New recording",
        "body_template": "body",
        "channels": ["realtime", "expo_push"],
        "enabled": True,
    }

    pool = AsyncMock()
    # fetchrow returns the template
    pool.fetchrow = AsyncMock(return_value=template_row)
    # fetch returns category prefs — both channels disabled
    pool.fetch = AsyncMock(return_value=[
        {"channel": "realtime", "enabled": False},
        {"channel": "expo_push", "enabled": False},
    ])

    mock_notification_svc = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.TEACHER_NEW_RECORDING,
            user_id=USER_ID,
            context={},
        )

    mock_notification_svc.send.assert_not_called()


@pytest.mark.asyncio
async def test_fire_event_defaults_to_enabled_when_no_category_prefs() -> None:
    """When user has no category preferences, all template channels default to enabled."""
    template_row = {
        "event_type": "parent.streak_milestone",
        "category": "streaks",
        "title_template": "Streak milestone!",
        "body_template": "{student_name} hit a {streak_days}-day streak!",
        "channels": ["realtime", "expo_push", "web_push"],
        "enabled": True,
    }

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=template_row)
    pool.fetch = AsyncMock(return_value=[])  # no prefs → defaults enabled

    mock_notification_svc = AsyncMock()
    mock_notification_svc.send = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.PARENT_STREAK_MILESTONE,
            user_id=USER_ID,
            context={"student_name": "Bob", "streak_days": "7"},
        )

    mock_notification_svc.send.assert_called_once()
    payload = mock_notification_svc.send.call_args[0][1]
    assert payload.title == "Streak milestone!"
    assert "Bob" in payload.body
    assert "7-day" in payload.body


@pytest.mark.asyncio
async def test_fire_event_includes_event_type_in_payload_data() -> None:
    """Payload data includes event_type so clients can route/display correctly."""
    template_row = {
        "event_type": "student.new_assignment",
        "category": "assignments",
        "title_template": "New assignment",
        "body_template": "You have a new assignment: {assignment_title}",
        "channels": ["realtime"],
        "enabled": True,
    }

    pool = _mock_pool(template_row=template_row)
    mock_notification_svc = AsyncMock()
    mock_notification_svc.send = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.STUDENT_NEW_ASSIGNMENT,
            user_id=USER_ID,
            context={"assignment_title": "Scales practice"},
        )

    payload = mock_notification_svc.send.call_args[0][1]
    assert payload.data["event_type"] == "student.new_assignment"
    assert payload.data["assignment_title"] == "Scales practice"


def test_filter_channels_respects_partial_prefs() -> None:
    """Channels not mentioned in prefs default to enabled; explicitly disabled ones are filtered out."""
    result = NotificationEventService._filter_channels(
        ["realtime", "expo_push", "web_push"],
        {"expo_push": False},  # only expo disabled
    )
    assert result == ["realtime", "web_push"]


def test_event_type_enum_has_18_members() -> None:
    """The EventType enum has exactly 18 event types (15 from PRD + 3 cross-persona variants)."""
    assert len(EventType) == 18


@pytest.mark.asyncio
async def test_fire_event_partial_channel_prefs_sends_with_filtered_channels() -> None:
    """When user disables one channel via category prefs, send still fires for remaining channels."""
    template_row = {
        "event_type": "parent.assignment_due_24h",
        "category": "assignments",
        "title_template": "Assignment due tomorrow",
        "body_template": "{student_name}'s assignment is due tomorrow",
        "channels": ["realtime", "expo_push", "web_push"],
        "enabled": True,
    }

    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=template_row)
    # User disabled web_push for assignments category
    pool.fetch = AsyncMock(return_value=[
        {"channel": "web_push", "enabled": False},
    ])

    mock_notification_svc = AsyncMock()
    mock_notification_svc.send = AsyncMock()

    svc = NotificationEventService(notification_service=mock_notification_svc)

    with patch("dailyriff_api.services.notification_events.get_pool", return_value=pool):
        await svc.fire_event(
            event_type=EventType.PARENT_ASSIGNMENT_DUE_24H,
            user_id=USER_ID,
            context={"student_name": "Charlie"},
        )

    # Send is still called because realtime + expo_push are still enabled
    mock_notification_svc.send.assert_called_once()
