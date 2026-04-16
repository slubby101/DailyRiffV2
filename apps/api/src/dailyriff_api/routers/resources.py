"""Resource endpoints."""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction
from dailyriff_api.schemas.resource import (
    ResourceCreateRequest,
    ResourceResponse,
    ResourceUpdateRequest,
)

router = APIRouter(prefix="/resources", tags=["resources"])

RESOURCE_COLUMNS = (
    "id, studio_id, title, url, description, category, "
    "created_by, created_at, updated_at"
)


@router.get("", response_model=list[ResourceResponse], responses=PROTECTED_RESPONSES)
async def list_resources(
    user: CurrentUser = Depends(get_current_user),
) -> list[ResourceResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {RESOURCE_COLUMNS} FROM resources ORDER BY created_at DESC",
        )
    return [ResourceResponse(**dict(r)) for r in rows]


@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_resource(
    body: ResourceCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ResourceResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"INSERT INTO resources (studio_id, title, url, description, category, created_by) "
            f"VALUES ($1, $2, $3, $4, $5, $6) "
            f"RETURNING {RESOURCE_COLUMNS}",
            body.studio_id,
            body.title,
            body.url,
            body.description,
            body.category,
            user.id,
        )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create resource",
        )
    return ResourceResponse(**dict(row))


_UPDATABLE_COLUMNS = {"title", "url", "description", "category"}


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Resource not found"}},
)
async def get_resource(
    resource_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ResourceResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"SELECT {RESOURCE_COLUMNS} FROM resources WHERE id = $1",
            resource_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ResourceResponse(**dict(row))


@router.patch(
    "/{resource_id}",
    response_model=ResourceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Resource not found"}},
)
async def update_resource(
    resource_id: UUID,
    body: ResourceUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ResourceResponse:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return await get_resource(resource_id, user)

    columns = [c for c in updates if c in _UPDATABLE_COLUMNS]
    values = [updates[c] for c in columns]

    set_clause = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(columns))
    now = datetime.now(tz.utc)
    set_clause += f", updated_at = ${len(columns) + 2}"

    sql = (
        f"UPDATE resources SET {set_clause} "
        f"WHERE id = $1 "
        f"RETURNING {RESOURCE_COLUMNS}"
    )

    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(sql, resource_id, *values, now)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ResourceResponse(**dict(row))


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Resource not found"}},
)
async def delete_resource(
    resource_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    async with rls_transaction(user.id) as conn:
        result = await conn.execute(
            "DELETE FROM resources WHERE id = $1",
            resource_id,
        )
