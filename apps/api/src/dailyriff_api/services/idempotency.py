"""Webhook idempotency + signature verification for Stripe and Postmark."""

from __future__ import annotations

import hashlib
import hmac
import time

from dailyriff_api.db import service_transaction

STRIPE_TIMESTAMP_TOLERANCE = 300


class IdempotencyService:
    async def claim_event(self, provider: str, event_id: str) -> bool:
        """Atomically claim an event. Returns True if this is the first claim (not a duplicate)."""
        async with service_transaction() as conn:
            row = await conn.fetchrow(
                "INSERT INTO idempotency_log (provider, event_id) "
                "VALUES ($1, $2) ON CONFLICT DO NOTHING RETURNING event_id",
                provider,
                event_id,
            )
        return row is not None


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

    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False
    if abs(time.time() - ts) > STRIPE_TIMESTAMP_TOLERANCE:
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
