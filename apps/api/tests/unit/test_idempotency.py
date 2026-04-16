"""Webhook idempotency + signature verification tests."""

from __future__ import annotations

import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from dailyriff_api.services.idempotency import (
    IdempotencyService,
    verify_stripe_signature,
    verify_postmark_signature,
)


def _mock_service_tx(*, fetchval_result=None, execute_result="INSERT 1"):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


class TestIdempotencyCheck:
    @pytest.mark.asyncio
    async def test_new_event_is_not_duplicate(self) -> None:
        svc = IdempotencyService()
        with patch(
            "dailyriff_api.services.idempotency.service_transaction",
            _mock_service_tx(fetchval_result=None),
        ):
            is_dup = await svc.is_duplicate("stripe", "evt_123")
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_existing_event_is_duplicate(self) -> None:
        svc = IdempotencyService()
        with patch(
            "dailyriff_api.services.idempotency.service_transaction",
            _mock_service_tx(fetchval_result="evt_123"),
        ):
            is_dup = await svc.is_duplicate("stripe", "evt_123")
        assert is_dup is True

    @pytest.mark.asyncio
    async def test_record_event_stores_to_db(self) -> None:
        svc = IdempotencyService()
        mock_tx = _mock_service_tx()
        with patch(
            "dailyriff_api.services.idempotency.service_transaction",
            mock_tx,
        ):
            await svc.record_event("stripe", "evt_456")


class TestStripeSignatureVerification:
    def test_valid_signature_passes(self) -> None:
        secret = "whsec_test_secret"
        payload = b'{"id": "evt_123"}'
        ts = str(int(time.time()))
        signed_payload = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        header = f"t={ts},v1={sig}"

        assert verify_stripe_signature(payload, header, secret) is True

    def test_invalid_signature_rejected(self) -> None:
        secret = "whsec_test_secret"
        payload = b'{"id": "evt_123"}'
        header = "t=12345,v1=invalidsig"

        assert verify_stripe_signature(payload, header, secret) is False

    def test_expired_timestamp_rejected(self) -> None:
        secret = "whsec_test_secret"
        payload = b'{"id": "evt_123"}'
        ts = str(int(time.time()) - 600)
        signed_payload = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        header = f"t={ts},v1={sig}"

        assert verify_stripe_signature(payload, header, secret) is False


class TestPostmarkSignatureVerification:
    def test_valid_signature_passes(self) -> None:
        token = "test-webhook-token"
        payload = b'{"RecordType": "Delivery"}'
        ts = str(int(time.time()))
        sig_input = f"{ts}{payload.decode()}".encode()
        sig = hmac.new(token.encode(), sig_input, hashlib.sha256).hexdigest()

        assert verify_postmark_signature(payload, ts, sig, token) is True

    def test_invalid_signature_rejected(self) -> None:
        assert verify_postmark_signature(b"body", "12345", "badsig", "token") is False
