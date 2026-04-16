"""COPPA deletion router unit tests — initiate, confirm, cancel, status."""

from __future__ import annotations

import hashlib
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
PARENT_DB_ID = uuid.uuid4()
CHILD_ID = uuid.uuid4()
REQUEST_ID = uuid.uuid4()

PARENT_ROW = {"id": PARENT_DB_ID}
PARENT_CHILD_ROW = {"id": uuid.uuid4()}

DELETION_REQUEST_ROW = {
    "id": REQUEST_ID,
    "parent_id": PARENT_DB_ID,
    "child_id": CHILD_ID,
    "studio_id": STUDIO_ID,
    "status": "pending_confirmation",
    "confirmation_token_hash": hashlib.sha256(b"test-token").hexdigest(),
    "email_confirmed_at": None,
    "scheduled_delete_at": None,
    "t7_reminder_sent_at": None,
    "t1_reminder_sent_at": None,
    "completed_at": None,
    "cancelled_at": None,
    "created_at": NOW,
    "updated_at": NOW,
}


def _make_svc_ctx(*, fetchrow_results=None, fetchval_result=None, execute_result="INSERT 1"):
    """Mock service_transaction with sequential fetchrow returns."""
    call_idx = 0

    @asynccontextmanager
    async def _fake():
        nonlocal call_idx
        conn = AsyncMock()

        if fetchrow_results is not None:
            async def _fetchrow(*args, **kwargs):
                nonlocal call_idx
                if call_idx < len(fetchrow_results):
                    result = fetchrow_results[call_idx]
                    call_idx += 1
                    return result
                return None

            conn.fetchrow = AsyncMock(side_effect=_fetchrow)
        else:
            conn.fetchrow = AsyncMock(return_value=None)

        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        conn.fetch = AsyncMock(return_value=[])
        yield conn

    return _fake


@pytest.fixture(autouse=True)
def _patch_other_routers(monkeypatch):
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


# ---- Test 1: Initiate deletion for parent's child ----

def test_initiate_deletion_creates_request(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.coppa_deletion as mod

    result_row = {
        **DELETION_REQUEST_ROW,
        "confirmation_token": "test-token-plain",
    }

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
        fetchrow_results=[PARENT_ROW, PARENT_CHILD_ROW, result_row]
    ))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/coppa/deletion/initiate",
        json={
            "child_id": str(CHILD_ID),
            "studio_id": str(STUDIO_ID),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_confirmation"


# ---- Test 2: Initiate deletion rejects non-parent ----

def test_initiate_deletion_rejects_non_parent(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.coppa_deletion as mod

    # Parent lookup returns None
    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
        fetchrow_results=[None]
    ))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/coppa/deletion/initiate",
        json={
            "child_id": str(CHILD_ID),
            "studio_id": str(STUDIO_ID),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---- Test 3: Confirm deletion with valid token ----

def test_confirm_deletion_with_valid_token(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.coppa_deletion as mod

    confirmed_row = {
        **DELETION_REQUEST_ROW,
        "status": "scheduled",
        "email_confirmed_at": NOW,
        "scheduled_delete_at": NOW + timedelta(days=15),
    }

    # Parent lookup, then service returns confirmed
    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
        fetchrow_results=[PARENT_ROW, DELETION_REQUEST_ROW, confirmed_row]
    ))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/coppa/deletion/confirm",
        json={
            "request_id": str(REQUEST_ID),
            "confirmation_token": "test-token",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"


# ---- Test 4: Cancel deletion ----

def test_cancel_deletion(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.coppa_deletion as mod

    scheduled_row = {
        **DELETION_REQUEST_ROW,
        "status": "scheduled",
        "scheduled_delete_at": NOW + timedelta(days=10),
    }
    cancelled_row = {**scheduled_row, "status": "cancelled", "cancelled_at": NOW}

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
        fetchrow_results=[PARENT_ROW, scheduled_row, cancelled_row]
    ))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/coppa/deletion/{REQUEST_ID}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


# ---- Test 5: Get deletion status ----

def test_get_deletion_status(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.coppa_deletion as mod

    active_row = {
        **DELETION_REQUEST_ROW,
        "status": "scheduled",
        "scheduled_delete_at": NOW + timedelta(days=5),
    }

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
        fetchrow_results=[PARENT_ROW, active_row]
    ))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/coppa/deletion/status",
        params={"child_id": str(CHILD_ID), "studio_id": str(STUDIO_ID)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"


# ---- Test 6: Get status returns 404 when no active request ----

def test_get_deletion_status_no_active(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.coppa_deletion as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
        fetchrow_results=[PARENT_ROW, None]
    ))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/coppa/deletion/status",
        params={"child_id": str(CHILD_ID), "studio_id": str(STUDIO_ID)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---- Test 7: Unauthenticated access rejected ----

def test_unauthenticated_deletion_rejected(client: TestClient) -> None:
    resp = client.post(
        "/coppa/deletion/initiate",
        json={"child_id": str(CHILD_ID), "studio_id": str(STUDIO_ID)},
    )
    assert resp.status_code == 401
