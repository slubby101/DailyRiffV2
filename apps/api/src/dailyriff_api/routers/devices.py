"""Device / push-subscription endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction
from dailyriff_api.schemas.device import DeviceRegisterRequest, DeviceResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse], responses=PROTECTED_RESPONSES)
async def list_devices(
    user: CurrentUser = Depends(get_current_user),
) -> list[DeviceResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            "SELECT id, user_id, channel, token, keys, user_agent, "
            "created_at, last_used_at "
            "FROM user_push_subscriptions "
            "WHERE user_id = $1 ORDER BY created_at DESC",
            user.id,
        )
    return [DeviceResponse(**dict(r)) for r in rows]


@router.post(
    "/register",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def register_device(
    body: DeviceRegisterRequest,
    user: CurrentUser = Depends(get_current_user),
) -> DeviceResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            "INSERT INTO user_push_subscriptions "
            "(user_id, channel, token, keys, user_agent) "
            "VALUES ($1, $2, $3, $4, $5) "
            "ON CONFLICT (user_id, channel, token) DO UPDATE "
            "SET keys = EXCLUDED.keys, user_agent = EXCLUDED.user_agent, "
            "last_used_at = now() "
            "RETURNING id, user_id, channel, token, keys, user_agent, "
            "created_at, last_used_at",
            user.id,
            body.channel,
            body.token,
            body.keys,
            body.user_agent,
        )
    assert row is not None
    return DeviceResponse(**dict(row))


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Device not found"}},
)
async def delete_device(
    device_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    async with rls_transaction(user.id) as conn:
        result = await conn.execute(
            "DELETE FROM user_push_subscriptions "
            "WHERE id = $1 AND user_id = $2",
            device_id,
            user.id,
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
