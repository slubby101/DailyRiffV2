"""Notification preferences endpoints with upsert semantics.

GET on a user with no row returns defaults without writing.
PATCH upserts (INSERT ... ON CONFLICT UPDATE).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from dailyriff_api.auth import CurrentUser, get_current_user
from dailyriff_api.db import rls_transaction
from dailyriff_api.schemas.preferences import (
    PreferencesResponse,
    PreferencesUpdateRequest,
)

router = APIRouter(prefix="/notification-preferences", tags=["preferences"])


@router.get("", response_model=PreferencesResponse)
async def get_preferences(
    user: CurrentUser = Depends(get_current_user),
) -> PreferencesResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            "SELECT user_id, realtime_enabled, expo_push_enabled, "
            "web_push_enabled, quiet_hours_start, quiet_hours_end, updated_at "
            "FROM notification_preferences WHERE user_id = $1",
            user.id,
        )
    if row is None:
        return PreferencesResponse(user_id=user.id)
    return PreferencesResponse(**dict(row))


@router.patch("", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> PreferencesResponse:
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return await get_preferences(user=user)

    columns = list(updates.keys())
    values = list(updates.values())

    insert_cols = ", ".join(columns)
    insert_placeholders = ", ".join(f"${i + 2}" for i in range(len(columns)))
    on_conflict_set = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in columns
    )

    sql = (
        f"INSERT INTO notification_preferences (user_id, {insert_cols}, updated_at) "
        f"VALUES ($1, {insert_placeholders}, ${ len(columns) + 2 }) "
        f"ON CONFLICT (user_id) DO UPDATE SET {on_conflict_set}, "
        f"updated_at = EXCLUDED.updated_at "
        "RETURNING user_id, realtime_enabled, expo_push_enabled, "
        "web_push_enabled, quiet_hours_start, quiet_hours_end, updated_at"
    )

    now = datetime.now(timezone.utc)
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(sql, user.id, *values, now)
    assert row is not None
    return PreferencesResponse(**dict(row))
