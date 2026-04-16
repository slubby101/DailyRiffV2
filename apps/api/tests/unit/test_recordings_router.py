"""Recordings router unit tests with mocked DB."""

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
RECORDING_ID = uuid.uuid4()
ASSIGNMENT_ID = uuid.uuid4()

RECORDING_ROW = {
    "id": RECORDING_ID,
    "studio_id": STUDIO_ID,
    "student_id": USER_A_ID,
    "assignment_id": ASSIGNMENT_ID,
    "r2_object_key": f"recordings/{STUDIO_ID}/{USER_A_ID}/{RECORDING_ID}.ogg",
    "mime_type": "audio/ogg; codecs=opus",
    "duration_seconds": 600,
    "file_size_bytes": None,
    "uploaded_at": None,
    "deleted_at": None,
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


def test_create_recording_returns_upload_url(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.recordings as rec_mod

    monkeypatch.setattr(
        rec_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=RECORDING_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/recordings",
        json={
            "studio_id": str(STUDIO_ID),
            "assignment_id": str(ASSIGNMENT_ID),
            "mime_type": "audio/ogg; codecs=opus",
            "duration_seconds": 600,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "recording_id" in data
    assert "upload_url" in data
    assert "r2_object_key" in data


def test_create_recording_rejects_unsupported_mime(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.recordings as rec_mod

    monkeypatch.setattr(
        rec_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=RECORDING_ROW)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/recordings",
        json={
            "studio_id": str(STUDIO_ID),
            "mime_type": "video/mp4",
            "duration_seconds": 600,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_confirm_upload(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.recordings as rec_mod

    uploaded_row = {**RECORDING_ROW, "uploaded_at": NOW, "file_size_bytes": 1024000}
    monkeypatch.setattr(
        rec_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=uploaded_row)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/recordings/{RECORDING_ID}/confirm-upload",
        json={"file_size_bytes": 1024000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["uploaded_at"] is not None


def test_list_recordings(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.recordings as rec_mod

    monkeypatch.setattr(
        rec_mod, "rls_transaction", _make_rls_ctx(fetch_result=[RECORDING_ROW])
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        "/recordings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_recording_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.recordings as rec_mod

    monkeypatch.setattr(
        rec_mod, "rls_transaction", _make_rls_ctx(fetchrow_result=None)
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/recordings/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_unauthenticated_recordings_rejected(client: TestClient) -> None:
    resp = client.get("/recordings")
    assert resp.status_code == 401


def test_create_recording_rejects_duration_under_300(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/recordings",
        json={
            "studio_id": str(STUDIO_ID),
            "mime_type": "audio/webm",
            "duration_seconds": 100,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_create_recording_rejects_duration_over_3600(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        "/recordings",
        json={
            "studio_id": str(STUDIO_ID),
            "mime_type": "audio/webm",
            "duration_seconds": 4000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
