"""Auth middleware behaviors — verified through HTTP calls against the app."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import DEFAULT_JWT_SECRET


@asynccontextmanager
async def _fake_rls_transaction(user_id):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    yield conn


@pytest.fixture(autouse=True)
def _mock_db(monkeypatch):
    """Patch rls_transaction so unit tests don't require a live database."""
    import dailyriff_api.routers.devices as dev_mod
    import dailyriff_api.routers.preferences as pref_mod

    monkeypatch.setattr(dev_mod, "rls_transaction", _fake_rls_transaction)
    monkeypatch.setattr(pref_mod, "rls_transaction", _fake_rls_transaction)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_is_public(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "git_sha" in body


def test_401_on_missing_token(client: TestClient) -> None:
    resp = client.get("/devices")
    assert resp.status_code == 401


def test_401_on_expired_token(client: TestClient) -> None:
    now = int(time.time())
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "expired@dailyriff.local",
            "aud": "authenticated",
            "app_metadata": {"role": "user"},
            "iat": now - 7200,
            "exp": now - 3600,
        },
        DEFAULT_JWT_SECRET,
        algorithm="HS256",
    )
    resp = client.get("/devices", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_401_on_malformed_token(client: TestClient) -> None:
    resp = client.get("/devices", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


def test_200_on_valid_token(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt()
    resp = client.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
