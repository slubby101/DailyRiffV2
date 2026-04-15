"""Studio endpoints."""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction
from dailyriff_api.schemas.studio import (
    StudioCreateRequest,
    StudioResponse,
    StudioUpdateRequest,
)

router = APIRouter(prefix="/studios", tags=["studios"])

STUDIO_COLUMNS = (
    "id, name, display_name, logo_url, primary_color, "
    "timezone, beta_cohort, state, created_at, updated_at"
)

_UPDATABLE_COLUMNS = {"display_name", "logo_url", "primary_color", "timezone"}


@router.get("", response_model=list[StudioResponse], responses=PROTECTED_RESPONSES)
async def list_studios(
    user: CurrentUser = Depends(get_current_user),
) -> list[StudioResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {STUDIO_COLUMNS} FROM studios ORDER BY created_at DESC",
        )
    return [StudioResponse(**dict(r)) for r in rows]


@router.post(
    "",
    response_model=StudioResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_studio(
    body: StudioCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StudioResponse:
    # Generate the studio id client-side so we can INSERT studios and
    # studio_members in the right order without hitting the RLS + RETURNING
    # chicken-and-egg problem: the SELECT policy on studios requires the user
    # to be a member (via studio_members), but the member row only exists
    # after the studios row is created. INSERT ... RETURNING would trigger
    # the SELECT policy check on the new row and fail because the member row
    # isn't there yet. Splitting into (INSERT studios) -> (INSERT member) ->
    # (SELECT studio) lets the final SELECT succeed via select_member.
    studio_id = uuid4()
    async with rls_transaction(user.id) as conn:
        await conn.execute(
            "INSERT INTO studios (id, name, display_name, timezone) "
            "VALUES ($1, $2, $3, $4)",
            studio_id,
            body.name,
            body.display_name,
            body.timezone,
        )
        await conn.execute(
            "INSERT INTO studio_members (studio_id, user_id, role) "
            "VALUES ($1, $2, 'owner')",
            studio_id,
            user.id,
        )
        row = await conn.fetchrow(
            f"SELECT {STUDIO_COLUMNS} FROM studios WHERE id = $1",
            studio_id,
        )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create studio",
        )
    return StudioResponse(**dict(row))


@router.get(
    "/{studio_id}",
    response_model=StudioResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Studio not found"}},
)
async def get_studio(
    studio_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> StudioResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"SELECT {STUDIO_COLUMNS} FROM studios WHERE id = $1",
            studio_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudioResponse(**dict(row))


@router.patch(
    "/{studio_id}",
    response_model=StudioResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Studio not found"}},
)
async def update_studio(
    studio_id: UUID,
    body: StudioUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StudioResponse:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return await get_studio(studio_id, user)

    columns = [c for c in updates if c in _UPDATABLE_COLUMNS]
    values = [updates[c] for c in columns]

    set_clause = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(columns))
    now = datetime.now(tz.utc)
    set_clause += f", updated_at = ${len(columns) + 2}"

    sql = (
        f"UPDATE studios SET {set_clause} "
        f"WHERE id = $1 "
        f"RETURNING {STUDIO_COLUMNS}"
    )

    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(sql, studio_id, *values, now)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudioResponse(**dict(row))


@router.post(
    "/{studio_id}/suspend",
    response_model=StudioResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Studio not found"}},
)
async def suspend_studio(
    studio_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> StudioResponse:
    now = datetime.now(tz.utc)
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"UPDATE studios SET state = 'suspended', updated_at = $2 "
            f"WHERE id = $1 RETURNING {STUDIO_COLUMNS}",
            studio_id,
            now,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudioResponse(**dict(row))


@router.post(
    "/{studio_id}/verify",
    response_model=StudioResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Studio not found"}},
)
async def verify_studio(
    studio_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> StudioResponse:
    now = datetime.now(tz.utc)
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"UPDATE studios SET state = 'active', updated_at = $2 "
            f"WHERE id = $1 RETURNING {STUDIO_COLUMNS}",
            studio_id,
            now,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudioResponse(**dict(row))
