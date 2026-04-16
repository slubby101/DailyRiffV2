"""Beta router unit tests — feedback submission, admin views, landing tokens."""

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

STUDIO_ID = uuid.uuid4()

FEEDBACK_ROW = {
    "id": uuid.uuid4(),
    "studio_id": STUDIO_ID,
    "submitted_by": USER_A_ID,
    "category": "bug",
    "severity": "high",
    "body": "Button doesn't work",
    "submitted_at": NOW,
    "resolved_at": None,
    "created_at": NOW,
    "updated_at": NOW,
}

TOKEN_ROW = {
    "id": uuid.uuid4(),
    "token": "test-token-abc123",
    "description": "For beta studio #1",
    "is_active": True,
    "created_by": USER_A_ID,
    "created_at": NOW,
}

# Membership row indicating user is in a beta studio
BETA_MEMBERSHIP_ROW = {"beta_cohort": True}
NON_BETA_MEMBERSHIP_ROW = {"beta_cohort": False}


def _make_svc_ctx(
    *,
    fetch_result=None,
    fetchrow_result=None,
    fetchrow_side_effect=None,
    fetchval_result=None,
    execute_result="INSERT 1",
):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        if fetchrow_side_effect is not None:
            conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
        else:
            conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn

    return _fake


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Studio-scoped: submit feedback
# ---------------------------------------------------------------------------


def test_unauthenticated_cannot_submit_feedback(client: TestClient) -> None:
    resp = client.post(
        f"/studios/{STUDIO_ID}/beta/feedback",
        json={"body": "test", "category": "bug", "severity": "high"},
    )
    assert resp.status_code == 401


def test_non_member_cannot_submit_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    # fetchrow returns None → not a member
    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(fetchrow_result=None))

    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        f"/studios/{STUDIO_ID}/beta/feedback",
        json={"body": "test", "category": "bug", "severity": "high"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_non_beta_studio_member_cannot_submit_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=NON_BETA_MEMBERSHIP_ROW),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        f"/studios/{STUDIO_ID}/beta/feedback",
        json={"body": "test", "category": "bug", "severity": "high"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "beta" in resp.json()["detail"].lower()


def test_beta_studio_member_can_submit_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    # First fetchrow call: membership check → beta member
    # Second fetchrow call: INSERT RETURNING → feedback row
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(
            fetchrow_side_effect=[BETA_MEMBERSHIP_ROW, FEEDBACK_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        f"/studios/{STUDIO_ID}/beta/feedback",
        json={"body": "Button doesn't work", "category": "bug", "severity": "high"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "Button doesn't work"
    assert data["category"] == "bug"
    assert data["severity"] == "high"


# ---------------------------------------------------------------------------
# Studio-scoped: list feedback
# ---------------------------------------------------------------------------


def test_beta_studio_member_can_list_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(
            fetchrow_result=BETA_MEMBERSHIP_ROW,
            fetch_result=[FEEDBACK_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get(
        f"/studios/{STUDIO_ID}/beta/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["body"] == "Button doesn't work"


def test_non_member_cannot_list_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(fetchrow_result=None))

    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get(
        f"/studios/{STUDIO_ID}/beta/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Public: validate beta landing token
# ---------------------------------------------------------------------------


def test_valid_beta_token_returns_true(
    client: TestClient, monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result={"id": uuid.uuid4()}),
    )

    resp = client.post("/beta/validate-token", json={"token": "valid-token"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_invalid_beta_token_returns_false(
    client: TestClient, monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=None),
    )

    resp = client.post("/beta/validate-token", json={"token": "bad-token"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


# ---------------------------------------------------------------------------
# Admin: list all beta feedback
# ---------------------------------------------------------------------------


def test_non_superadmin_cannot_list_all_feedback(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.get(
        "/admin/beta/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_superadmin_can_list_all_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetch_result=[FEEDBACK_ROW]),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/admin/beta/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


def test_superadmin_can_filter_feedback_by_category(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetch_result=[FEEDBACK_ROW]),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/admin/beta/feedback?category=bug",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_superadmin_can_filter_feedback_by_severity(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetch_result=[FEEDBACK_ROW]),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/admin/beta/feedback?severity=high",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin: resolve feedback
# ---------------------------------------------------------------------------


def test_superadmin_can_resolve_feedback(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    resolved_row = {**FEEDBACK_ROW, "resolved_at": NOW}
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=resolved_row),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/beta/feedback/{FEEDBACK_ROW['id']}/resolve",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is not None


def test_resolve_nonexistent_feedback_returns_404(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=None),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/beta/feedback/{uuid.uuid4()}/resolve",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_non_superadmin_cannot_resolve_feedback(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        f"/admin/beta/feedback/{FEEDBACK_ROW['id']}/resolve",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin: create + list landing tokens
# ---------------------------------------------------------------------------


def test_superadmin_can_create_landing_token(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=TOKEN_ROW),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        "/admin/beta/landing-tokens",
        json={"description": "For beta studio #1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"] == "test-token-abc123"
    assert data["description"] == "For beta studio #1"
    assert data["is_active"] is True


def test_non_superadmin_cannot_create_landing_token(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        "/admin/beta/landing-tokens",
        json={"description": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_superadmin_can_list_landing_tokens(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetch_result=[TOKEN_ROW]),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.get(
        "/admin/beta/landing-tokens",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["token"] == "test-token-abc123"


# ---------------------------------------------------------------------------
# Admin: send beta onboarding
# ---------------------------------------------------------------------------


ONBOARDING_STUDIO_ROW = {
    "id": STUDIO_ID,
    "name": "beta-studio",
    "display_name": "Beta Studio",
    "beta_cohort": True,
    "owner_id": USER_A_ID,
}

NON_BETA_ONBOARDING_ROW = {
    **ONBOARDING_STUDIO_ROW,
    "beta_cohort": False,
}


def test_superadmin_can_send_beta_onboarding(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=ONBOARDING_STUDIO_ROW),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/beta/studios/{STUDIO_ID}/send-onboarding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


def test_onboarding_fails_for_non_beta_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=NON_BETA_ONBOARDING_ROW),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/beta/studios/{STUDIO_ID}/send-onboarding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "beta" in resp.json()["detail"].lower()


def test_onboarding_returns_404_for_missing_studio(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.beta as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_svc_ctx(fetchrow_result=None),
    )

    token = make_test_jwt(user_id=USER_A_ID, role="superadmin")
    resp = client.post(
        f"/admin/beta/studios/{uuid.uuid4()}/send-onboarding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_non_superadmin_cannot_send_onboarding(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.post(
        f"/admin/beta/studios/{STUDIO_ID}/send-onboarding",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Beta cohort immutability: normal APIs cannot set beta_cohort
# ---------------------------------------------------------------------------


def test_studios_update_does_not_accept_beta_cohort(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    """Verify that studio update endpoints don't allow beta_cohort mutation.

    beta_cohort can only be set via direct DB/admin action, not normal APIs.
    The studios router uses StudioUpdateRequest which doesn't include beta_cohort.
    """
    token = make_test_jwt(user_id=USER_A_ID, role="user")
    resp = client.put(
        f"/studios/{STUDIO_ID}",
        json={"beta_cohort": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 405 (no PUT), 422 (validation error), or 403 (access denied)
    # All are acceptable — the point is it's not 200
    assert resp.status_code != 200
