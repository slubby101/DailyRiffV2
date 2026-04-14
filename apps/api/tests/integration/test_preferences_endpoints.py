"""Integration tests for notification preferences endpoints."""

from __future__ import annotations

import os
from typing import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import USER_A_ID


def _needs_supabase():
    return pytest.mark.skipif(
        not os.environ.get("SUPABASE_SERVICE_ROLE"),
        reason="Requires running Supabase (SUPABASE_SERVICE_ROLE not set)",
    )


@pytest.fixture
def async_client(seeded_users):
    from dailyriff_api.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@_needs_supabase()
def test_get_defaults_without_row(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.get("/notification-preferences", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["realtime_enabled"] is True
    assert body["expo_push_enabled"] is True
    assert body["web_push_enabled"] is True


@_needs_supabase()
def test_patch_upserts_preferences(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.patch(
        "/notification-preferences",
        json={"realtime_enabled": False},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["realtime_enabled"] is False
    assert body["expo_push_enabled"] is True

    resp = async_client.get("/notification-preferences", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["realtime_enabled"] is False
