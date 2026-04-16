"""Impersonation session schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ImpersonationMode = Literal["silent", "live"]


class ImpersonationStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=1, max_length=1000)
    mode: ImpersonationMode = "silent"


class ImpersonationSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    impersonator_user_id: UUID
    target_user_id: UUID
    studio_id: UUID | None = None
    reason: str
    mode: ImpersonationMode
    ip_address: str | None = None
    user_agent: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    notification_sent_at: datetime | None = None


class AccountAccessLogEntry(BaseModel):
    """Single entry in a user's Account Access Log (read-only)."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    impersonator_user_id: UUID
    reason: str
    mode: ImpersonationMode
    started_at: datetime
    ended_at: datetime | None = None
    playback_count: int = 0
