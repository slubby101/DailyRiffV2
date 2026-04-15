"""Integration tests for studio endpoints against a real Supabase database."""

from __future__ import annotations

import os
from typing import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import USER_A_ID, USER_B_ID


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
def test_create_and_list_studio(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.post(
        "/studios",
        json={"name": "integration-test-studio", "display_name": "Integration Studio"},
        headers=headers,
    )
    assert resp.status_code == 201
    studio = resp.json()
    assert studio["name"] == "integration-test-studio"
    assert studio["state"] == "pending"
    studio_id = studio["id"]

    resp = async_client.get("/studios", headers=headers)
    assert resp.status_code == 200
    studios = resp.json()
    assert any(s["id"] == studio_id for s in studios)


@_needs_supabase()
def test_studio_rls_isolation(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token_a = make_test_jwt(user_id=USER_A_ID)
    token_b = make_test_jwt(user_id=USER_B_ID)

    resp = async_client.post(
        "/studios",
        json={"name": "rls-isolation-studio"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    studio_id = resp.json()["id"]

    resp = async_client.get(
        f"/studios/{studio_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


@_needs_supabase()
def test_update_studio(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.post(
        "/studios",
        json={"name": "update-test-studio"},
        headers=headers,
    )
    assert resp.status_code == 201
    studio_id = resp.json()["id"]

    resp = async_client.patch(
        f"/studios/{studio_id}",
        json={"display_name": "Updated Name", "primary_color": "#ff6600"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Name"
    assert resp.json()["primary_color"] == "#ff6600"


@_needs_supabase()
def test_suspend_and_verify_studio(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    resp = async_client.post(
        "/studios",
        json={"name": "suspend-test-studio"},
        headers=headers,
    )
    assert resp.status_code == 201
    studio_id = resp.json()["id"]

    resp = async_client.post(f"/studios/{studio_id}/suspend", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "suspended"

    resp = async_client.post(f"/studios/{studio_id}/verify", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "active"
