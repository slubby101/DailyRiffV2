"""Notification preferences schemas."""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    realtime_enabled: bool = True
    expo_push_enabled: bool = True
    web_push_enabled: bool = True
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    updated_at: datetime | None = None


class PreferencesUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    realtime_enabled: bool | None = None
    expo_push_enabled: bool | None = None
    web_push_enabled: bool | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
