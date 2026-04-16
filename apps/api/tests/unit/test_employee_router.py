"""Employee router unit tests — superadmin access control + CRUD."""

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

EMPLOYEE_ROW = {
    "id": uuid.uuid4(),
    "user_id": USER_A_ID,
    "role": "owner",
    "created_by": None,
    "notes": "Bootstrap owner",
    "created_at": NOW,
}


def _make_svc_ctx(*, fetch_result=None, fetchrow_result=None, fetchval_result=None, execute_result="INSERT 1"):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.employees as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_non_superadmin_gets_403(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get("/employees", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_unauthenticated_gets_401(client: TestClient) -> None:
    resp = client.get("/employees")
    assert resp.status_code == 401


def test_superadmin_can_list_employees(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.employees as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetch_result=[EMPLOYEE_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get("/employees", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["role"] == "owner"


def test_superadmin_can_create_employee(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.employees as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=EMPLOYEE_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        "/employees",
        json={
            "user_id": str(USER_A_ID),
            "role": "owner",
            "notes": "Bootstrap owner",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "owner"


def test_superadmin_can_get_employee_by_id(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.employees as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=EMPLOYEE_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        f"/employees/{EMPLOYEE_ROW['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"


def test_get_employee_returns_404_when_missing(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.employees as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        f"/employees/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_superadmin_can_update_employee(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.employees as mod

    updated = {**EMPLOYEE_ROW, "role": "support"}
    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=updated)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.patch(
        f"/employees/{EMPLOYEE_ROW['id']}",
        json={"role": "support"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "support"


def test_superadmin_can_delete_employee(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.employees as mod

    monkeypatch.setattr(
        mod, "service_transaction", _make_svc_ctx(fetchrow_result=EMPLOYEE_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.delete(
        f"/employees/{EMPLOYEE_ROW['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
