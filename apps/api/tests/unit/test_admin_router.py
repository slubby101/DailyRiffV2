"""Admin router unit tests — superadmin access control + CRUD for all studios."""

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

STUDIO_ROW = {
    "id": uuid.uuid4(),
    "name": "test-studio",
    "display_name": "Test Studio",
    "logo_url": None,
    "primary_color": None,
    "timezone": "America/New_York",
    "beta_cohort": False,
    "state": "pending",
    "created_at": NOW,
    "updated_at": NOW,
}


def _make_svc_ctx(*, fetch_result=None, fetchrow_result=None, execute_result="UPDATE 1"):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# --- Access control ---


def test_non_superadmin_cannot_list_all_studios(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get("/admin/studios", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_all_studios(client: TestClient) -> None:
    resp = client.get("/admin/studios")
    assert resp.status_code == 401


def test_non_superadmin_cannot_get_pending_studios(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get("/admin/verification-queue", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# --- List all studios ---


def test_superadmin_can_list_all_studios(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[STUDIO_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get("/admin/studios", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-studio"


def test_superadmin_can_list_empty_studios(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(fetch_result=[]))

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get("/admin/studios", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


# --- Get studio detail ---


def test_superadmin_can_get_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=STUDIO_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        f"/admin/studios/{STUDIO_ROW['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-studio"


def test_get_studio_returns_404_when_missing(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        f"/admin/studios/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Suspend studio ---


def test_superadmin_can_suspend_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    suspended_row = {**STUDIO_ROW, "state": "suspended"}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=suspended_row)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/studios/{STUDIO_ROW['id']}/suspend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "suspended"


def test_suspend_studio_returns_404_when_missing(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/studios/{uuid.uuid4()}/suspend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Verify studio ---


def test_superadmin_can_verify_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    active_row = {**STUDIO_ROW, "state": "active"}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=active_row)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/studios/{STUDIO_ROW['id']}/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "active"


# --- Pending studios (verification queue) ---


def test_superadmin_can_list_pending_studios(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.admin as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[STUDIO_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/admin/verification-queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["state"] == "pending"
