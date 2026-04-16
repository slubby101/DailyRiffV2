"""Lessons router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
STUDENT_USER_ID = uuid.uuid4()
LESSON_ID = uuid.uuid4()
OCCURRENCE_ID = uuid.uuid4()
ABSENCE_ID = uuid.uuid4()
POLICY_ID = uuid.uuid4()

TEACHER_MEMBERSHIP = {"role": "teacher"}
STUDENT_MEMBERSHIP = {"role": "student"}
OWNER_MEMBERSHIP = {"role": "owner"}

LESSON_ROW = {
    "id": LESSON_ID,
    "studio_id": STUDIO_ID,
    "teacher_id": USER_A_ID,
    "student_id": STUDENT_USER_ID,
    "title": "Piano Lesson",
    "description": "Weekly piano",
    "start_time": time(15, 0),
    "duration_minutes": 30,
    "start_date": date(2026, 5, 4),
    "end_date": date(2026, 8, 31),
    "is_recurring": True,
    "cadence": "weekly",
    "day_of_week": 0,
    "cost": 50.00,
    "is_paid": False,
    "is_trial": False,
    "created_by": USER_A_ID,
    "created_at": NOW,
    "updated_at": NOW,
}

OCCURRENCE_ROW = {
    "id": OCCURRENCE_ID,
    "lesson_id": LESSON_ID,
    "studio_id": STUDIO_ID,
    "occurrence_date": date(2026, 5, 4),
    "start_time": time(15, 0),
    "duration_minutes": 30,
    "attendance_status": "scheduled",
    "marked_by": None,
    "marked_at": None,
    "teacher_notes": None,
    "progress_notes": None,
    "improvement_areas": None,
    "strengths": None,
    "next_focus": None,
    "cost": 50.00,
    "is_paid": False,
    "is_makeup": False,
    "makeup_for_id": None,
    "created_at": NOW,
    "updated_at": NOW,
}

ABSENCE_ROW = {
    "id": ABSENCE_ID,
    "occurrence_id": OCCURRENCE_ID,
    "studio_id": STUDIO_ID,
    "reported_by": STUDENT_USER_ID,
    "reason": "Sick",
    "status": "reported",
    "makeup_requested": True,
    "makeup_occurrence_id": None,
    "created_at": NOW,
    "updated_at": NOW,
}

POLICY_ROW = {
    "id": POLICY_ID,
    "studio_id": STUDIO_ID,
    "max_absences_per_term": 3,
    "makeup_window_days": 30,
    "auto_notify_after_absences": 2,
    "cancellation_notice_hours": 24,
    "created_at": NOW,
    "updated_at": NOW,
}


def _make_service_ctx(
    *,
    fetchrow_results=None,
    fetch_results=None,
    execute_result="UPDATE 1",
):
    if fetchrow_results is not None and not isinstance(fetchrow_results, list):
        fetchrow_results = [fetchrow_results]
    if fetch_results is not None and not isinstance(fetch_results, list):
        fetch_results = [fetch_results]

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        _fetchrow_idx = [0]
        _fetch_idx = [0]

        async def _fetchrow(*args, **kwargs):
            if fetchrow_results is None:
                return None
            idx = _fetchrow_idx[0]
            _fetchrow_idx[0] += 1
            if idx < len(fetchrow_results):
                return fetchrow_results[idx]
            return fetchrow_results[-1] if fetchrow_results else None

        async def _fetch(*args, **kwargs):
            if fetch_results is None:
                return []
            idx = _fetch_idx[0]
            _fetch_idx[0] += 1
            if idx < len(fetch_results):
                return fetch_results[idx]
            return fetch_results[-1] if fetch_results else []

        conn.fetchrow = _fetchrow
        conn.fetch = _fetch
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn

    return _fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Create lesson
# ---------------------------------------------------------------------------


def test_create_lesson(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,      # _require_teacher_or_owner
                {"user_id": STUDENT_USER_ID},  # student check
                LESSON_ROW,              # INSERT RETURNING
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/lessons",
        json={
            "studio_id": str(STUDIO_ID),
            "student_id": str(STUDENT_USER_ID),
            "title": "Piano Lesson",
            "start_time": "15:00:00",
            "duration_minutes": 30,
            "start_date": "2026-05-04",
            "end_date": "2026-08-31",
            "is_recurring": True,
            "cadence": "weekly",
            "day_of_week": 0,
            "cost": 50.00,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Piano Lesson"
    assert data["cadence"] == "weekly"


def test_create_lesson_student_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,  # _require_teacher_or_owner
                None,                # student not found
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/lessons",
        json={
            "studio_id": str(STUDIO_ID),
            "student_id": str(uuid.uuid4()),
            "title": "Piano",
            "start_time": "15:00:00",
            "duration_minutes": 30,
            "start_date": "2026-05-04",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_create_lesson_forbidden_for_students(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/lessons",
        json={
            "studio_id": str(STUDIO_ID),
            "student_id": str(STUDENT_USER_ID),
            "title": "Piano",
            "start_time": "15:00:00",
            "duration_minutes": 30,
            "start_date": "2026-05-04",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_create_recurring_without_day_of_week_fails(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,
                {"user_id": STUDENT_USER_ID},
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/lessons",
        json={
            "studio_id": str(STUDIO_ID),
            "student_id": str(STUDENT_USER_ID),
            "title": "Piano",
            "start_time": "15:00:00",
            "duration_minutes": 30,
            "start_date": "2026-05-04",
            "is_recurring": True,
            "cadence": "weekly",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# List lessons
# ---------------------------------------------------------------------------


def test_list_lessons(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP],  # any studio member
            fetch_results=[[LESSON_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/lessons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Get lesson
# ---------------------------------------------------------------------------


def test_get_lesson(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP, LESSON_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/lessons/{LESSON_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Piano Lesson"


def test_get_lesson_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/lessons/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete lesson
# ---------------------------------------------------------------------------


def test_delete_lesson(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            execute_result="DELETE 1",
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.delete(
        f"/studios/{STUDIO_ID}/lessons/{LESSON_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


def test_delete_lesson_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            execute_result="DELETE 0",
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.delete(
        f"/studios/{STUDIO_ID}/lessons/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Mark attendance
# ---------------------------------------------------------------------------


def test_mark_attendance_scheduled_to_present(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    marked_row = {**OCCURRENCE_ROW, "attendance_status": "present", "marked_by": USER_A_ID, "marked_at": NOW}

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,          # _require_teacher_or_owner
                {"attendance_status": "scheduled"},  # existing occurrence
                marked_row,                  # UPDATE RETURNING
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/occurrences/{OCCURRENCE_ID}/attendance",
        json={"attendance_status": "present"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["attendance_status"] == "present"


def test_mark_attendance_invalid_transition(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,
                {"attendance_status": "excused"},  # terminal state
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/occurrences/{OCCURRENCE_ID}/attendance",
        json={"attendance_status": "present"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "Cannot transition" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Report absence
# ---------------------------------------------------------------------------


def test_report_absence(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                STUDENT_MEMBERSHIP,   # _require_studio_member
                {"id": OCCURRENCE_ID},  # verify occurrence exists
                ABSENCE_ROW,          # INSERT RETURNING
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/occurrences/{OCCURRENCE_ID}/report-absence",
        json={"reason": "Sick", "makeup_requested": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["reason"] == "Sick"
    assert resp.json()["makeup_requested"] is True


# ---------------------------------------------------------------------------
# List absences
# ---------------------------------------------------------------------------


def test_list_absences(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP],
            fetch_results=[[ABSENCE_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/absences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Update absence status
# ---------------------------------------------------------------------------


def test_update_absence_status(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    acked = {**ABSENCE_ROW, "status": "acknowledged"}

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,
                {"status": "reported"},  # existing absence
                acked,                    # UPDATE RETURNING
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/absences/{ABSENCE_ID}?target_status=acknowledged",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


def test_update_absence_invalid_transition(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,
                {"status": "resolved"},  # terminal state
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/absences/{ABSENCE_ID}?target_status=reported",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Schedule makeup
# ---------------------------------------------------------------------------


def test_schedule_makeup(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    makeup_occurrence = {
        **OCCURRENCE_ROW,
        "id": uuid.uuid4(),
        "is_makeup": True,
        "makeup_for_id": OCCURRENCE_ID,
        "occurrence_date": date(2026, 5, 15),
    }
    makeup_absence = {
        **ABSENCE_ROW,
        "status": "makeup_scheduled",
        "makeup_occurrence_id": makeup_occurrence["id"],
    }

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                TEACHER_MEMBERSHIP,    # _require_teacher_or_owner
                ABSENCE_ROW,           # fetch absence
                OCCURRENCE_ROW,        # fetch original occurrence
                makeup_occurrence,     # INSERT makeup occurrence
                makeup_absence,        # UPDATE absence
            ],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/absences/{ABSENCE_ID}/schedule-makeup?makeup_date=2026-05-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "makeup_scheduled"


# ---------------------------------------------------------------------------
# Absence policy
# ---------------------------------------------------------------------------


def test_get_absence_policy(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP, POLICY_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/absence-policy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["max_absences_per_term"] == 3


def test_upsert_absence_policy(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    updated = {**POLICY_ROW, "max_absences_per_term": 5}

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, updated],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.put(
        f"/studios/{STUDIO_ID}/absence-policy",
        json={"max_absences_per_term": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["max_absences_per_term"] == 5


# ---------------------------------------------------------------------------
# Auth: unauthenticated
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.get(f"/studios/{STUDIO_ID}/lessons")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update lesson
# ---------------------------------------------------------------------------


def test_update_lesson(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    updated = {**LESSON_ROW, "title": "Guitar Lesson"}

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, updated],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/lessons/{LESSON_ID}",
        json={"title": "Guitar Lesson"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Guitar Lesson"


# ---------------------------------------------------------------------------
# List occurrences
# ---------------------------------------------------------------------------


def test_list_occurrences(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP],
            fetch_results=[[OCCURRENCE_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/occurrences?start=2026-05-01&end=2026-05-31",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Update notes
# ---------------------------------------------------------------------------


def test_update_occurrence_notes(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.lessons as mod

    noted = {**OCCURRENCE_ROW, "teacher_notes": "Good progress on arpeggios"}

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, noted],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/occurrences/{OCCURRENCE_ID}/notes",
        json={"teacher_notes": "Good progress on arpeggios"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["teacher_notes"] == "Good progress on arpeggios"
