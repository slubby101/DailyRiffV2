"""Notification templates + per-category/channel preference endpoints.

GET /notification-templates — list all templates (any authenticated user)
GET /notification-category-preferences — list user's per-category/channel prefs
PUT /notification-category-preferences — upsert a single category/channel preference
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction, service_transaction
from dailyriff_api.schemas.notification_templates import (
    CategoryPreferenceResponse,
    CategoryPreferenceUpsertRequest,
    NotificationTemplateResponse,
)

router = APIRouter(tags=["notification-templates"])


@router.get(
    "/notification-templates",
    response_model=list[NotificationTemplateResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_templates(
    user: CurrentUser = Depends(get_current_user),
) -> list[NotificationTemplateResponse]:
    async with service_transaction() as conn:
        rows = await conn.fetch(
            "SELECT id, event_type, category, persona, title_template, "
            "body_template, channels, trigger_source, enabled, created_at, updated_at "
            "FROM notification_templates ORDER BY event_type"
        )
    return [NotificationTemplateResponse(**dict(r)) for r in rows]


@router.get(
    "/notification-category-preferences",
    response_model=list[CategoryPreferenceResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_category_preferences(
    user: CurrentUser = Depends(get_current_user),
) -> list[CategoryPreferenceResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            "SELECT id, user_id, category, channel, enabled, updated_at "
            "FROM notification_category_preferences "
            "WHERE user_id = $1 ORDER BY category, channel",
            user.id,
        )
    return [CategoryPreferenceResponse(**dict(r)) for r in rows]


@router.put(
    "/notification-category-preferences",
    response_model=CategoryPreferenceResponse,
    responses=PROTECTED_RESPONSES,
)
async def upsert_category_preference(
    body: CategoryPreferenceUpsertRequest,
    user: CurrentUser = Depends(get_current_user),
) -> CategoryPreferenceResponse:
    now = datetime.now(timezone.utc)
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            "INSERT INTO notification_category_preferences "
            "(user_id, category, channel, enabled, updated_at) "
            "VALUES ($1, $2, $3, $4, $5) "
            "ON CONFLICT (user_id, category, channel) DO UPDATE SET "
            "enabled = EXCLUDED.enabled, updated_at = EXCLUDED.updated_at "
            "RETURNING id, user_id, category, channel, enabled, updated_at",
            user.id,
            body.category,
            body.channel,
            body.enabled,
            now,
        )
    assert row is not None
    return CategoryPreferenceResponse(**dict(row))
