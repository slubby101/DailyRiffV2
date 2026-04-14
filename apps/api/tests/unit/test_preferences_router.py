"""Preferences router unit tests with mocked DB."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, time, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID

NOW = datetime.now(timezone.utc)


def _make_rls_ctx(*, fetchrow_result=None):
    @asynccontextmanager
    async def _fake(user_id):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetch = AsyncMock(return_value=[])
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_device_db(monkeypatch):
    import dailyriff_api.routers.devices as dev_mod

    @asynccontextmanager
    async def _noop(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        yield conn

    monkeypatch.setattr(dev_mod, "rls_transaction", _noop)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_get_preferences_returns_defaults_when_no_row(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.preferences as pref_mod

    monkeypatch.setattr(pref_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/notification-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["realtime_enabled"] is True
    assert body["expo_push_enabled"] is True
    assert body["web_push_enabled"] is True
    assert body["user_id"] == str(USER_A_ID)


def test_get_preferences_returns_stored_row(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.preferences as pref_mod

    stored = {
        "user_id": USER_A_ID,
        "realtime_enabled": False,
        "expo_push_enabled": True,
        "web_push_enabled": False,
        "quiet_hours_start": time(22, 0),
        "quiet_hours_end": time(7, 0),
        "updated_at": NOW,
    }
    monkeypatch.setattr(pref_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=stored))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/notification-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["realtime_enabled"] is False
    assert body["web_push_enabled"] is False


def test_patch_preferences_upserts(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.preferences as pref_mod

    upserted = {
        "user_id": USER_A_ID,
        "realtime_enabled": False,
        "expo_push_enabled": True,
        "web_push_enabled": True,
        "quiet_hours_start": None,
        "quiet_hours_end": None,
        "updated_at": NOW,
    }
    monkeypatch.setattr(
        pref_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=upserted)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        "/notification-preferences",
        json={"realtime_enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["realtime_enabled"] is False


def test_patch_empty_body_returns_current(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.preferences as pref_mod

    monkeypatch.setattr(pref_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        "/notification-preferences",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["realtime_enabled"] is True
