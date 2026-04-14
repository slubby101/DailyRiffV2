"""Integration tests for device endpoints against a real Supabase database."""

from __future__ import annotations

import os
from typing import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.conftest import SEED_PASSWORD, USER_A_EMAIL, USER_A_ID, USER_B_ID


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
def test_register_and_list_device(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.post(
        "/devices/register",
        json={"channel": "expo", "token": "ExponentPushToken[test]"},
        headers=headers,
    )
    assert resp.status_code == 201
    device = resp.json()
    assert device["channel"] == "expo"
    assert device["user_id"] == str(USER_A_ID)

    resp = async_client.get("/devices", headers=headers)
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) >= 1
    assert any(d["token"] == "ExponentPushToken[test]" for d in devices)


@_needs_supabase()
def test_delete_own_device(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.post(
        "/devices/register",
        json={"channel": "webpush", "token": "https://push.example.com/del-test",
              "keys": {"p256dh": "k1", "auth": "k2"}},
        headers=headers,
    )
    assert resp.status_code == 201
    device_id = resp.json()["id"]

    resp = async_client.delete(f"/devices/{device_id}", headers=headers)
    assert resp.status_code == 204


@_needs_supabase()
def test_user_cannot_delete_other_users_subscription(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token_a = make_test_jwt(user_id=USER_A_ID)
    token_b = make_test_jwt(user_id=USER_B_ID)

    resp = async_client.post(
        "/devices/register",
        json={"channel": "expo", "token": "ExponentPushToken[cross-user-test]"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    device_id = resp.json()["id"]

    resp = async_client.delete(
        f"/devices/{device_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
