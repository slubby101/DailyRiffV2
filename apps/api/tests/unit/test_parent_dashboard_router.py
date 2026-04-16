"""Parent dashboard router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
PARENT_ID = uuid.uuid4()
CHILD_USER_ID = uuid.uuid4()
PARENT_CHILD_ID = uuid.uuid4()
ASSIGNMENT_ID = uuid.uuid4()
LESSON_ID = uuid.uuid4()
OCCURRENCE_ID = uuid.uuid4()
RECORDING_ID = uuid.uuid4()
PAYMENT_ID = uuid.uuid4()

PARENT_ROW = {"id": PARENT_ID, "user_id": USER_A_ID, "studio_id": STUDIO_ID}

PARENT_CHILD_LINK = {
    "id": PARENT_CHILD_ID,
    "parent_id": PARENT_ID,
    "child_user_id": CHILD_USER_ID,
    "is_primary_contact": True,
    "can_manage_payments": True,
    "can_view_progress": True,
    "can_communicate_with_teacher": True,
    "studio_id": STUDIO_ID,
}

CHILD_ROW = {
    "parent_child_id": PARENT_CHILD_ID,
    "child_user_id": CHILD_USER_ID,
    "is_primary_contact": True,
    "can_manage_payments": True,
    "can_view_progress": True,
    "can_communicate_with_teacher": True,
    "studio_id": STUDIO_ID,
    "studio_name": "Mitchell Music Studio",
    "email": "student@test.com",
}


def _make_service_ctx(
    *,
    fetchrow_results=None,
    fetch_results=None,
    execute_result="UPDATE 1",
):
    """Create a fake service_transaction context manager with sequenced results."""
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
# Children list (dashboard)
# ---------------------------------------------------------------------------


def test_children_list_returns_children(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    # fetchrow calls: 1. _require_parent, 2. next_lesson (per child), 3. latest_assignment (per child)
    # fetch calls: 1. children_rows, 2. practice_rows (per child with can_view_progress)
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                PARENT_ROW,  # _require_parent
                {"start_date": date(2026, 4, 20)},  # next_lesson
                {"title": "Scale practice"},  # latest_assignment
            ],
            fetch_results=[
                [CHILD_ROW],  # children_rows
                [{"practice_date": date(2026, 4, 16)}],  # practice_rows for streak
            ],
        ),
    )
    # Pin today for deterministic streak
    monkeypatch.setattr(mod, "date", type("FakeDate", (date,), {
        "today": staticmethod(lambda: date(2026, 4, 16))
    }))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/parent/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["children"]) == 1
    child = data["children"][0]
    assert child["studio_name"] == "Mitchell Music Studio"
    assert child["next_lesson_date"] == "2026-04-20"
    assert child["latest_assignment_title"] == "Scale practice"
    assert child["current_streak"] == 1
    assert child["permissions"]["can_view_progress"] is True


def test_children_list_empty(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_ROW],
            fetch_results=[[]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/parent/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["children"] == []


def test_children_list_requires_parent(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[None]),  # not a parent
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/parent/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_children_list_requires_auth(client: TestClient) -> None:
    resp = client.get("/parent/children")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Child schedule
# ---------------------------------------------------------------------------


def test_child_schedule_returns_lessons(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    schedule_row = {
        "lesson_id": LESSON_ID,
        "occurrence_id": OCCURRENCE_ID,
        "start_date": date(2026, 4, 20),
        "start_time": "15:00",
        "end_time": "15:30",
        "duration_minutes": 30,
        "teacher_email": "teacher@test.com",
        "status": "scheduled",
    }

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_ROW, PARENT_CHILD_LINK],
            fetch_results=[[schedule_row]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/parent/children/{CHILD_USER_ID}/schedule",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["start_date"] == "2026-04-20"
    assert data[0]["duration_minutes"] == 30


def test_child_schedule_requires_parent_child_link(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_ROW, None],  # no parent-child link
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/parent/children/{CHILD_USER_ID}/schedule",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_child_schedule_requires_auth(client: TestClient) -> None:
    resp = client.get(f"/parent/children/{CHILD_USER_ID}/schedule")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Child progress
# ---------------------------------------------------------------------------


def test_child_progress_returns_streak_and_assignments(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[
                PARENT_ROW,  # _require_parent
                PARENT_CHILD_LINK,  # _verify_parent_child
                {"total": 5, "completed": 3},  # assignment counts
            ],
            fetch_results=[
                [  # practice_rows
                    {"practice_date": date(2026, 4, 15)},
                    {"practice_date": date(2026, 4, 16)},
                ],
                [  # weekly_durations
                    {"duration_seconds": 600},
                    {"duration_seconds": 900},
                ],
                [  # recording_rows
                    {
                        "id": RECORDING_ID,
                        "assignment_id": ASSIGNMENT_ID,
                        "duration_seconds": 600,
                        "uploaded_at": NOW,
                        "created_at": NOW,
                    }
                ],
            ],
        ),
    )
    monkeypatch.setattr(mod, "date", type("FakeDate", (date,), {
        "today": staticmethod(lambda: date(2026, 4, 16))
    }))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/parent/children/{CHILD_USER_ID}/progress",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_streak"] == 2
    assert data["is_active"] is True
    assert data["weekly_minutes"] == 25
    assert data["total_assignments"] == 5
    assert data["completed_assignments"] == 3
    assert len(data["recent_recordings"]) == 1


def test_child_progress_denied_without_permission(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    no_progress_link = {**PARENT_CHILD_LINK, "can_view_progress": False}
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_ROW, no_progress_link],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/parent/children/{CHILD_USER_ID}/progress",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()


def test_child_progress_requires_auth(client: TestClient) -> None:
    resp = client.get(f"/parent/children/{CHILD_USER_ID}/progress")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Child payments (read-only)
# ---------------------------------------------------------------------------


def test_child_payments_returns_balance_and_history(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    payment_row = {
        "id": PAYMENT_ID,
        "amount": Decimal("50.00"),
        "currency": "USD",
        "status": "pending",
        "method": "cash",
        "memo": "April lesson",
        "created_at": NOW,
    }
    balance_row = {
        "total_pending": Decimal("50.00"),
        "total_paid": Decimal("100.00"),
        "total_refunded": Decimal("0.00"),
    }

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_ROW, PARENT_CHILD_LINK, balance_row],
            fetch_results=[[payment_row]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/parent/children/{CHILD_USER_ID}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pending"] == "50.00"
    assert data["total_paid"] == "100.00"
    assert len(data["payments"]) == 1
    assert data["payments"][0]["memo"] == "April lesson"


def test_child_payments_denied_without_permission(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.parent_dashboard as mod

    no_payment_link = {**PARENT_CHILD_LINK, "can_manage_payments": False}
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_ROW, no_payment_link],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/parent/children/{CHILD_USER_ID}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "permission" in resp.json()["detail"].lower()


def test_child_payments_requires_auth(client: TestClient) -> None:
    resp = client.get(f"/parent/children/{CHILD_USER_ID}/payments")
    assert resp.status_code == 401
