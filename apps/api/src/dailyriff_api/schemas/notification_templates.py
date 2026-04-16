"""Notification template and category preference schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_type: str
    category: str
    persona: str
    title_template: str
    body_template: str
    channels: list[str]
    trigger_source: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CategoryPreferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    category: str
    channel: str
    enabled: bool
    updated_at: datetime


class CategoryPreferenceUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    channel: str
    enabled: bool
