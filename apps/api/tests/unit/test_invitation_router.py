"""Invitation router unit tests — access control, CRUD, redemption."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
INVITATION_ID = uuid.uuid4()

MEMBERSHIP_ROW_OWNER = {"role": "owner"}
MEMBERSHIP_ROW_TEACHER = {"role": "teacher"}
MEMBERSHIP_ROW_STUDENT = {"role": "student"}

INVITATION_ROW = {
    "id": INVITATION_ID,
    "studio_id": STUDIO_ID,
    "invited_by": USER_A_ID,
    "invited_email": "student@example.com",
    "invited_user_id": None,
    "persona": "student",
    "status": "pending",
    "token_hash": "fakehash",
    "age_class": "adult",
    "auto_approve": False,
    "expires_at": NOW + timedelta(days=14),
    "redeemed_at": None,
    "redeemed_by": None,
    "created_at": NOW,
    "updated_at": NOW,
}

REDEEMED_ROW = {
    **INVITATION_ROW,
    "status": "accepted",
    "redeemed_at": NOW,
    "redeemed_by": USER_B_ID,
    "invited_user_id": USER_B_ID,
}


def _make_svc_ctx(
    *,
    fetchrow_results=None,
    fetch_result=None,
    execute_result="UPDATE 1",
):
    """Create a mock service_transaction with sequential fetchrow returns."""
    call_idx = 0

    @asynccontextmanager
    async def _fake():
        nonlocal call_idx
        conn = AsyncMock()

        if fetchrow_results is not None:
            async def _fetchrow(*args, **kwargs):
                nonlocal call_idx
                if call_idx < len(fetchrow_results):
                    result = fetchrow_results[call_idx]
                    call_idx += 1
                    return result
                return None
            conn.fetchrow = AsyncMock(side_effect=_fetchrow)
        else:
            conn.fetchrow = AsyncMock(return_value=None)

        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.execute = AsyncMock(return_value=execute_result)
        conn.fetchval = AsyncMock(return_value=None)
        yield conn

    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.invitations as mod
    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# --- Access control ---


def test_unauthenticated_cannot_create_invitation(client: TestClient) -> None:
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations",
        json={"invited_email": "a@b.com", "persona": "student"},
    )
    assert resp.status_code == 401


def test_non_member_cannot_create_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    # fetchrow returns None for membership check
    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(fetchrow_results=[None]))

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations",
        json={"invited_email": "a@b.com", "persona": "student"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_student_cannot_create_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_STUDENT]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations",
        json={"invited_email": "a@b.com", "persona": "student"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# --- Create invitation ---


def test_teacher_can_create_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    # First fetchrow: membership check, second: INSERT RETURNING
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_TEACHER, INVITATION_ROW]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations",
        json={"invited_email": "student@example.com", "persona": "student", "age_class": "adult"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["invited_email"] == "student@example.com"
    assert data["persona"] == "student"
    assert data["status"] == "pending"
    # token_hash should NOT be in the response
    assert "token_hash" not in data


def test_owner_can_create_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_OWNER, INVITATION_ROW]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations",
        json={"invited_email": "teacher@example.com", "persona": "teacher"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


# --- List invitations ---


def test_teacher_can_list_invitations(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(
            fetchrow_results=[MEMBERSHIP_ROW_TEACHER],
            fetch_result=[INVITATION_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/invitations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["invited_email"] == "student@example.com"


def test_student_cannot_list_invitations(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_STUDENT]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/invitations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# --- Batch invite ---


def test_teacher_can_create_batch_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    parent_row = {**INVITATION_ROW, "persona": "parent", "age_class": "minor"}
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_TEACHER, parent_row]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations/batch",
        json={"invited_email": "parent@example.com", "child_names": ["Alice", "Bob"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["persona"] == "parent"


def test_batch_invite_rejects_empty_children(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_TEACHER]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations/batch",
        json={"invited_email": "parent@example.com", "child_names": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# --- Regenerate ---


def test_teacher_can_regenerate_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    regenerated_row = {**INVITATION_ROW, "token_hash": "newhash"}
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_TEACHER, regenerated_row]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations/{INVITATION_ID}/regenerate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_regenerate_returns_404_when_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    # membership found, but regenerate returns None
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[MEMBERSHIP_ROW_TEACHER, None]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/invitations/{uuid.uuid4()}/regenerate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Redeem ---


def test_user_can_redeem_valid_invitation(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    # redeem_invitation: atomic UPDATE returns the redeemed row directly
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[REDEEMED_ROW]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.post(
        "/invitations/redeem",
        json={"token": "some-valid-token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["studio_id"] == str(STUDIO_ID)


def test_redeem_invalid_token_returns_400(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.invitations as mod
    # redeem_invitation: fetchrow returns None (no matching hash)
    monkeypatch.setattr(
        mod, "service_transaction",
        _make_svc_ctx(fetchrow_results=[None]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.post(
        "/invitations/redeem",
        json={"token": "invalid-token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_unauthenticated_cannot_redeem(client: TestClient) -> None:
    resp = client.post(
        "/invitations/redeem",
        json={"token": "some-token"},
    )
    assert resp.status_code == 401
