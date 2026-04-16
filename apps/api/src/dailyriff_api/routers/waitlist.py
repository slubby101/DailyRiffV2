"""Waitlist endpoints — public submission + superadmin management.

Public:
  POST /waitlist  — submit a waitlist entry (hCaptcha-protected)

Admin (superadmin only):
  GET    /admin/waitlist                           — list entries
  GET    /admin/waitlist/{entry_id}                — get single entry
  POST   /admin/waitlist/{entry_id}/approve        — approve entry
  POST   /admin/waitlist/{entry_id}/reject         — reject entry
  POST   /admin/waitlist/{entry_id}/messages       — send message to applicant
  GET    /admin/waitlist/{entry_id}/messages       — list messages for entry
  POST   /admin/waitlist/bypass                    — create bypass invite
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone as tz
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from dailyriff_api.auth import (
    SUPERADMIN_RESPONSES,
    CurrentUser,
    require_superadmin,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.waitlist import (
    WaitlistBypassCreateRequest,
    WaitlistEntryResponse,
    WaitlistMessageRequest,
    WaitlistMessageResponse,
    WaitlistRejectRequest,
    WaitlistStatus,
    WaitlistSubmitRequest,
    WaitlistSubmitResponse,
)
from dailyriff_api.services.captcha import verify_hcaptcha

# Two routers: one public (no auth), one admin (superadmin)
public_router = APIRouter(tags=["waitlist"])
admin_router = APIRouter(prefix="/admin/waitlist", tags=["admin-waitlist"])

ENTRY_COLUMNS = (
    "id, email, name, studio_name, status, ip_address, bypass_token, "
    "reviewed_by, reviewed_at, rejection_reason, studio_id, created_at, updated_at"
)

MESSAGE_COLUMNS = "id, waitlist_entry_id, sender_id, body, created_at"


# ---------------------------------------------------------------------------
# Public: submit waitlist entry
# ---------------------------------------------------------------------------


@public_router.post(
    "/waitlist",
    response_model=WaitlistSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_waitlist(
    body: WaitlistSubmitRequest,
    request: Request,
) -> WaitlistSubmitResponse:
    """Submit a new waitlist entry from the marketing homepage."""
    # Verify hCaptcha (no-op in dev/test)
    if body.captcha_token:
        valid = await verify_hcaptcha(body.captcha_token)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha verification failed",
            )

    ip_address = request.client.host if request.client else None

    async with service_transaction() as conn:
        # Check for duplicate email
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM waitlist_entries WHERE email = $1",
            body.email,
        )
        if existing and existing > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already on the waitlist",
            )

        row = await conn.fetchrow(
            f"INSERT INTO waitlist_entries (email, name, studio_name, ip_address, hcaptcha_token) "
            f"VALUES ($1, $2, $3, $4, $5) "
            f"RETURNING {ENTRY_COLUMNS}",
            body.email,
            body.name,
            body.studio_name,
            ip_address,
            body.captcha_token,
        )

    return WaitlistSubmitResponse(**{
        k: v for k, v in dict(row).items()
        if k in WaitlistSubmitResponse.model_fields
    })


# ---------------------------------------------------------------------------
# Admin: list + filter
# ---------------------------------------------------------------------------


@admin_router.get(
    "",
    response_model=list[WaitlistEntryResponse],
    responses=SUPERADMIN_RESPONSES,
)
async def list_waitlist(
    user: CurrentUser = Depends(require_superadmin),
    status_filter: Optional[WaitlistStatus] = Query(None, alias="status"),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[WaitlistEntryResponse]:
    """List all waitlist entries, optionally filtered by status."""
    limit, offset = pagination
    async with service_transaction() as conn:
        if status_filter:
            rows = await conn.fetch(
                f"SELECT {ENTRY_COLUMNS} FROM waitlist_entries "
                f"WHERE status = $1 ORDER BY created_at ASC LIMIT $2 OFFSET $3",
                status_filter,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                f"SELECT {ENTRY_COLUMNS} FROM waitlist_entries ORDER BY created_at ASC LIMIT $1 OFFSET $2",
                limit,
                offset,
            )
    return [WaitlistEntryResponse(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Admin: get single entry
# ---------------------------------------------------------------------------


@admin_router.get(
    "/{entry_id}",
    response_model=WaitlistEntryResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Entry not found"}},
)
async def get_waitlist_entry(
    entry_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> WaitlistEntryResponse:
    """Get a single waitlist entry."""
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"SELECT {ENTRY_COLUMNS} FROM waitlist_entries WHERE id = $1",
            entry_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return WaitlistEntryResponse(**dict(row))


# ---------------------------------------------------------------------------
# Admin: approve
# ---------------------------------------------------------------------------


@admin_router.post(
    "/{entry_id}/approve",
    response_model=WaitlistEntryResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Entry not found"}},
)
async def approve_waitlist_entry(
    entry_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> WaitlistEntryResponse:
    """Approve a waitlist entry. Transitions status to 'approved'."""
    now = datetime.now(tz.utc)
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"UPDATE waitlist_entries "
            f"SET status = 'approved', reviewed_by = $2, reviewed_at = $3, updated_at = $3 "
            f"WHERE id = $1 "
            f"RETURNING {ENTRY_COLUMNS}",
            entry_id,
            user.id,
            now,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "approve",
            "waitlist_entry",
            str(entry_id),
            {"email": row["email"]},
        )
    return WaitlistEntryResponse(**dict(row))


# ---------------------------------------------------------------------------
# Admin: reject
# ---------------------------------------------------------------------------


@admin_router.post(
    "/{entry_id}/reject",
    response_model=WaitlistEntryResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Entry not found"}},
)
async def reject_waitlist_entry(
    entry_id: UUID,
    body: WaitlistRejectRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> WaitlistEntryResponse:
    """Reject a waitlist entry with optional reason."""
    now = datetime.now(tz.utc)
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"UPDATE waitlist_entries "
            f"SET status = 'rejected', reviewed_by = $2, reviewed_at = $3, "
            f"    rejection_reason = $4, updated_at = $3 "
            f"WHERE id = $1 "
            f"RETURNING {ENTRY_COLUMNS}",
            entry_id,
            user.id,
            now,
            body.reason,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "reject",
            "waitlist_entry",
            str(entry_id),
            {"email": row["email"], "reason": body.reason},
        )
    return WaitlistEntryResponse(**dict(row))


# ---------------------------------------------------------------------------
# Admin: messages
# ---------------------------------------------------------------------------


@admin_router.post(
    "/{entry_id}/messages",
    response_model=WaitlistMessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Entry not found"}},
)
async def send_waitlist_message(
    entry_id: UUID,
    body: WaitlistMessageRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> WaitlistMessageResponse:
    """Send a message to a waitlist applicant."""
    async with service_transaction() as conn:
        exists = await conn.fetchval(
            "SELECT COUNT(*) FROM waitlist_entries WHERE id = $1",
            entry_id,
        )
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        row = await conn.fetchrow(
            f"INSERT INTO waitlist_messages (waitlist_entry_id, sender_id, body) "
            f"VALUES ($1, $2, $3) "
            f"RETURNING {MESSAGE_COLUMNS}",
            entry_id,
            user.id,
            body.body,
        )
    return WaitlistMessageResponse(**dict(row))


@admin_router.get(
    "/{entry_id}/messages",
    response_model=list[WaitlistMessageResponse],
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Entry not found"}},
)
async def list_waitlist_messages(
    entry_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> list[WaitlistMessageResponse]:
    """List messages for a waitlist entry."""
    async with service_transaction() as conn:
        exists = await conn.fetchval(
            "SELECT COUNT(*) FROM waitlist_entries WHERE id = $1",
            entry_id,
        )
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        rows = await conn.fetch(
            f"SELECT {MESSAGE_COLUMNS} FROM waitlist_messages "
            f"WHERE waitlist_entry_id = $1 ORDER BY created_at ASC",
            entry_id,
        )
    return [WaitlistMessageResponse(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Admin: bypass invite (personal-network direct invites)
# ---------------------------------------------------------------------------


@admin_router.post(
    "/bypass",
    response_model=WaitlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses=SUPERADMIN_RESPONSES,
)
async def create_bypass_invite(
    body: WaitlistBypassCreateRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> WaitlistEntryResponse:
    """Create a pre-approved waitlist entry with a bypass token for direct invites."""
    bypass_token = secrets.token_urlsafe(32)
    now = datetime.now(tz.utc)

    async with service_transaction() as conn:
        # Check for duplicate email
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM waitlist_entries WHERE email = $1",
            body.email,
        )
        if existing and existing > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already on the waitlist",
            )

        row = await conn.fetchrow(
            f"INSERT INTO waitlist_entries "
            f"(email, name, studio_name, status, bypass_token, reviewed_by, reviewed_at) "
            f"VALUES ($1, $2, $3, 'approved', $4, $5, $6) "
            f"RETURNING {ENTRY_COLUMNS}",
            body.email,
            body.name,
            body.studio_name,
            bypass_token,
            user.id,
            now,
        )
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "create_bypass",
            "waitlist_entry",
            str(row["id"]),
            {"email": body.email, "bypass": True},
        )
    return WaitlistEntryResponse(**dict(row))


# Combine into a single router attribute for main.py import
# We export both routers; main.py registers them both.
router = public_router
