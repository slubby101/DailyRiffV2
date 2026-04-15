"""Settings router unit tests — superadmin access control + CRUD."""

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

SETTING_ROW = {
    "id": uuid.uuid4(),
    "key": "max_recordings_per_day",
    "value_json": {"limit": 10},
    "description": "Max recordings per student per day",
    "category": "business_rule_caps",
    "updated_at": NOW,
    "updated_by": USER_A_ID,
}

LOG_ROW = {
    "id": uuid.uuid4(),
    "user_id": USER_A_ID,
    "action": "update",
    "entity_type": "platform_setting",
    "entity_id": "max_recordings_per_day",
    "details": {"new_value": {"limit": 5}},
    "created_at": NOW,
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
    import dailyriff_api.routers.settings as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_non_superadmin_gets_403(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get("/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_unauthenticated_gets_401(client: TestClient) -> None:
    resp = client.get("/settings")
    assert resp.status_code == 401


def test_superadmin_can_list_settings(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.settings as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[SETTING_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get("/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["key"] == "max_recordings_per_day"


def test_superadmin_can_get_setting_by_key(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.settings as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=SETTING_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/settings/max_recordings_per_day",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["key"] == "max_recordings_per_day"


def test_get_setting_returns_404_when_missing(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.settings as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/settings/nonexistent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_superadmin_can_update_setting(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.settings as mod

    updated_row = {**SETTING_ROW, "value_json": {"limit": 5}}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=updated_row)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.put(
        "/settings/max_recordings_per_day",
        json={"value_json": {"limit": 5}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["value_json"] == {"limit": 5}


def test_superadmin_can_create_setting(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.settings as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=SETTING_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        "/settings",
        json={
            "key": "max_recordings_per_day",
            "value_json": {"limit": 10},
            "category": "business_rule_caps",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["key"] == "max_recordings_per_day"


def test_superadmin_can_list_activity_logs(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.settings as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[LOG_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/settings/activity-logs/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action"] == "update"


def test_non_superadmin_cannot_create_setting(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        "/settings",
        json={
            "key": "test",
            "value_json": 1,
            "category": "rate_limits",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
