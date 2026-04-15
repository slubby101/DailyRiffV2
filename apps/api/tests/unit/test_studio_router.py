"""Studio router unit tests with mocked DB."""

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


def _make_rls_ctx(*, fetch_result=None, fetchrow_result=None, execute_result="UPDATE 1"):
    @asynccontextmanager
    async def _fake(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_other_routers(monkeypatch):
    import dailyriff_api.routers.preferences as pref_mod
    import dailyriff_api.routers.devices as dev_mod

    @asynccontextmanager
    async def _noop(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn

    monkeypatch.setattr(pref_mod, "rls_transaction", _noop)
    monkeypatch.setattr(dev_mod, "rls_transaction", _noop)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_list_studios_empty(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    monkeypatch.setattr(studio_mod, "rls_transaction", _make_rls_ctx(fetch_result=[]))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get("/studios", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_studios_returns_rows(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    monkeypatch.setattr(studio_mod, "rls_transaction", _make_rls_ctx(fetch_result=[STUDIO_ROW]))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get("/studios", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-studio"


def test_create_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=STUDIO_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/studios",
        json={"name": "test-studio"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "test-studio"


def test_get_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=STUDIO_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    studio_id = str(STUDIO_ROW["id"])
    resp = client.get(
        f"/studios/{studio_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-studio"


def test_get_studio_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_update_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    updated_row = {**STUDIO_ROW, "display_name": "Updated Studio"}
    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=updated_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ROW['id']}",
        json={"display_name": "Updated Studio"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Studio"


def test_update_studio_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{uuid.uuid4()}",
        json={"display_name": "Nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_suspend_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    suspended_row = {**STUDIO_ROW, "state": "suspended"}
    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=suspended_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ROW['id']}/suspend",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "suspended"


def test_verify_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.studios as studio_mod

    active_row = {**STUDIO_ROW, "state": "active"}
    monkeypatch.setattr(
        studio_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=active_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ROW['id']}/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "active"


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    resp = client.get("/studios")
    assert resp.status_code == 401
