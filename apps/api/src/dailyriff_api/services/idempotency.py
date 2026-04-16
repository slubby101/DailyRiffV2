"""Webhook idempotency + signature verification for Stripe and Postmark."""

from __future__ import annotations

import hashlib
import hmac
import time

from dailyriff_api.db import service_transaction

STRIPE_TIMESTAMP_TOLERANCE = 300


class IdempotencyService:
    async def is_duplicate(self, provider: str, event_id: str) -> bool:
        async with service_transaction() as conn:
            existing = await conn.fetchval(
                "SELECT event_id FROM idempotency_log "
                "WHERE provider = $1 AND event_id = $2",
                provider,
                event_id,
            )
        return existing is not None

    async def record_event(self, provider: str, event_id: str) -> None:
        async with service_transaction() as conn:
            await conn.execute(
                "INSERT INTO idempotency_log (provider, event_id) "
                "VALUES ($1, $2) ON CONFLICT DO NOTHING",
                provider,
                event_id,
            )


def verify_stripe_signature(
    payload: bytes, header: str, secret: str
) -> bool:
    parts = dict(
        item.split("=", 1) for item in header.split(",") if "=" in item
    )
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False

    if abs(time.time() - int(timestamp)) > STRIPE_TIMESTAMP_TOLERANCE:
        return False

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_postmark_signature(
    payload: bytes, timestamp: str, signature: str, token: str
) -> bool:
    sig_input = f"{timestamp}{payload.decode()}".encode()
    expected = hmac.new(token.encode(), sig_input, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
