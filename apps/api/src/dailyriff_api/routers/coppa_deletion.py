"""COPPA 15-day grace deletion endpoints.

Parent-initiated child data deletion with email confirmation,
cancellation, and status tracking.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

router = APIRouter(prefix="/coppa/deletion", tags=["coppa-deletion"])


class DeletionInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    child_id: UUID
    studio_id: UUID


class DeletionConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    confirmation_token: str


class DeletionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    parent_id: UUID
    child_id: UUID
    studio_id: UUID
    status: str
    email_confirmed_at: datetime | None = None
    scheduled_delete_at: datetime | None = None
    t7_reminder_sent_at: datetime | None = None
    t1_reminder_sent_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


_INTERNAL_FIELDS = {"confirmation_token_hash", "confirmation_token"}


def _to_response(row: dict) -> DeletionResponse:
    """Strip internal fields before returning to client."""
    return DeletionResponse(**{k: v for k, v in row.items() if k not in _INTERNAL_FIELDS})


async def _require_parent(conn, user_id: UUID) -> dict:
    """Verify user is a parent. Returns parent row or raises 403."""
    parent = await conn.fetchrow(
        "SELECT id FROM parents WHERE user_id = $1", user_id
    )
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents can manage child data deletion",
        )
    return parent


async def _verify_parent_child(conn, parent_id: UUID, child_id: UUID) -> None:
    """Verify parent-child relationship exists."""
    link = await conn.fetchrow(
        "SELECT id FROM parent_children WHERE parent_id = $1 AND child_id = $2",
        parent_id,
        child_id,
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No parent-child relationship found",
        )


@router.post(
    "/initiate",
    response_model=DeletionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def initiate_deletion(
    body: DeletionInitiateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> DeletionResponse:
    """Parent initiates child data deletion. Returns pending request."""
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)
        await _verify_parent_child(conn, parent["id"], body.child_id)

        result = await CoppaDeletionService.initiate_deletion(
            conn=conn,
            parent_id=parent["id"],
            child_id=body.child_id,
            studio_id=body.studio_id,
        )

    return _to_response(result)


@router.post(
    "/confirm",
    response_model=DeletionResponse,
    responses={
        **PROTECTED_RESPONSES,
        404: {"description": "Request not found or invalid token"},
    },
)
async def confirm_deletion(
    body: DeletionConfirmRequest,
    user: CurrentUser = Depends(get_current_user),
) -> DeletionResponse:
    """Confirm deletion via email token. Schedules 15-day grace period."""
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)

        result = await CoppaDeletionService.confirm_deletion(
            conn=conn,
            request_id=body.request_id,
            confirmation_token=body.confirmation_token,
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deletion request not found or invalid token",
        )
    return _to_response(result)


@router.post(
    "/{request_id}/cancel",
    response_model=DeletionResponse,
    responses={
        **PROTECTED_RESPONSES,
        404: {"description": "Request not found or cannot be cancelled"},
    },
)
async def cancel_deletion(
    request_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> DeletionResponse:
    """Cancel a pending or scheduled deletion. Available any time before T-0."""
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)

        result = await CoppaDeletionService.cancel_deletion(
            conn=conn,
            request_id=request_id,
            parent_id=parent["id"],
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deletion request not found or cannot be cancelled",
        )
    return _to_response(result)


@router.get(
    "/status",
    response_model=DeletionResponse,
    responses={
        **PROTECTED_RESPONSES,
        404: {"description": "No active deletion request"},
    },
)
async def get_deletion_status(
    child_id: UUID = Query(...),
    studio_id: UUID = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> DeletionResponse:
    """Get the most recent active deletion request for a child."""
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)

        result = await CoppaDeletionService.get_deletion_status(
            conn=conn,
            parent_id=parent["id"],
            child_id=child_id,
            studio_id=studio_id,
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active deletion request found",
        )
    return _to_response(result)
