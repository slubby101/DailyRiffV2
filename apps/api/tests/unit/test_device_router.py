"""Device router unit tests with mocked DB."""

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

DEVICE_ROW = {
    "id": uuid.uuid4(),
    "user_id": USER_A_ID,
    "channel": "expo",
    "token": "ExponentPushToken[test]",
    "keys": None,
    "user_agent": None,
    "created_at": NOW,
    "last_used_at": None,
}


def _make_rls_ctx(*, fetch_result=None, fetchrow_result=None, execute_result="DELETE 1"):
    @asynccontextmanager
    async def _fake(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.preferences as pref_mod

    @asynccontextmanager
    async def _noop(user_id):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn

    monkeypatch.setattr(pref_mod, "rls_transaction", _noop)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_list_devices_returns_rows(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.devices as dev_mod

    monkeypatch.setattr(dev_mod, "rls_transaction", _make_rls_ctx(fetch_result=[DEVICE_ROW]))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["channel"] == "expo"


def test_register_device_creates(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.devices as dev_mod

    monkeypatch.setattr(
        dev_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=DEVICE_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/devices/register",
        json={"channel": "expo", "token": "ExponentPushToken[test]"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["channel"] == "expo"


def test_delete_device_success(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.devices as dev_mod

    monkeypatch.setattr(
        dev_mod, "rls_transaction", _make_rls_ctx(execute_result="DELETE 1")
    )

    token = make_test_jwt(user_id=USER_A_ID)
    device_id = str(uuid.uuid4())
    resp = client.delete(
        f"/devices/{device_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


def test_delete_device_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.devices as dev_mod

    monkeypatch.setattr(
        dev_mod, "rls_transaction", _make_rls_ctx(execute_result="DELETE 0")
    )

    token = make_test_jwt(user_id=USER_A_ID)
    device_id = str(uuid.uuid4())
    resp = client.delete(
        f"/devices/{device_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
