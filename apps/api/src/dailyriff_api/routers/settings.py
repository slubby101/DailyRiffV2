"""Platform settings endpoints — superadmin only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.settings import (
    ActivityLogResponse,
    SettingCreateRequest,
    SettingResponse,
    SettingUpdateRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])

SETTING_COLUMNS = "id, key, value_json, description, category, updated_at, updated_by"
LOG_COLUMNS = "id, user_id, action, entity_type, entity_id, details, created_at"

SUPERADMIN_RESPONSES: dict[int | str, dict] = {
    **PROTECTED_RESPONSES,
    403: {"description": "Superadmin role required"},
}


def _require_superadmin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin role required",
        )
    return user


@router.get("", response_model=list[SettingResponse], responses=SUPERADMIN_RESPONSES)
async def list_settings(
    user: CurrentUser = Depends(_require_superadmin),
) -> list[SettingResponse]:
    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {SETTING_COLUMNS} FROM platform_settings ORDER BY category, key",
        )
    return [SettingResponse(**dict(r)) for r in rows]


@router.get(
    "/activity-logs/",
    response_model=list[ActivityLogResponse],
    responses=SUPERADMIN_RESPONSES,
)
async def list_activity_logs(
    limit: int = 50,
    offset: int = 0,
    user: CurrentUser = Depends(_require_superadmin),
) -> list[ActivityLogResponse]:
    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {LOG_COLUMNS} FROM activity_logs "
            f"ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
    return [ActivityLogResponse(**dict(r)) for r in rows]


@router.get(
    "/{key}",
    response_model=SettingResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Setting not found"}},
)
async def get_setting(
    key: str,
    user: CurrentUser = Depends(_require_superadmin),
) -> SettingResponse:
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"SELECT {SETTING_COLUMNS} FROM platform_settings WHERE key = $1",
            key,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return SettingResponse(**dict(row))


@router.put(
    "/{key}",
    response_model=SettingResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Setting not found"}},
)
async def update_setting(
    key: str,
    body: SettingUpdateRequest,
    user: CurrentUser = Depends(_require_superadmin),
) -> SettingResponse:
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"UPDATE platform_settings "
            f"SET value_json = $1, description = COALESCE($2, description), "
            f"updated_at = now(), updated_by = $3 "
            f"WHERE key = $4 "
            f"RETURNING {SETTING_COLUMNS}",
            body.value_json,
            body.description,
            user.id,
            key,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "update",
            "platform_setting",
            key,
            {"new_value": body.value_json},
        )
    return SettingResponse(**dict(row))


@router.post(
    "",
    response_model=SettingResponse,
    status_code=status.HTTP_201_CREATED,
    responses=SUPERADMIN_RESPONSES,
)
async def create_setting(
    body: SettingCreateRequest,
    user: CurrentUser = Depends(_require_superadmin),
) -> SettingResponse:
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO platform_settings (key, value_json, description, category, updated_by) "
            f"VALUES ($1, $2, $3, $4, $5) "
            f"RETURNING {SETTING_COLUMNS}",
            body.key,
            body.value_json,
            body.description,
            body.category,
            user.id,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create platform setting",
            )
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "create",
            "platform_setting",
            body.key,
            {"value": body.value_json},
        )
    return SettingResponse(**dict(row))
