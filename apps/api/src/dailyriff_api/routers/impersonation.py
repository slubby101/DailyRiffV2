"""Impersonation endpoints — superadmin only.

Provides start/end impersonation session + Account Access Log for target users.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from dailyriff_api.auth import (
    SUPERADMIN_RESPONSES,
    CurrentUser,
    get_current_user,
    require_superadmin,
    PROTECTED_RESPONSES,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.impersonation import (
    AccountAccessLogEntry,
    ImpersonationSessionResponse,
    ImpersonationStartRequest,
)
from dailyriff_api.services import impersonation_service

router = APIRouter(prefix="/admin/impersonation", tags=["impersonation"])


@router.post(
    "/{target_user_id}/start",
    response_model=ImpersonationSessionResponse,
    responses={
        **SUPERADMIN_RESPONSES,
        404: {"description": "Target user not found"},
        409: {"description": "Active session already exists"},
    },
)
async def start_impersonation(
    target_user_id: UUID,
    body: ImpersonationStartRequest,
    request: Request,
    user: CurrentUser = Depends(require_superadmin),
) -> ImpersonationSessionResponse:
    """Start an impersonation session for a target user."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    async with service_transaction() as conn:
        try:
            session = await impersonation_service.start_session(
                conn,
                impersonator_id=user.id,
                target_user_id=target_user_id,
                reason=body.reason,
                mode=body.mode,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except ValueError as e:
            msg = str(e)
            if "not found" in msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=msg
                )
            if "already exists" in msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail=msg
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=msg
            )
    return ImpersonationSessionResponse(**session)


@router.post(
    "/{session_id}/end",
    response_model=ImpersonationSessionResponse,
    responses={
        **SUPERADMIN_RESPONSES,
        404: {"description": "No active session found"},
    },
)
async def end_impersonation(
    session_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> ImpersonationSessionResponse:
    """End an active impersonation session."""
    async with service_transaction() as conn:
        try:
            session = await impersonation_service.end_session(
                conn,
                session_id=session_id,
                impersonator_id=user.id,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
    return ImpersonationSessionResponse(**session)


@router.get(
    "/active",
    response_model=ImpersonationSessionResponse | None,
    responses=SUPERADMIN_RESPONSES,
)
async def get_active_session(
    user: CurrentUser = Depends(require_superadmin),
) -> ImpersonationSessionResponse | None:
    """Get the impersonator's currently active session, if any."""
    async with service_transaction() as conn:
        session = await impersonation_service.get_active_session(
            conn, impersonator_id=user.id
        )
    if session is None:
        return None
    return ImpersonationSessionResponse(**session)


# --- Account Access Log (available to the target user themselves) ---

access_log_router = APIRouter(tags=["account-access-log"])


@access_log_router.get(
    "/account-access-log",
    response_model=list[AccountAccessLogEntry],
    responses=PROTECTED_RESPONSES,
)
async def get_account_access_log(
    user: CurrentUser = Depends(get_current_user),
) -> list[AccountAccessLogEntry]:
    """Return the Account Access Log for the authenticated user.

    Shows every admin impersonation session that targeted this user,
    including playback counts from impersonation_playback_log.
    Read-only — available on the user's settings page.
    """
    async with service_transaction() as conn:
        rows = await impersonation_service.list_sessions_for_target(
            conn, target_user_id=user.id
        )
    return [AccountAccessLogEntry(**r) for r in rows]
