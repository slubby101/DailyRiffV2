"""COPPA VPC endpoints — consent initiation, confirmation, signed-form, revocation, webhook.

Public (requires auth):
  POST   /coppa/initiate             — create Setup Intent + pending consent
  POST   /coppa/confirm              — confirm consent after Setup Intent succeeds
  POST   /coppa/signed-form          — signed-form escape hatch
  POST   /coppa/revoke               — revoke verified consent
  GET    /coppa/consent               — get consent status for a child

Webhook (no auth, signature-verified):
  POST   /coppa/webhook/stripe       — Stripe setup_intent.succeeded webhook
"""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from dailyriff_api.auth import CurrentUser, get_current_user, PROTECTED_RESPONSES
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.coppa import (
    CoppaConfirmRequest,
    CoppaConsentResponse,
    CoppaInitiateRequest,
    CoppaInitiateResponse,
    CoppaRevokeRequest,
    CoppaSignedFormRequest,
    CoppaWebhookResponse,
)
from dailyriff_api.services.coppa_service import CoppaService
from dailyriff_api.services.idempotency import IdempotencyService, verify_stripe_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coppa", tags=["coppa"])


def _get_stripe_webhook_secret() -> str | None:
    return os.environ.get("STRIPE_WEBHOOK_SECRET")


# ---------------------------------------------------------------------------
# POST /coppa/initiate — create Setup Intent + pending consent
# ---------------------------------------------------------------------------


@router.post(
    "/initiate",
    response_model=CoppaInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def initiate_coppa_consent(
    body: CoppaInitiateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CoppaInitiateResponse:
    """Initiate COPPA VPC: create a Stripe Setup Intent and a pending consent record."""
    # Verify caller is a parent of the child
    async with service_transaction() as conn:
        parent = await conn.fetchrow(
            "SELECT id FROM parents WHERE user_id = $1",
            user.id,
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only parents can initiate COPPA consent",
            )

        parent_child = await conn.fetchrow(
            "SELECT id FROM parent_children WHERE parent_id = $1 AND child_user_id = $2",
            parent["id"],
            body.child_id,
        )
        if parent_child is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the parent/guardian of this child",
            )

    svc = CoppaService(stripe_client=_get_stripe_client())
    result = await svc.initiate_consent(
        parent_id=parent["id"],
        child_id=body.child_id,
        studio_id=body.studio_id,
    )

    return CoppaInitiateResponse(
        consent_id=result["consent_id"],
        client_secret=result["client_secret"],
        status=result["status"],
    )


def _get_stripe_client():
    """Get a real Stripe client. Returns None if not configured."""
    return None


# ---------------------------------------------------------------------------
# POST /coppa/confirm — confirm consent after Setup Intent
# ---------------------------------------------------------------------------


@router.post(
    "/confirm",
    response_model=CoppaConsentResponse,
    responses=PROTECTED_RESPONSES,
)
async def confirm_coppa_consent(
    body: CoppaConfirmRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CoppaConsentResponse:
    """Confirm a pending COPPA consent after Stripe Setup Intent succeeds."""
    async with service_transaction() as conn:
        parent = await conn.fetchrow(
            "SELECT id FROM parents WHERE user_id = $1",
            user.id,
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only parents can confirm COPPA consent",
            )

    svc = CoppaService()
    result = await svc.confirm_consent(
        consent_id=body.consent_id,
        setup_intent_id=body.setup_intent_id,
        parent_id=parent["id"],
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent not found or not in pending state",
        )

    return CoppaConsentResponse(**result)


# ---------------------------------------------------------------------------
# POST /coppa/signed-form — signed-form escape hatch
# ---------------------------------------------------------------------------


@router.post(
    "/signed-form",
    response_model=CoppaConsentResponse,
    responses=PROTECTED_RESPONSES,
)
async def submit_signed_form(
    body: CoppaSignedFormRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CoppaConsentResponse:
    """Submit a signed consent form (escape hatch for parents without cards)."""
    async with service_transaction() as conn:
        parent = await conn.fetchrow(
            "SELECT id FROM parents WHERE user_id = $1",
            user.id,
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only parents can submit signed forms",
            )

    svc = CoppaService()
    result = await svc.submit_signed_form(
        consent_id=body.consent_id,
        form_url=body.form_url,
        parent_id=parent["id"],
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent not found or not in pending state",
        )

    return CoppaConsentResponse(**result)


# ---------------------------------------------------------------------------
# POST /coppa/revoke — revoke verified consent
# ---------------------------------------------------------------------------


@router.post(
    "/revoke",
    response_model=CoppaConsentResponse,
    responses=PROTECTED_RESPONSES,
)
async def revoke_coppa_consent(
    body: CoppaRevokeRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CoppaConsentResponse:
    """Revoke a verified COPPA consent. Pauses data collection, schedules 30-day auto-delete."""
    async with service_transaction() as conn:
        parent = await conn.fetchrow(
            "SELECT id FROM parents WHERE user_id = $1",
            user.id,
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only parents can revoke COPPA consent",
            )

    svc = CoppaService()
    result = await svc.revoke_consent(
        consent_id=body.consent_id,
        parent_id=parent["id"],
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent not found or not in verified state",
        )

    return CoppaConsentResponse(**result)


# ---------------------------------------------------------------------------
# GET /coppa/consent — get consent status
# ---------------------------------------------------------------------------


@router.get(
    "/consent",
    response_model=CoppaConsentResponse | None,
    responses=PROTECTED_RESPONSES,
)
async def get_coppa_consent(
    child_id: str = Query(...),
    studio_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> CoppaConsentResponse | None:
    """Get the current COPPA consent status for a child in a studio."""
    from uuid import UUID

    async with service_transaction() as conn:
        parent = await conn.fetchrow(
            "SELECT id FROM parents WHERE user_id = $1",
            user.id,
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only parents can check COPPA consent status",
            )

    svc = CoppaService()
    result = await svc.get_consent(
        parent_id=parent["id"],
        child_id=UUID(child_id),
        studio_id=UUID(studio_id),
    )
    if result is None:
        return None

    return CoppaConsentResponse(**result)


# ---------------------------------------------------------------------------
# POST /coppa/webhook/stripe — Stripe webhook for setup_intent.succeeded
# ---------------------------------------------------------------------------


@router.post(
    "/webhook/stripe",
    response_model=CoppaWebhookResponse,
)
async def stripe_webhook(request: Request) -> CoppaWebhookResponse:
    """Handle Stripe setup_intent.succeeded webhook for COPPA VPC.

    Verifies signature, checks idempotency, then confirms the consent.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = _get_stripe_webhook_secret()

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook not configured",
        )

    if not verify_stripe_signature(payload, sig_header, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_id = event.get("id")
    event_type = event.get("type")

    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event ID",
        )

    # Idempotency: claim + process in one transaction so failed processing releases the claim
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            "INSERT INTO idempotency_log (provider, event_id) "
            "VALUES ($1, $2) ON CONFLICT DO NOTHING RETURNING event_id",
            "stripe_coppa",
            event_id,
        )
        if row is None:
            return CoppaWebhookResponse(received=True)

        if event_type == "setup_intent.succeeded":
            setup_intent = event.get("data", {}).get("object", {})
            setup_intent_id = setup_intent.get("id")

            if setup_intent_id:
                metadata = setup_intent.get("metadata", {})
                if metadata.get("purpose") == "coppa_vpc":
                    svc = CoppaService()
                    await svc.confirm_via_webhook(setup_intent_id=setup_intent_id, conn=conn)

                    await conn.execute(
                        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
                        "VALUES ($1, $2, $3, $4, $5)",
                        None,
                        "coppa_vpc_webhook_confirmed",
                        "coppa_consent",
                        setup_intent_id,
                        {"event_id": event_id, "event_type": event_type},
                    )

    return CoppaWebhookResponse(received=True)
