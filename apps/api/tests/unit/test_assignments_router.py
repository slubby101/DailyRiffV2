"""Assignments router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
ASSIGNMENT_ID = uuid.uuid4()
ACK_ID = uuid.uuid4()

ASSIGNMENT_ROW = {
    "id": ASSIGNMENT_ID,
    "studio_id": STUDIO_ID,
    "teacher_id": USER_A_ID,
    "student_id": USER_B_ID,
    "title": "Practice scales",
    "description": "C major and G major",
    "pieces": ["Clair de Lune"],
    "techniques": ["legato"],
    "due_date": NOW + timedelta(days=7),
    "status": "active",
    "feedback_text": None,
    "feedback_rating": None,
    "created_at": NOW,
    "updated_at": NOW,
}

ACK_ROW = {
    "id": ACK_ID,
    "assignment_id": ASSIGNMENT_ID,
    "recording_id": None,
    "status": "pending",
    "acknowledged_at": None,
    "created_at": NOW,
}


def _make_rls_ctx(*, fetch_result=None, fetchrow_result=None, execute_result="UPDATE 1"):
    @asynccontextmanager
    async def _fake(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_other_routers(monkeypatch):
    """Prevent other routers from touching real DB."""
    import dailyriff_api.routers.preferences as pref_mod
    import dailyriff_api.routers.devices as dev_mod

    @asynccontextmanager
    async def _noop(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn

    monkeypatch.setattr(pref_mod, "rls_transaction", _noop)
    monkeypatch.setattr(dev_mod, "rls_transaction", _noop)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_create_assignment(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.assignments as asgn_mod

    # Stub studio membership check + insert
    @asynccontextmanager
    async def _ctx(user_id):
        conn = AsyncMock()
        # First fetch: studio_members check
        call_count = {"fetch": 0}

        async def _smart_fetch(*args, **kwargs):
            call_count["fetch"] += 1
            if call_count["fetch"] == 1:
                return [{"user_id": USER_A_ID}, {"user_id": USER_B_ID}]
            return []

        conn.fetch = _smart_fetch
        conn.fetchrow = AsyncMock(return_value=ASSIGNMENT_ROW)
        conn.execute = AsyncMock(return_value="INSERT 1")
        yield conn

    monkeypatch.setattr(asgn_mod, "rls_transaction", _ctx)

    @asynccontextmanager
    async def _svc_ctx():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"role": "teacher"})
        yield conn

    monkeypatch.setattr(asgn_mod, "service_transaction", _svc_ctx)

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/assignments",
        json={
            "studio_id": str(STUDIO_ID),
            "student_id": str(USER_B_ID),
            "title": "Practice scales",
            "description": "C major and G major",
            "pieces": ["Clair de Lune"],
            "techniques": ["legato"],
            "due_date": (NOW + timedelta(days=7)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Practice scales"


def test_list_assignments(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.assignments as asgn_mod

    monkeypatch.setattr(
        asgn_mod, "rls_transaction", _make_rls_ctx(fetch_result=[ASSIGNMENT_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/assignments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_assignment_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.assignments as asgn_mod

    monkeypatch.setattr(
        asgn_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/assignments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_add_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.assignments as asgn_mod

    updated_row = {**ASSIGNMENT_ROW, "feedback_text": "Great work!", "feedback_rating": 5}

    monkeypatch.setattr(
        asgn_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=updated_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/assignments/{ASSIGNMENT_ID}/feedback",
        json={"feedback_text": "Great work!", "feedback_rating": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["feedback_rating"] == 5


def test_list_pending_acknowledgements(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.assignments as asgn_mod

    monkeypatch.setattr(
        asgn_mod, "rls_transaction", _make_rls_ctx(fetch_result=[ACK_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/assignments/{ASSIGNMENT_ID}/acknowledgements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["status"] == "pending"


def test_unauthenticated_assignments_rejected(client: TestClient) -> None:
    resp = client.get("/assignments")
    assert resp.status_code == 401


def test_create_assignment_validation_rejects_past_due_date(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.assignments as asgn_mod

    monkeypatch.setattr(
        asgn_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=ASSIGNMENT_ROW)
    )

    @asynccontextmanager
    async def _svc_ctx():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"role": "teacher"})
        yield conn

    monkeypatch.setattr(asgn_mod, "service_transaction", _svc_ctx)

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/assignments",
        json={
            "studio_id": str(STUDIO_ID),
            "student_id": str(USER_B_ID),
            "title": "Practice scales",
            "due_date": (NOW - timedelta(days=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
