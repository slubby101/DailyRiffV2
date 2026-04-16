"""Resource router unit tests with mocked DB."""

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
STUDIO_ID = uuid.uuid4()

RESOURCE_ROW = {
    "id": uuid.uuid4(),
    "studio_id": STUDIO_ID,
    "title": "Music Theory Basics",
    "url": "https://example.com/theory",
    "description": "Intro to music theory",
    "category": "theory",
    "created_by": USER_A_ID,
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
    import dailyriff_api.routers.studios as studio_mod

    @asynccontextmanager
    async def _noop(user_id):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn

    monkeypatch.setattr(pref_mod, "rls_transaction", _noop)
    monkeypatch.setattr(dev_mod, "rls_transaction", _noop)
    monkeypatch.setattr(studio_mod, "rls_transaction", _noop)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_list_resources_empty(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(res_mod, "rls_transaction", _make_rls_ctx(fetch_result=[]))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get("/resources", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_resources_returns_rows(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(res_mod, "rls_transaction", _make_rls_ctx(fetch_result=[RESOURCE_ROW]))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get("/resources", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Music Theory Basics"


def test_create_resource(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=RESOURCE_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/resources",
        json={
            "studio_id": str(STUDIO_ID),
            "title": "Music Theory Basics",
            "url": "https://example.com/theory",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Music Theory Basics"


def test_get_resource(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=RESOURCE_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/resources/{RESOURCE_ROW['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Music Theory Basics"


def test_get_resource_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/resources/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_update_resource(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    updated_row = {**RESOURCE_ROW, "title": "Advanced Theory"}
    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=updated_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/resources/{RESOURCE_ROW['id']}",
        json={"title": "Advanced Theory"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Advanced Theory"


def test_update_resource_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/resources/{uuid.uuid4()}",
        json={"title": "Nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_resource(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(execute_result="DELETE 1")
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.delete(
        f"/resources/{RESOURCE_ROW['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


def test_delete_resource_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.resources as res_mod

    monkeypatch.setattr(
        res_mod, "rls_transaction", _make_rls_ctx(execute_result="DELETE 0")
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.delete(
        f"/resources/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    resp = client.get("/resources")
    assert resp.status_code == 401
