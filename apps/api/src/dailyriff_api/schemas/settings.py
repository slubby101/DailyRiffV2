"""Platform settings and activity log schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


Category = Literal[
    "rate_limits",
    "business_rule_caps",
    "notification_delays",
    "coppa_grace_windows",
]


class SettingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    key: str
    value_json: Any
    description: str | None = None
    category: Category
    updated_at: datetime
    updated_by: UUID | None = None


class SettingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value_json: Any
    description: str | None = None


class SettingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value_json: Any
    description: str | None = None
    category: Category


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    action: str
    entity_type: str
    entity_id: str | None = None
    details: Any | None = None
    created_at: datetime
