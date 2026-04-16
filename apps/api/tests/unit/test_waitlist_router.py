"""Waitlist router unit tests — public submission + superadmin management."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID

NOW = datetime.now(timezone.utc)

WAITLIST_ROW = {
    "id": uuid.uuid4(),
    "email": "studio@example.com",
    "name": "Jane Doe",
    "studio_name": "Jane's Music",
    "status": "pending",
    "ip_address": "127.0.0.1",
    "bypass_token": None,
    "reviewed_by": None,
    "reviewed_at": None,
    "rejection_reason": None,
    "studio_id": None,
    "created_at": NOW,
    "updated_at": NOW,
}

MESSAGE_ROW = {
    "id": uuid.uuid4(),
    "waitlist_entry_id": WAITLIST_ROW["id"],
    "sender_id": USER_A_ID,
    "body": "Welcome aboard!",
    "created_at": NOW,
}


def _make_svc_ctx(*, fetch_result=None, fetchrow_result=None, fetchval_result=None, execute_result="INSERT 1"):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture(autouse=True)
def _patch_captcha(monkeypatch):
    import dailyriff_api.routers.waitlist as mod

    async def _always_pass(*args, **kwargs):
        return True

    monkeypatch.setattr(mod, "verify_hcaptcha", _always_pass)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# --- Public submission ---


def test_waitlist_submit_creates_entry(
    client: TestClient, monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=WAITLIST_ROW)
    )

    resp = client.post("/waitlist", json={
        "email": "studio@example.com",
        "name": "Jane Doe",
        "studio_name": "Jane's Music",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "studio@example.com"
    assert data["status"] == "pending"


def test_waitlist_submit_missing_email_returns_422(client: TestClient) -> None:
    resp = client.post("/waitlist", json={"name": "Jane Doe"})
    assert resp.status_code == 422


def test_waitlist_submit_duplicate_email_returns_409(
    client: TestClient, monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    # fetchval returns existing entry count > 0
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchval_result=1)
    )

    resp = client.post("/waitlist", json={
        "email": "studio@example.com",
        "name": "Jane Doe",
    })
    assert resp.status_code == 409


# --- Superadmin: list waitlist ---


def test_non_superadmin_cannot_list_waitlist(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get("/admin/waitlist", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_waitlist(client: TestClient) -> None:
    resp = client.get("/admin/waitlist")
    assert resp.status_code == 401


def test_superadmin_can_list_waitlist(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[WAITLIST_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get("/admin/waitlist", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"] == "studio@example.com"


def test_superadmin_can_filter_waitlist_by_status(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[WAITLIST_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/admin/waitlist?status=pending",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# --- Superadmin: approve ---


def test_superadmin_can_approve_waitlist_entry(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    approved_row = {**WAITLIST_ROW, "status": "approved", "reviewed_by": USER_A_ID, "reviewed_at": NOW}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=approved_row)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/waitlist/{WAITLIST_ROW['id']}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approve_nonexistent_entry_returns_404(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/waitlist/{uuid.uuid4()}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Superadmin: reject ---


def test_superadmin_can_reject_waitlist_entry(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    rejected_row = {**WAITLIST_ROW, "status": "rejected", "reviewed_by": USER_A_ID, "reviewed_at": NOW, "rejection_reason": "Not a studio"}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=rejected_row)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/waitlist/{WAITLIST_ROW['id']}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Not a studio"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


# --- Superadmin: send message ---


def test_superadmin_can_send_waitlist_message(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(
            fetchrow_result=MESSAGE_ROW,
            fetchval_result=1,  # entry exists
        )
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/waitlist/{WAITLIST_ROW['id']}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": "Welcome aboard!"},
    )
    assert resp.status_code == 201
    assert resp.json()["body"] == "Welcome aboard!"


# --- Superadmin: list messages ---


def test_superadmin_can_list_waitlist_messages(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(
            fetch_result=[MESSAGE_ROW],
            fetchval_result=1,  # entry exists
        )
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        f"/admin/waitlist/{WAITLIST_ROW['id']}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- Bypass token ---


def test_superadmin_can_create_bypass_invite(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.waitlist as mod

    bypass_row = {**WAITLIST_ROW, "status": "approved", "bypass_token": "abc123"}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=bypass_row, fetchval_result=0)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        "/admin/waitlist/bypass",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "friend@example.com", "name": "Friend"},
    )
    assert resp.status_code == 201
    assert resp.json()["bypass_token"] is not None
