"""Messaging router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
CONV_ID = uuid.uuid4()
STUDIO_ID = uuid.uuid4()
MSG_ID = uuid.uuid4()

CONV_ROW = {
    "id": CONV_ID,
    "studio_id": STUDIO_ID,
    "created_by": USER_A_ID,
    "created_at": NOW,
    "updated_at": NOW,
}

PARTICIPANT_ROW_A = {
    "conversation_id": CONV_ID,
    "user_id": USER_A_ID,
    "joined_at": NOW,
    "last_read_at": None,
}

PARTICIPANT_ROW_B = {
    "conversation_id": CONV_ID,
    "user_id": USER_B_ID,
    "joined_at": NOW,
    "last_read_at": None,
}

MSG_ROW = {
    "id": MSG_ID,
    "conversation_id": CONV_ID,
    "sender_id": USER_A_ID,
    "body": "Hello!",
    "created_at": NOW,
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


def test_create_conversation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.messaging as msg_mod

    monkeypatch.setattr(
        msg_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=CONV_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/conversations",
        json={"studio_id": str(STUDIO_ID), "participant_ids": [str(USER_B_ID)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["studio_id"] == str(STUDIO_ID)


def test_list_conversations(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.messaging as msg_mod

    monkeypatch.setattr(
        msg_mod, "rls_transaction", _make_rls_ctx(fetch_result=[CONV_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_conversation_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.messaging as msg_mod

    monkeypatch.setattr(
        msg_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/conversations/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_send_message(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.messaging as msg_mod

    monkeypatch.setattr(
        msg_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=MSG_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/conversations/{CONV_ID}/messages",
        json={"body": "Hello!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["body"] == "Hello!"


def test_list_messages(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.messaging as msg_mod

    monkeypatch.setattr(
        msg_mod, "rls_transaction", _make_rls_ctx(fetch_result=[MSG_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/conversations/{CONV_ID}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_mark_conversation_read(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.messaging as msg_mod

    monkeypatch.setattr(
        msg_mod, "rls_transaction", _make_rls_ctx(execute_result="UPDATE 1")
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/conversations/{CONV_ID}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


def test_unauthenticated_conversations_rejected(client: TestClient) -> None:
    resp = client.get("/conversations")
    assert resp.status_code == 401
