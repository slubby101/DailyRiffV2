"""Notification preferences endpoint stubs.

Slice c ships these as protected stubs; slice d wires them to the DB with
upsert semantics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from dailyriff_api.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/notification-preferences", tags=["preferences"])

_DEFAULTS = {
    "realtime_enabled": True,
    "expo_enabled": True,
    "webpush_enabled": True,
}


@router.get("")
def get_preferences(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"user_id": str(user.id), **_DEFAULTS}


@router.patch("")
def update_preferences(
    payload: dict, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return {"user_id": str(user.id), **_DEFAULTS, **payload}
