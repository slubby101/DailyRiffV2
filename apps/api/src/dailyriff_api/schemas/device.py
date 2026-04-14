"""Device / push-subscription schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeviceRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["expo", "webpush"]
    token: str
    keys: dict[str, str] | None = None
    user_agent: str | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    channel: str
    token: str
    keys: dict[str, str] | None = None
    user_agent: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
