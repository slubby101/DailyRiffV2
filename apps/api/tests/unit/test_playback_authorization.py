"""Playback authorization policy — exhaustive persona × relationship matrix.

Tests verify can_play_recording() through its public interface.
Mock only at DB boundary (asyncpg connection).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, call

import pytest

from dailyriff_api.auth import CurrentUser

# IDs for test fixtures
STUDIO_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
STUDENT_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")
TEACHER_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
PARENT_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000001")
OWNER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000001")
ADMIN_ID = uuid.UUID("ffffffff-0000-0000-0000-000000000001")
PEER_STUDENT_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
OTHER_TEACHER_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000002")
RECORDING_ID = uuid.UUID("11111111-0000-0000-0000-000000000001")
IMPERSONATION_SESSION_ID = uuid.UUID("22222222-0000-0000-0000-000000000001")

RECORDING_ROW = {
    "id": RECORDING_ID,
    "studio_id": STUDIO_ID,
    "student_id": STUDENT_ID,
    "deleted_at": None,
}


def _user(uid, *, role="user", studio_id=None, impersonation_session_id=None):
    return CurrentUser(
        id=uid,
        email="test@example.com",
        role=role,
        studio_id=studio_id,
        impersonation_session_id=impersonation_session_id,
    )


def _conn_with_responses(*responses):
    """Build an AsyncMock conn where successive fetchrow calls return *responses*.

    Each call to conn.fetchrow returns the next item in *responses*.
    """
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=list(responses))
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def can_play():
    from dailyriff_api.services.playback_authorization import can_play_recording
    return can_play_recording


# ---- Allow-list: positive cases ----

@pytest.mark.asyncio
async def test_student_who_recorded_can_play(can_play):
    conn = _conn_with_responses()  # no DB queries needed for student self-check
    user = _user(STUDENT_ID)
    assert await can_play(conn, user, RECORDING_ROW) is True


@pytest.mark.asyncio
async def test_parent_with_can_view_progress_can_play(can_play):
    conn = _conn_with_responses(
        {"can_view_progress": True},  # parent_children query
    )
    user = _user(PARENT_ID)
    assert await can_play(conn, user, RECORDING_ROW) is True


@pytest.mark.asyncio
async def test_assigned_teacher_can_play(can_play):
    conn = _conn_with_responses(
        None,  # parent_children query → not a parent
        {"id": uuid.uuid4()},  # assignments query → has assignment with this student
    )
    user = _user(TEACHER_ID)
    assert await can_play(conn, user, RECORDING_ROW) is True


@pytest.mark.asyncio
async def test_studio_owner_can_play(can_play):
    conn = _conn_with_responses(
        None,  # parent_children → not a parent
        None,  # assignments → not a teacher of this student
        {"role": "owner"},  # studio_members → is owner
    )
    user = _user(OWNER_ID)
    assert await can_play(conn, user, RECORDING_ROW) is True


@pytest.mark.asyncio
async def test_superadmin_with_impersonation_can_play(can_play):
    conn = _conn_with_responses()  # no queries needed; impersonation short-circuits
    user = _user(
        ADMIN_ID,
        role="superadmin",
        impersonation_session_id=IMPERSONATION_SESSION_ID,
    )
    assert await can_play(conn, user, RECORDING_ROW) is True


@pytest.mark.asyncio
async def test_recording_in_grace_period_still_playable(can_play):
    """Pending-deletion recordings (deleted_at set) are playable during grace period."""
    from datetime import datetime, timezone

    deleted_row = {**RECORDING_ROW, "deleted_at": datetime.now(timezone.utc)}
    conn = _conn_with_responses()
    user = _user(STUDENT_ID)
    assert await can_play(conn, user, deleted_row) is True


# ---- Deny-list: negative cases ----

@pytest.mark.asyncio
async def test_parent_without_can_view_progress_denied(can_play):
    conn = _conn_with_responses(
        {"can_view_progress": False},  # parent row exists but perm off
        None,  # assignments → not a teacher
        None,  # studio_members → not owner
    )
    user = _user(PARENT_ID)
    assert await can_play(conn, user, RECORDING_ROW) is False


@pytest.mark.asyncio
async def test_superadmin_without_impersonation_denied(can_play):
    conn = _conn_with_responses(
        None,  # parent_children → no
        None,  # assignments → no
        None,  # studio_members → no (superadmin isn't a studio member)
    )
    user = _user(ADMIN_ID, role="superadmin")
    assert await can_play(conn, user, RECORDING_ROW) is False


@pytest.mark.asyncio
async def test_peer_student_denied(can_play):
    conn = _conn_with_responses(
        None,  # parent_children → no
        None,  # assignments → no
        None,  # studio_members → not owner (student role)
    )
    user = _user(PEER_STUDENT_ID)
    assert await can_play(conn, user, RECORDING_ROW) is False


@pytest.mark.asyncio
async def test_non_assigned_teacher_denied(can_play):
    conn = _conn_with_responses(
        None,  # parent_children → no
        None,  # assignments → no assignment with this student
        None,  # studio_members → not owner
    )
    user = _user(OTHER_TEACHER_ID)
    assert await can_play(conn, user, RECORDING_ROW) is False
