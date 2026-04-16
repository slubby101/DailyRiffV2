"""COPPA router unit tests — access control, consent lifecycle, webhook."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
PARENT_DB_ID = uuid.uuid4()
CHILD_ID = uuid.uuid4()
CONSENT_ID = uuid.uuid4()

PARENT_ROW = {"id": PARENT_DB_ID}
PARENT_CHILD_ROW = {"id": uuid.uuid4()}

CONSENT_ROW = {
    "id": CONSENT_ID,
    "parent_id": PARENT_DB_ID,
    "child_id": CHILD_ID,
    "studio_id": STUDIO_ID,
    "status": "pending",
    "stripe_setup_intent_id": "seti_test_123",
    "form_url": None,
    "verified_at": None,
    "revoked_at": None,
    "revocation_auto_delete_at": None,
    "created_at": NOW,
    "updated_at": NOW,
}

VERIFIED_CONSENT_ROW = {
    **CONSENT_ROW,
    "status": "verified",
    "verified_at": NOW,
}


def _make_svc_ctx(*, fetchrow_results=None, execute_result="INSERT 1"):
    """Mock service_transaction with sequential fetchrow returns."""
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

        conn.execute = AsyncMock(return_value=execute_result)
        conn.fetchval = AsyncMock(return_value=None)
        yield conn

    return _fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# --- Access control ---


class TestAccessControl:
    def test_unauthenticated_cannot_initiate(self, client: TestClient) -> None:
        resp = client.post(
            "/coppa/initiate",
            json={"child_id": str(CHILD_ID), "studio_id": str(STUDIO_ID)},
        )
        assert resp.status_code == 401

    def test_non_parent_cannot_initiate(
        self, client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        # parent lookup returns None
        monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(fetchrow_results=[None]))

        token = make_test_jwt(user_id=USER_A_ID)
        resp = client.post(
            "/coppa/initiate",
            json={"child_id": str(CHILD_ID), "studio_id": str(STUDIO_ID)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_parent_without_child_cannot_initiate(
        self, client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        # parent found, but parent_child lookup returns None
        monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(fetchrow_results=[PARENT_ROW, None]))

        token = make_test_jwt(user_id=USER_A_ID)
        resp = client.post(
            "/coppa/initiate",
            json={"child_id": str(CHILD_ID), "studio_id": str(STUDIO_ID)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# --- Confirm endpoint removed (security fix: only webhook can confirm) ---


class TestConfirmEndpointRemoved:
    def test_confirm_endpoint_no_longer_exists(self, client: TestClient, make_test_jwt: Callable[..., str]) -> None:
        """The /coppa/confirm endpoint was removed — confirmation must go through the
        Stripe webhook which verifies the signature server-side."""
        token = make_test_jwt(user_id=USER_A_ID)
        resp = client.post(
            "/coppa/confirm",
            json={"consent_id": str(CONSENT_ID), "setup_intent_id": "seti_test_123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # 404 or 405 — the route no longer exists
        assert resp.status_code in (404, 405)


# --- Signed form endpoint ---


class TestSignedFormEndpoint:
    def test_signed_form_rejects_non_https_url(
        self, client: TestClient, make_test_jwt, monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
            fetchrow_results=[PARENT_ROW]
        ))

        token = make_test_jwt(user_id=USER_A_ID)
        resp = client.post(
            "/coppa/signed-form",
            json={
                "consent_id": str(CONSENT_ID),
                "form_url": "http://example.com/form.pdf",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "HTTPS" in resp.json()["detail"]

    def test_signed_form_verifies_consent(
        self, client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
            fetchrow_results=[PARENT_ROW]
        ))

        mock_svc = MagicMock()
        mock_svc.submit_signed_form = AsyncMock(return_value={
            **VERIFIED_CONSENT_ROW,
            "form_url": "https://storage.example.com/forms/signed.pdf",
        })

        with patch.object(mod, "CoppaService", return_value=mock_svc):
            token = make_test_jwt(user_id=USER_A_ID)
            resp = client.post(
                "/coppa/signed-form",
                json={
                    "consent_id": str(CONSENT_ID),
                    "form_url": "https://storage.example.com/forms/signed.pdf",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "verified"


# --- Revoke endpoint ---


class TestRevokeEndpoint:
    def test_revoke_returns_revoked_consent(
        self, client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx(
            fetchrow_results=[PARENT_ROW]
        ))

        revoked_row = {
            **VERIFIED_CONSENT_ROW,
            "status": "revoked",
            "revoked_at": NOW,
            "revocation_auto_delete_at": NOW + timedelta(days=30),
        }
        mock_svc = MagicMock()
        mock_svc.revoke_consent = AsyncMock(return_value=revoked_row)

        with patch.object(mod, "CoppaService", return_value=mock_svc):
            token = make_test_jwt(user_id=USER_A_ID)
            resp = client.post(
                "/coppa/revoke",
                json={"consent_id": str(CONSENT_ID)},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"
        assert resp.json()["revocation_auto_delete_at"] is not None


# --- Webhook ---


class TestStripeWebhook:
    def _make_signed_payload(self, payload: bytes, secret: str) -> str:
        ts = str(int(time.time()))
        signed = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_webhook_rejects_missing_secret(
        self, client: TestClient, monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        monkeypatch.setattr(mod, "_get_stripe_webhook_secret", lambda: None)

        resp = client.post(
            "/coppa/webhook/stripe",
            content=b'{"id": "evt_1"}',
            headers={"stripe-signature": "t=1,v1=fake"},
        )
        assert resp.status_code == 400

    def test_webhook_rejects_invalid_signature(
        self, client: TestClient, monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        monkeypatch.setattr(mod, "_get_stripe_webhook_secret", lambda: "whsec_test")

        resp = client.post(
            "/coppa/webhook/stripe",
            content=b'{"id": "evt_1"}',
            headers={"stripe-signature": "t=1,v1=invalidsig"},
        )
        assert resp.status_code == 400

    def test_webhook_confirms_consent_on_setup_intent_succeeded(
        self, client: TestClient, monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        secret = "whsec_test_secret"
        monkeypatch.setattr(mod, "_get_stripe_webhook_secret", lambda: secret)

        # Mock coppa service
        mock_svc = MagicMock()
        mock_svc.confirm_via_webhook = AsyncMock(return_value=VERIFIED_CONSENT_ROW)
        monkeypatch.setattr(mod, "CoppaService", lambda: mock_svc)

        # Mock service_transaction: idempotency claim returns row (first claim), then activity log
        @asynccontextmanager
        async def _svc_ctx():
            conn = AsyncMock()
            conn.fetchrow = AsyncMock(return_value={"event_id": "evt_test_123"})
            conn.execute = AsyncMock(return_value="INSERT 1")
            yield conn

        monkeypatch.setattr(mod, "service_transaction", _svc_ctx)

        payload = json.dumps({
            "id": "evt_test_123",
            "type": "setup_intent.succeeded",
            "data": {
                "object": {
                    "id": "seti_test_123",
                    "metadata": {"purpose": "coppa_vpc"},
                }
            },
        }).encode()

        sig_header = self._make_signed_payload(payload, secret)

        resp = client.post(
            "/coppa/webhook/stripe",
            content=payload,
            headers={"stripe-signature": sig_header},
        )

        assert resp.status_code == 200
        assert resp.json()["received"] is True
        mock_svc.confirm_via_webhook.assert_awaited_once()

    def test_webhook_duplicate_event_is_idempotent(
        self, client: TestClient, monkeypatch
    ) -> None:
        import dailyriff_api.routers.coppa as mod
        secret = "whsec_test_secret"
        monkeypatch.setattr(mod, "_get_stripe_webhook_secret", lambda: secret)

        # Duplicate: fetchrow returns None (ON CONFLICT DO NOTHING → no RETURNING row)
        @asynccontextmanager
        async def _svc_ctx():
            conn = AsyncMock()
            conn.fetchrow = AsyncMock(return_value=None)
            yield conn

        monkeypatch.setattr(mod, "service_transaction", _svc_ctx)

        payload = json.dumps({"id": "evt_duplicate", "type": "setup_intent.succeeded"}).encode()
        sig_header = self._make_signed_payload(payload, secret)

        resp = client.post(
            "/coppa/webhook/stripe",
            content=payload,
            headers={"stripe-signature": sig_header},
        )

        assert resp.status_code == 200
        assert resp.json()["received"] is True
