"""COPPA verifiable parental consent service.

Handles Stripe Setup Intent flow, signed-form escape hatch, confirmation,
and revocation with 30-day auto-delete scheduling.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz
from typing import Any, Protocol
from uuid import UUID

from dailyriff_api.db import service_transaction


class StripeClient(Protocol):
    """Protocol for Stripe API interactions — mocked at system boundary."""

    async def create_setup_intent(self, *, metadata: dict[str, str]) -> dict[str, str]: ...

    async def confirm_setup_intent(self, setup_intent_id: str) -> dict[str, Any]: ...


COPPA_CONSENT_COLUMNS = (
    "id, parent_id, child_id, studio_id, stripe_setup_intent_id, form_url, "
    "status, verified_at, revoked_at, revocation_auto_delete_at, "
    "created_at, updated_at"
)


class CoppaService:
    def __init__(self, *, stripe_client: StripeClient | None = None) -> None:
        self._stripe = stripe_client

    async def initiate_consent(
        self,
        *,
        parent_id: UUID,
        child_id: UUID,
        studio_id: UUID,
    ) -> dict[str, Any]:
        """Create a pending COPPA consent and a Stripe Setup Intent.

        Returns dict with consent_id, client_secret, and status.
        """
        if self._stripe is None:
            raise RuntimeError("Stripe client not configured")

        intent = await self._stripe.create_setup_intent(
            metadata={
                "parent_id": str(parent_id),
                "child_id": str(child_id),
                "studio_id": str(studio_id),
                "purpose": "coppa_vpc",
            }
        )

        setup_intent_id = intent["id"]
        client_secret = intent["client_secret"]

        async with service_transaction() as conn:
            row = await conn.fetchrow(
                f"INSERT INTO coppa_consents "
                f"(parent_id, child_id, studio_id, stripe_setup_intent_id) "
                f"VALUES ($1, $2, $3, $4) "
                f"RETURNING {COPPA_CONSENT_COLUMNS}",
                parent_id,
                child_id,
                studio_id,
                setup_intent_id,
            )

        return {
            "consent_id": row["id"],
            "client_secret": client_secret,
            "status": row["status"],
        }

    async def confirm_consent(
        self,
        *,
        consent_id: UUID,
        setup_intent_id: str,
        parent_id: UUID,
    ) -> dict[str, Any] | None:
        """Confirm a pending COPPA consent after Stripe Setup Intent succeeds.

        Returns updated consent dict or None if consent is not in pending state.
        """
        async with service_transaction() as conn:
            # Fetch the consent and verify ownership + status
            row = await conn.fetchrow(
                f"SELECT {COPPA_CONSENT_COLUMNS} FROM coppa_consents "
                f"WHERE id = $1 AND parent_id = $2",
                consent_id,
                parent_id,
            )
            if row is None:
                return None
            if row["status"] != "pending":
                return None

            now = datetime.now(tz.utc)
            updated = await conn.fetchrow(
                f"UPDATE coppa_consents "
                f"SET status = 'verified', verified_at = $2, "
                f"    stripe_setup_intent_id = $3, updated_at = $2 "
                f"WHERE id = $1 AND status = 'pending' "
                f"RETURNING {COPPA_CONSENT_COLUMNS}",
                consent_id,
                now,
                setup_intent_id,
            )

        if updated is None:
            return None
        return dict(updated)

    async def submit_signed_form(
        self,
        *,
        consent_id: UUID,
        form_url: str,
        parent_id: UUID,
    ) -> dict[str, Any] | None:
        """Verify consent via signed-form escape hatch (alternative to Stripe).

        Returns updated consent dict or None if not in pending state.
        """
        async with service_transaction() as conn:
            row = await conn.fetchrow(
                f"SELECT {COPPA_CONSENT_COLUMNS} FROM coppa_consents "
                f"WHERE id = $1 AND parent_id = $2",
                consent_id,
                parent_id,
            )
            if row is None or row["status"] != "pending":
                return None

            now = datetime.now(tz.utc)
            updated = await conn.fetchrow(
                f"UPDATE coppa_consents "
                f"SET status = 'verified', verified_at = $2, "
                f"    form_url = $3, updated_at = $2 "
                f"WHERE id = $1 AND status = 'pending' "
                f"RETURNING {COPPA_CONSENT_COLUMNS}",
                consent_id,
                now,
                form_url,
            )

        if updated is None:
            return None
        return dict(updated)

    async def revoke_consent(
        self,
        *,
        consent_id: UUID,
        parent_id: UUID,
    ) -> dict[str, Any] | None:
        """Revoke a verified COPPA consent. Schedules 30-day auto-delete.

        Returns updated consent dict or None if not in verified state.
        """
        async with service_transaction() as conn:
            row = await conn.fetchrow(
                f"SELECT {COPPA_CONSENT_COLUMNS} FROM coppa_consents "
                f"WHERE id = $1 AND parent_id = $2",
                consent_id,
                parent_id,
            )
            if row is None or row["status"] != "verified":
                return None

            now = datetime.now(tz.utc)
            auto_delete_at = now + timedelta(days=30)

            updated = await conn.fetchrow(
                f"UPDATE coppa_consents "
                f"SET status = 'revoked', revoked_at = $2, "
                f"    revocation_auto_delete_at = $3, updated_at = $2 "
                f"WHERE id = $1 AND status = 'verified' "
                f"RETURNING {COPPA_CONSENT_COLUMNS}",
                consent_id,
                now,
                auto_delete_at,
            )

        if updated is None:
            return None
        return dict(updated)

    async def get_consent(
        self,
        *,
        parent_id: UUID,
        child_id: UUID,
        studio_id: UUID,
    ) -> dict[str, Any] | None:
        """Get the most recent COPPA consent for a parent-child-studio triple."""
        async with service_transaction() as conn:
            row = await conn.fetchrow(
                f"SELECT {COPPA_CONSENT_COLUMNS} FROM coppa_consents "
                f"WHERE parent_id = $1 AND child_id = $2 AND studio_id = $3 "
                f"ORDER BY created_at DESC LIMIT 1",
                parent_id,
                child_id,
                studio_id,
            )
        if row is None:
            return None
        return dict(row)

    async def confirm_via_webhook(
        self,
        *,
        setup_intent_id: str,
    ) -> dict[str, Any] | None:
        """Confirm a consent via Stripe webhook (setup_intent.succeeded).

        Looks up consent by stripe_setup_intent_id, transitions pending→verified.
        Returns updated consent dict or None.
        """
        async with service_transaction() as conn:
            row = await conn.fetchrow(
                f"SELECT {COPPA_CONSENT_COLUMNS} FROM coppa_consents "
                f"WHERE stripe_setup_intent_id = $1",
                setup_intent_id,
            )
            if row is None or row["status"] != "pending":
                return None

            now = datetime.now(tz.utc)
            updated = await conn.fetchrow(
                f"UPDATE coppa_consents "
                f"SET status = 'verified', verified_at = $2, updated_at = $2 "
                f"WHERE id = $1 AND status = 'pending' "
                f"RETURNING {COPPA_CONSENT_COLUMNS}",
                row["id"],
                now,
            )

        if updated is None:
            return None
        return dict(updated)
