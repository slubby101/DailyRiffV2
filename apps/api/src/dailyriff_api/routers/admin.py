"""Admin endpoints — superadmin only.

Provides cross-tenant views for the superadmin operator surface:
all studios (bypassing RLS), platform users from auth.users, etc.
"""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    SUPERADMIN_RESPONSES,
    CurrentUser,
    require_superadmin,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.studio import StudioResponse

router = APIRouter(prefix="/admin", tags=["admin"])

STUDIO_COLUMNS = (
    "id, name, display_name, logo_url, primary_color, "
    "timezone, beta_cohort, state, created_at, updated_at"
)


@router.get(
    "/studios",
    response_model=list[StudioResponse],
    responses=SUPERADMIN_RESPONSES,
)
async def list_all_studios(
    user: CurrentUser = Depends(require_superadmin),
) -> list[StudioResponse]:
    """List all studios across the platform (bypasses RLS)."""
    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {STUDIO_COLUMNS} FROM studios ORDER BY created_at DESC",
        )
    return [StudioResponse(**dict(r)) for r in rows]


@router.get(
    "/verification-queue",
    response_model=list[StudioResponse],
    responses=SUPERADMIN_RESPONSES,
)
async def list_pending_studios(
    user: CurrentUser = Depends(require_superadmin),
) -> list[StudioResponse]:
    """List studios awaiting verification."""
    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {STUDIO_COLUMNS} FROM studios WHERE state = 'pending' ORDER BY created_at ASC",
        )
    return [StudioResponse(**dict(r)) for r in rows]


@router.get(
    "/studios/{studio_id}",
    response_model=StudioResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Studio not found"}},
)
async def get_studio(
    studio_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> StudioResponse:
    """Get a single studio by ID (bypasses RLS)."""
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"SELECT {STUDIO_COLUMNS} FROM studios WHERE id = $1",
            studio_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudioResponse(**dict(row))


@router.post(
    "/studios/{studio_id}/suspend",
    response_model=StudioResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Studio not found"}},
)
async def suspend_studio(
    studio_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> StudioResponse:
    """Suspend a studio (superadmin, bypasses RLS)."""
    now = datetime.now(tz.utc)
    async with service_transaction() as conn:
        prev = await conn.fetchval(
            "SELECT state FROM studios WHERE id = $1",
            studio_id,
        )
        row = await conn.fetchrow(
            f"UPDATE studios SET state = 'suspended', updated_at = $2 "
            f"WHERE id = $1 RETURNING {STUDIO_COLUMNS}",
            studio_id,
            now,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "suspend",
            "studio",
            str(studio_id),
            {"previous_state": prev},
        )
    return StudioResponse(**dict(row))


@router.post(
    "/studios/{studio_id}/verify",
    response_model=StudioResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Studio not found"}},
)
async def verify_studio(
    studio_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> StudioResponse:
    """Verify/activate a studio (superadmin, bypasses RLS)."""
    now = datetime.now(tz.utc)
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"UPDATE studios SET state = 'active', updated_at = $2 "
            f"WHERE id = $1 RETURNING {STUDIO_COLUMNS}",
            studio_id,
            now,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "verify",
            "studio",
            str(studio_id),
            {},
        )
    return StudioResponse(**dict(row))
