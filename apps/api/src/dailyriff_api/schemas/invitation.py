"""Invitation request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


InvitationPersona = Literal["studio-owner", "teacher", "parent", "student"]
InvitationStatus = Literal["pending", "accepted", "declined", "expired", "revoked"]
AgeClass = Literal["minor", "teen", "adult"]


class InvitationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invited_email: str
    persona: InvitationPersona
    age_class: AgeClass | None = None


class InvitationBatchCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invited_email: str
    child_names: list[str]


class InvitationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    invited_by: UUID
    invited_email: str
    invited_user_id: UUID | None
    persona: InvitationPersona
    status: InvitationStatus
    age_class: AgeClass | None
    auto_approve: bool
    expires_at: datetime
    redeemed_at: datetime | None
    redeemed_by: UUID | None
    created_at: datetime
    updated_at: datetime


class InvitationRedeemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str


class InvitationRedeemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invitation_id: UUID
    studio_id: UUID
    persona: InvitationPersona
    status: InvitationStatus


class ParentChildResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    parent_id: UUID
    child_user_id: UUID
    is_primary_contact: bool
    can_manage_payments: bool
    can_view_progress: bool
    can_communicate_with_teacher: bool
    created_at: datetime


class ParentChildUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_primary_contact: bool | None = None
    can_manage_payments: bool | None = None
    can_view_progress: bool | None = None
    can_communicate_with_teacher: bool | None = None
