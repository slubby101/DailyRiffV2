"""Integration tests for resource endpoints against a real Supabase database."""

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


def _create_studio(client: TestClient, token: str, name: str) -> str:
    resp = client.post(
        "/studios",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@_needs_supabase()
def test_create_and_list_resources(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    studio_id = _create_studio(async_client, token, "resource-test-studio")

    resp = async_client.post(
        "/resources",
        json={
            "studio_id": studio_id,
            "title": "Music Theory 101",
            "url": "https://example.com/theory",
            "description": "Intro to theory",
            "category": "theory",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    resource = resp.json()
    assert resource["title"] == "Music Theory 101"
    assert resource["studio_id"] == studio_id
    resource_id = resource["id"]

    resp = async_client.get("/resources", headers=headers)
    assert resp.status_code == 200
    assert any(r["id"] == resource_id for r in resp.json())


@_needs_supabase()
def test_resource_rls_isolation(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token_a = make_test_jwt(user_id=USER_A_ID)
    token_b = make_test_jwt(user_id=USER_B_ID)

    studio_id = _create_studio(async_client, token_a, "rls-resource-studio")

    resp = async_client.post(
        "/resources",
        json={
            "studio_id": studio_id,
            "title": "Secret Resource",
            "url": "https://example.com/secret",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    resource_id = resp.json()["id"]

    resp = async_client.get(
        f"/resources/{resource_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


@_needs_supabase()
def test_update_resource(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    studio_id = _create_studio(async_client, token, "update-resource-studio")

    resp = async_client.post(
        "/resources",
        json={
            "studio_id": studio_id,
            "title": "Original Title",
            "url": "https://example.com/original",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    resource_id = resp.json()["id"]

    resp = async_client.patch(
        f"/resources/{resource_id}",
        json={"title": "Updated Title", "category": "updated"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["category"] == "updated"


@_needs_supabase()
def test_delete_resource(
    async_client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    headers = {"Authorization": f"Bearer {token}"}

    studio_id = _create_studio(async_client, token, "delete-resource-studio")

    resp = async_client.post(
        "/resources",
        json={
            "studio_id": studio_id,
            "title": "To Delete",
            "url": "https://example.com/delete",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    resource_id = resp.json()["id"]

    resp = async_client.delete(f"/resources/{resource_id}", headers=headers)
    assert resp.status_code == 204

    resp = async_client.get(f"/resources/{resource_id}", headers=headers)
    assert resp.status_code == 404
