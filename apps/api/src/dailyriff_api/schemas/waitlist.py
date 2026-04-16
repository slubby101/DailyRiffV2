"""Waitlist request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


WaitlistStatus = Literal["pending", "approved", "rejected", "invited"]


class WaitlistSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    name: str
    studio_name: str | None = None
    captcha_token: str | None = None


class WaitlistEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    name: str
    studio_name: str | None
    status: WaitlistStatus
    ip_address: str | None
    bypass_token: str | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    studio_id: UUID | None
    created_at: datetime
    updated_at: datetime


class WaitlistSubmitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    name: str
    studio_name: str | None
    status: WaitlistStatus
    created_at: datetime
    updated_at: datetime


class WaitlistApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WaitlistRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class WaitlistMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str


class WaitlistMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    waitlist_entry_id: UUID
    sender_id: UUID
    body: str
    created_at: datetime


class WaitlistBypassCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    name: str
    studio_name: str | None = None
