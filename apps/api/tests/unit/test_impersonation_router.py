"""Impersonation router unit tests — start/end sessions, scope restrictions,
Account Access Log, and auth middleware impersonation header wiring.
"""

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
SESSION_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

SESSION_ROW = {
    "id": SESSION_ID,
    "impersonator_user_id": USER_A_ID,
    "target_user_id": USER_B_ID,
    "studio_id": None,
    "reason": "Investigating support ticket #123",
    "mode": "silent",
    "ip_address": "127.0.0.1",
    "user_agent": "test-agent",
    "started_at": NOW,
    "ended_at": None,
    "notification_sent_at": None,
}


def _make_svc_ctx(*, fetch_result=None, fetchrow_result=None, fetchval_result=None):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock()
        yield conn
    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.impersonation as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _superadmin_headers(make_test_jwt: Callable[..., str]) -> dict:
    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    return {"Authorization": f"Bearer {token}"}


def _user_headers(make_test_jwt: Callable[..., str]) -> dict:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    return {"Authorization": f"Bearer {token}"}


# --- Access control ---


def test_non_superadmin_cannot_start_impersonation(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": "test"},
        headers=_user_headers(make_test_jwt),
    )
    assert resp.status_code == 403


def test_unauthenticated_cannot_start_impersonation(client: TestClient) -> None:
    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": "test"},
    )
    assert resp.status_code == 401


def test_non_superadmin_cannot_end_impersonation(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    resp = client.post(
        f"/admin/impersonation/{SESSION_ID}/end",
        headers=_user_headers(make_test_jwt),
    )
    assert resp.status_code == 403


def test_non_superadmin_cannot_get_active_session(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    resp = client.get(
        "/admin/impersonation/active",
        headers=_user_headers(make_test_jwt),
    )
    assert resp.status_code == 403


# --- Start impersonation ---


def test_start_impersonation_success(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        # target user exists
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": USER_B_ID},  # target user check
            None,  # no active session
            SESSION_ROW,  # INSERT RETURNING
        ])
        conn.execute = AsyncMock()
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": "Investigating support ticket #123", "mode": "silent"},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(SESSION_ID)
    assert body["target_user_id"] == str(USER_B_ID)
    assert body["reason"] == "Investigating support ticket #123"
    assert body["mode"] == "silent"
    assert body["ended_at"] is None


def test_start_impersonation_requires_reason(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": ""},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 422


def test_start_impersonation_reason_required_field(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 422


def test_start_impersonation_cannot_impersonate_self(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod
    import dailyriff_api.services.impersonation_service as svc

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{USER_A_ID}/start",
        json={"reason": "testing"},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower()


def test_start_impersonation_target_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)  # target not found
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": "testing"},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_start_impersonation_active_session_conflict(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": USER_B_ID},  # target exists
            {"id": SESSION_ID},  # active session exists
        ])
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": "testing"},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


# --- End impersonation ---


def test_end_impersonation_success(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    ended_session = {**SESSION_ROW, "ended_at": NOW}

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=ended_session)
        conn.execute = AsyncMock()
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{SESSION_ID}/end",
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ended_at"] is not None


def test_end_impersonation_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{SESSION_ID}/end",
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 404


# --- Active session ---


def test_get_active_session_returns_session(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=SESSION_ROW)
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.get(
        "/admin/impersonation/active",
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(SESSION_ID)


def test_get_active_session_returns_null_when_none(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    resp = client.get(
        "/admin/impersonation/active",
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 200
    # fetchrow returns None from default mock, so no active session


# --- Account Access Log ---


def test_account_access_log_returns_entries(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as imp_mod

    log_rows = [
        {
            "session_id": SESSION_ID,
            "impersonator_user_id": USER_A_ID,
            "reason": "Support ticket",
            "mode": "silent",
            "started_at": NOW,
            "ended_at": NOW,
            "playback_count": 3,
        }
    ]

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=log_rows)
        yield conn

    monkeypatch.setattr(imp_mod, "service_transaction", _fake)

    token = make_test_jwt(user_id=USER_B_ID, role="user")
    resp = client.get(
        "/account-access-log",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["session_id"] == str(SESSION_ID)
    assert body[0]["playback_count"] == 3


def test_account_access_log_empty_for_no_sessions(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_B_ID, role="user")
    resp = client.get(
        "/account-access-log",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_account_access_log_requires_auth(client: TestClient) -> None:
    resp = client.get("/account-access-log")
    assert resp.status_code == 401


# --- Scope restriction (require_not_impersonating) ---


def test_require_not_impersonating_blocks_impersonating_user() -> None:
    from dailyriff_api.auth import CurrentUser, require_not_impersonating

    user = CurrentUser(
        id=USER_B_ID,
        email=None,
        role="superadmin",
        impersonation_session_id=SESSION_ID,
    )
    with pytest.raises(Exception) as exc_info:
        require_not_impersonating(user)
    assert exc_info.value.status_code == 403
    assert "impersonation" in exc_info.value.detail.lower()


def test_require_not_impersonating_allows_normal_user() -> None:
    from dailyriff_api.auth import CurrentUser, require_not_impersonating

    user = CurrentUser(
        id=USER_B_ID,
        email="test@example.com",
        role="user",
    )
    result = require_not_impersonating(user)
    assert result.id == USER_B_ID


# --- Impersonation service unit tests ---


@pytest.mark.asyncio
async def test_service_start_validates_not_self() -> None:
    from dailyriff_api.services.impersonation_service import start_session

    conn = AsyncMock()
    with pytest.raises(ValueError, match="yourself"):
        await start_session(
            conn,
            impersonator_id=USER_A_ID,
            target_user_id=USER_A_ID,
            reason="testing",
        )


@pytest.mark.asyncio
async def test_service_start_validates_target_exists() -> None:
    from dailyriff_api.services.impersonation_service import start_session

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await start_session(
            conn,
            impersonator_id=USER_A_ID,
            target_user_id=USER_B_ID,
            reason="testing",
        )


@pytest.mark.asyncio
async def test_service_start_validates_no_active_session() -> None:
    from dailyriff_api.services.impersonation_service import start_session

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[
        {"id": USER_B_ID},  # target exists
        {"id": SESSION_ID},  # active session exists
    ])
    with pytest.raises(ValueError, match="already exists"):
        await start_session(
            conn,
            impersonator_id=USER_A_ID,
            target_user_id=USER_B_ID,
            reason="testing",
        )


@pytest.mark.asyncio
async def test_service_end_validates_session_exists() -> None:
    from dailyriff_api.services.impersonation_service import end_session

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="No active session"):
        await end_session(
            conn,
            session_id=SESSION_ID,
            impersonator_id=USER_A_ID,
        )


@pytest.mark.asyncio
async def test_service_validate_session_returns_none_for_invalid() -> None:
    from dailyriff_api.services.impersonation_service import validate_session

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    result = await validate_session(conn, session_id=SESSION_ID)
    assert result is None


@pytest.mark.asyncio
async def test_service_validate_session_returns_dict_for_active() -> None:
    from dailyriff_api.services.impersonation_service import validate_session

    session_data = {
        "id": SESSION_ID,
        "impersonator_user_id": USER_A_ID,
        "target_user_id": USER_B_ID,
        "mode": "silent",
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=session_data)
    result = await validate_session(conn, session_id=SESSION_ID)
    assert result is not None
    assert result["target_user_id"] == USER_B_ID


# --- Blocked actions ---


def test_blocked_actions_list_is_complete() -> None:
    from dailyriff_api.services.impersonation_service import (
        BLOCKED_ACTIONS,
        is_action_blocked_during_impersonation,
    )

    expected = {
        "change_password",
        "delete_account",
        "change_email",
        "change_2fa",
        "authorize_oauth",
        "delete_recording",
        "delete_message",
        "delete_child_data",
    }
    assert BLOCKED_ACTIONS == expected
    for action in expected:
        assert is_action_blocked_during_impersonation(action)
    assert not is_action_blocked_during_impersonation("view_recording")


# --- Auth middleware impersonation header ---


@pytest.mark.asyncio
async def test_auth_rejects_impersonation_header_from_non_superadmin(
    make_test_jwt: Callable[..., str],
) -> None:
    from fastapi.security import HTTPAuthorizationCredentials
    from unittest.mock import MagicMock

    from dailyriff_api.auth import get_current_user

    token = make_test_jwt(user_id=USER_A_ID, role="user")
    creds = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    request = MagicMock()
    request.headers = {"x-impersonation-session": str(SESSION_ID)}

    with pytest.raises(Exception) as exc_info:
        await get_current_user(creds, request=request)
    assert exc_info.value.status_code == 403
    assert "superadmin" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_auth_rejects_invalid_impersonation_session_id(
    make_test_jwt: Callable[..., str],
) -> None:
    from fastapi.security import HTTPAuthorizationCredentials
    from unittest.mock import MagicMock

    from dailyriff_api.auth import get_current_user

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    creds = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    request = MagicMock()
    request.headers = {"x-impersonation-session": "not-a-uuid"}

    with pytest.raises(Exception) as exc_info:
        await get_current_user(creds, request=request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_rejects_expired_impersonation_session(
    make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    from fastapi.security import HTTPAuthorizationCredentials
    from unittest.mock import MagicMock

    from dailyriff_api.auth import get_current_user
    import dailyriff_api.services.impersonation_service as svc

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    creds = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    request = MagicMock()
    request.headers = {"x-impersonation-session": str(SESSION_ID)}

    # Session not found (expired/ended)
    async def fake_validate(conn, *, session_id):
        return None

    monkeypatch.setattr(svc, "validate_session", fake_validate)

    @asynccontextmanager
    async def _fake():
        yield AsyncMock()

    import dailyriff_api.db as db_mod
    monkeypatch.setattr(db_mod, "_pool", AsyncMock())

    # We need to mock service_transaction at the module level where it's imported
    import dailyriff_api.auth as auth_mod
    # The import is inside the function, so we patch at the source
    monkeypatch.setattr("dailyriff_api.db.service_transaction", _fake)

    with pytest.raises(Exception) as exc_info:
        await get_current_user(creds, request=request)
    assert exc_info.value.status_code == 403
    assert "invalid" in exc_info.value.detail.lower() or "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_auth_returns_target_user_on_valid_impersonation(
    make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    from fastapi.security import HTTPAuthorizationCredentials
    from unittest.mock import MagicMock

    from dailyriff_api.auth import get_current_user
    import dailyriff_api.services.impersonation_service as svc

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    creds = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    request = MagicMock()
    request.headers = {"x-impersonation-session": str(SESSION_ID)}

    async def fake_validate(conn, *, session_id):
        return {
            "id": SESSION_ID,
            "impersonator_user_id": USER_A_ID,
            "target_user_id": USER_B_ID,
            "mode": "silent",
        }

    monkeypatch.setattr(svc, "validate_session", fake_validate)

    @asynccontextmanager
    async def _fake():
        yield AsyncMock()

    monkeypatch.setattr("dailyriff_api.db.service_transaction", _fake)

    user = await get_current_user(creds, request=request)
    assert user.id == USER_B_ID
    assert user.impersonation_session_id == SESSION_ID
    assert user.role is None  # impersonated sessions get role=None (not superadmin)


@pytest.mark.asyncio
async def test_auth_rejects_impersonation_by_wrong_impersonator(
    make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    """Session belongs to a different superadmin — reject."""
    from fastapi.security import HTTPAuthorizationCredentials
    from unittest.mock import MagicMock

    from dailyriff_api.auth import get_current_user
    import dailyriff_api.services.impersonation_service as svc

    other_admin = uuid.UUID("00000000-0000-0000-0000-000000000003")
    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    creds = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    request = MagicMock()
    request.headers = {"x-impersonation-session": str(SESSION_ID)}

    async def fake_validate(conn, *, session_id):
        return {
            "id": SESSION_ID,
            "impersonator_user_id": other_admin,  # different admin
            "target_user_id": USER_B_ID,
            "mode": "silent",
        }

    monkeypatch.setattr(svc, "validate_session", fake_validate)

    @asynccontextmanager
    async def _fake():
        yield AsyncMock()

    monkeypatch.setattr("dailyriff_api.db.service_transaction", _fake)

    with pytest.raises(Exception) as exc_info:
        await get_current_user(creds, request=request)
    assert exc_info.value.status_code == 403


# --- Live mode in start request ---


def test_start_impersonation_with_live_mode(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.impersonation as mod

    live_session = {**SESSION_ROW, "mode": "live"}

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": USER_B_ID},  # target exists
            None,  # no active session
            live_session,  # INSERT RETURNING
        ])
        conn.execute = AsyncMock()
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    resp = client.post(
        f"/admin/impersonation/{USER_B_ID}/start",
        json={"reason": "Live investigation", "mode": "live"},
        headers=_superadmin_headers(make_test_jwt),
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "live"
