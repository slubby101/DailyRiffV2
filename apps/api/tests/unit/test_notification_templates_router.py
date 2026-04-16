"""Notification templates router unit tests with mocked DB."""

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


def _make_rls_ctx(*, fetch_result=None, fetchrow_result=None):
    @asynccontextmanager
    async def _fake(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        yield conn
    return _fake


def _make_service_ctx(*, fetch_result=None):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
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


TEMPLATE_ROW = {
    "id": uuid.uuid4(),
    "event_type": "teacher.new_recording",
    "category": "recordings",
    "persona": "teacher",
    "title_template": "New recording from {student_name}",
    "body_template": "{student_name} uploaded a recording",
    "channels": ["realtime", "expo_push", "web_push"],
    "trigger_source": "postgres_trigger",
    "enabled": True,
    "created_at": NOW,
    "updated_at": NOW,
}


def test_list_templates_returns_all(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.notification_templates as nt_mod

    monkeypatch.setattr(
        nt_mod, "service_transaction", _make_service_ctx(fetch_result=[TEMPLATE_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/notification-templates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["event_type"] == "teacher.new_recording"
    assert body[0]["channels"] == ["realtime", "expo_push", "web_push"]


PREF_ROW = {
    "id": uuid.uuid4(),
    "user_id": USER_A_ID,
    "category": "recordings",
    "channel": "expo_push",
    "enabled": False,
    "updated_at": NOW,
}


def test_list_category_preferences(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.notification_templates as nt_mod

    monkeypatch.setattr(
        nt_mod, "rls_transaction", _make_rls_ctx(fetch_result=[PREF_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/notification-category-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["category"] == "recordings"
    assert body[0]["channel"] == "expo_push"
    assert body[0]["enabled"] is False


def test_upsert_category_preference(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.notification_templates as nt_mod

    result_row = {
        "id": uuid.uuid4(),
        "user_id": USER_A_ID,
        "category": "recordings",
        "channel": "expo_push",
        "enabled": False,
        "updated_at": NOW,
    }

    monkeypatch.setattr(
        nt_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=result_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.put(
        "/notification-category-preferences",
        json={"category": "recordings", "channel": "expo_push", "enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "recordings"
    assert body["channel"] == "expo_push"
    assert body["enabled"] is False


def test_templates_require_auth(client: TestClient) -> None:
    resp = client.get("/notification-templates")
    assert resp.status_code == 401


def test_category_preferences_require_auth(client: TestClient) -> None:
    resp = client.get("/notification-category-preferences")
    assert resp.status_code == 401
