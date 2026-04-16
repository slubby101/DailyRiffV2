"""COPPA VPC service unit tests — TDD red-green per behavior."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone as tz
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from dailyriff_api.services.coppa_service import CoppaService


PARENT_ID = uuid4()
CHILD_ID = uuid4()
STUDIO_ID = uuid4()


def _mock_service_tx(*, fetchrow_result=None, fetchrow_side_effect=None, fetchval_result=None, execute_result="INSERT 1"):
    """Create a mock service_transaction context manager."""
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        if fetchrow_side_effect is not None:
            conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)
        else:
            conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


class TestInitiateConsent:
    @pytest.mark.asyncio
    async def test_initiate_creates_pending_consent_and_returns_client_secret(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        mock_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "pending",
            "stripe_setup_intent_id": "seti_test_123",
            "form_url": None,
            "verified_at": None,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }

        mock_stripe = MagicMock()
        mock_stripe.create_setup_intent = AsyncMock(return_value={
            "id": "seti_test_123",
            "client_secret": "seti_test_123_secret_abc",
        })

        svc = CoppaService(stripe_client=mock_stripe)

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_result=mock_row),
        ):
            result = await svc.initiate_consent(
                parent_id=PARENT_ID,
                child_id=CHILD_ID,
                studio_id=STUDIO_ID,
            )

        assert result["consent_id"] == consent_id
        assert result["client_secret"] == "seti_test_123_secret_abc"
        assert result["status"] == "pending"
        mock_stripe.create_setup_intent.assert_awaited_once()


class TestConfirmConsent:
    @pytest.mark.asyncio
    async def test_confirm_transitions_pending_to_verified(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        pending_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "pending",
            "stripe_setup_intent_id": "seti_test_123",
            "form_url": None,
            "verified_at": None,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }
        verified_row = {**pending_row, "status": "verified", "verified_at": now}

        svc = CoppaService(stripe_client=MagicMock())

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_side_effect=[pending_row, verified_row]),
        ):
            result = await svc.confirm_consent(
                consent_id=consent_id,
                setup_intent_id="seti_test_123",
                parent_id=PARENT_ID,
            )

        assert result is not None
        assert result["status"] == "verified"
        assert result["verified_at"] is not None

    @pytest.mark.asyncio
    async def test_confirm_rejects_non_pending_consent(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        already_verified_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "verified",
            "stripe_setup_intent_id": "seti_test_123",
            "form_url": None,
            "verified_at": now,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }

        svc = CoppaService(stripe_client=MagicMock())

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_result=already_verified_row),
        ):
            result = await svc.confirm_consent(
                consent_id=consent_id,
                setup_intent_id="seti_test_123",
                parent_id=PARENT_ID,
            )

        assert result is None


class TestSignedFormEscapeHatch:
    @pytest.mark.asyncio
    async def test_submit_signed_form_verifies_consent(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        pending_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "pending",
            "stripe_setup_intent_id": None,
            "form_url": None,
            "verified_at": None,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }
        verified_row = {
            **pending_row,
            "status": "verified",
            "verified_at": now,
            "form_url": "https://storage.example.com/forms/signed.pdf",
        }

        svc = CoppaService()

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_side_effect=[pending_row, verified_row]),
        ):
            result = await svc.submit_signed_form(
                consent_id=consent_id,
                form_url="https://storage.example.com/forms/signed.pdf",
                parent_id=PARENT_ID,
            )

        assert result is not None
        assert result["status"] == "verified"
        assert result["form_url"] == "https://storage.example.com/forms/signed.pdf"


class TestRevokeConsent:
    @pytest.mark.asyncio
    async def test_revoke_verified_consent_sets_revoked_status_and_auto_delete(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        auto_delete = now + timedelta(days=30)
        verified_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "verified",
            "stripe_setup_intent_id": "seti_test_123",
            "form_url": None,
            "verified_at": now,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }
        revoked_row = {
            **verified_row,
            "status": "revoked",
            "revoked_at": now,
            "revocation_auto_delete_at": auto_delete,
        }

        svc = CoppaService()

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_side_effect=[verified_row, revoked_row]),
        ):
            result = await svc.revoke_consent(
                consent_id=consent_id,
                parent_id=PARENT_ID,
            )

        assert result is not None
        assert result["status"] == "revoked"
        assert result["revoked_at"] is not None
        assert result["revocation_auto_delete_at"] is not None

    @pytest.mark.asyncio
    async def test_revoke_non_verified_consent_returns_none(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        pending_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "pending",
            "stripe_setup_intent_id": None,
            "form_url": None,
            "verified_at": None,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }

        svc = CoppaService()

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_result=pending_row),
        ):
            result = await svc.revoke_consent(
                consent_id=consent_id,
                parent_id=PARENT_ID,
            )

        assert result is None


class TestGetConsentStatus:
    @pytest.mark.asyncio
    async def test_get_consent_returns_consent_for_parent_child(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        mock_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "verified",
            "stripe_setup_intent_id": "seti_test_123",
            "form_url": None,
            "verified_at": now,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }

        svc = CoppaService()

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_result=mock_row),
        ):
            result = await svc.get_consent(
                parent_id=PARENT_ID,
                child_id=CHILD_ID,
                studio_id=STUDIO_ID,
            )

        assert result is not None
        assert result["status"] == "verified"

    @pytest.mark.asyncio
    async def test_get_consent_returns_none_when_not_found(self) -> None:
        svc = CoppaService()

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_result=None),
        ):
            result = await svc.get_consent(
                parent_id=PARENT_ID,
                child_id=CHILD_ID,
                studio_id=STUDIO_ID,
            )

        assert result is None


class TestWebhookConfirm:
    @pytest.mark.asyncio
    async def test_webhook_confirm_verifies_consent_by_setup_intent_id(self) -> None:
        consent_id = uuid4()
        now = datetime.now(tz.utc)
        pending_row = {
            "id": consent_id,
            "parent_id": PARENT_ID,
            "child_id": CHILD_ID,
            "studio_id": STUDIO_ID,
            "status": "pending",
            "stripe_setup_intent_id": "seti_test_123",
            "form_url": None,
            "verified_at": None,
            "revoked_at": None,
            "revocation_auto_delete_at": None,
            "created_at": now,
            "updated_at": now,
        }
        verified_row = {**pending_row, "status": "verified", "verified_at": now}

        svc = CoppaService()

        with patch(
            "dailyriff_api.services.coppa_service.service_transaction",
            _mock_service_tx(fetchrow_side_effect=[pending_row, verified_row]),
        ):
            result = await svc.confirm_via_webhook(
                setup_intent_id="seti_test_123",
            )

        assert result is not None
        assert result["status"] == "verified"
