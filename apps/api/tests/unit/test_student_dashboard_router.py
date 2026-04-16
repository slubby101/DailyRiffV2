"""Student dashboard router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
ASSIGNMENT_ID = uuid.uuid4()
RECORDING_ID = uuid.uuid4()


def _make_rls_ctx(*, fetch_results=None):
    """Create a fake rls_transaction that returns different results per call."""
    call_count = 0
    results = fetch_results or []

    @asynccontextmanager
    async def _fake(user_id):
        nonlocal call_count
        conn = AsyncMock()

        # Dashboard makes 4 fetch calls in order:
        # 1. practice_dates, 2. weekly_durations, 3. assignments, 4. recordings
        fetch_values = list(results)

        async def _fetch(*args, **kwargs):
            nonlocal call_count
            idx = call_count
            call_count += 1
            if idx < len(fetch_values):
                return fetch_values[idx]
            return []

        conn.fetch = AsyncMock(side_effect=_fetch)
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn
    return _fake


def _make_simple_rls_ctx(*, fetch_result=None):
    """Simple rls_transaction that always returns the same fetch result."""
    @asynccontextmanager
    async def _fake(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn
    return _fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_dashboard_returns_empty_state(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    monkeypatch.setattr(
        dash_mod, "rls_transaction", _make_rls_ctx(fetch_results=[[], [], [], []])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["streak"]["current_streak"] == 0
    assert data["streak"]["is_active"] is False
    assert data["streak"]["weekly_minutes"] == 0
    assert data["upcoming_assignments"] == []
    assert data["recent_recordings"] == []


def test_dashboard_computes_streak_from_recordings(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    practice_dates = [
        {"practice_date": date(2026, 4, 14)},
        {"practice_date": date(2026, 4, 15)},
        {"practice_date": date(2026, 4, 16)},
    ]
    weekly_durations = [
        {"duration_seconds": 600},
        {"duration_seconds": 900},
    ]

    monkeypatch.setattr(
        dash_mod, "rls_transaction",
        _make_rls_ctx(fetch_results=[practice_dates, weekly_durations, [], []])
    )
    # Pin today for deterministic test
    monkeypatch.setattr(dash_mod, "date", type("FakeDate", (date,), {
        "today": staticmethod(lambda: date(2026, 4, 16))
    }))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["streak"]["current_streak"] == 3
    assert data["streak"]["is_active"] is True
    assert data["streak"]["weekly_minutes"] == 25  # (600+900)//60


def test_dashboard_returns_upcoming_assignments(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    assignments = [
        {
            "id": ASSIGNMENT_ID,
            "title": "Scale practice",
            "due_date": date(2026, 4, 20),
            "status": "pending",
            "created_at": NOW,
        }
    ]

    monkeypatch.setattr(
        dash_mod, "rls_transaction",
        _make_rls_ctx(fetch_results=[[], [], assignments, []])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["upcoming_assignments"]) == 1
    assert data["upcoming_assignments"][0]["title"] == "Scale practice"


def test_dashboard_returns_recent_recordings(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    recordings = [
        {
            "id": RECORDING_ID,
            "assignment_id": ASSIGNMENT_ID,
            "duration_seconds": 600,
            "uploaded_at": NOW,
            "created_at": NOW,
        }
    ]

    monkeypatch.setattr(
        dash_mod, "rls_transaction",
        _make_rls_ctx(fetch_results=[[], [], [], recordings])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["recent_recordings"]) == 1
    assert data["recent_recordings"][0]["duration_seconds"] == 600


def test_streak_endpoint_returns_streak(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    practice_dates = [
        {"practice_date": date(2026, 4, 15)},
        {"practice_date": date(2026, 4, 16)},
    ]
    weekly_durations = [{"duration_seconds": 300}]

    monkeypatch.setattr(
        dash_mod, "rls_transaction",
        _make_rls_ctx(fetch_results=[practice_dates, weekly_durations])
    )
    monkeypatch.setattr(dash_mod, "date", type("FakeDate", (date,), {
        "today": staticmethod(lambda: date(2026, 4, 16))
    }))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/streak",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_streak"] == 2
    assert data["weekly_minutes"] == 5


def test_student_assignments_list(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    assignments = [
        {
            "id": ASSIGNMENT_ID,
            "title": "Chord progression",
            "due_date": date(2026, 4, 22),
            "status": "active",
            "created_at": NOW,
        }
    ]

    monkeypatch.setattr(
        dash_mod, "rls_transaction",
        _make_simple_rls_ctx(fetch_result=assignments)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/assignments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Chord progression"


def test_student_recordings_list(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.student_dashboard as dash_mod

    recordings = [
        {
            "id": RECORDING_ID,
            "assignment_id": None,
            "duration_seconds": 900,
            "uploaded_at": NOW,
            "created_at": NOW,
        }
    ]

    monkeypatch.setattr(
        dash_mod, "rls_transaction",
        _make_simple_rls_ctx(fetch_result=recordings)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/student/recordings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["duration_seconds"] == 900


def test_dashboard_requires_auth(client: TestClient) -> None:
    resp = client.get("/student/dashboard")
    assert resp.status_code == 401


def test_streak_requires_auth(client: TestClient) -> None:
    resp = client.get("/student/streak")
    assert resp.status_code == 401


def test_student_assignments_requires_auth(client: TestClient) -> None:
    resp = client.get("/student/assignments")
    assert resp.status_code == 401


def test_student_recordings_requires_auth(client: TestClient) -> None:
    resp = client.get("/student/recordings")
    assert resp.status_code == 401
