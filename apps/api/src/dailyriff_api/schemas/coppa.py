"""COPPA VPC request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


CoppaConsentStatus = Literal["pending", "verified", "revoked", "expired"]


class CoppaInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_id: UUID
    studio_id: UUID


class CoppaInitiateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_id: UUID
    client_secret: str
    status: CoppaConsentStatus


class CoppaConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_id: UUID
    setup_intent_id: str


class CoppaSignedFormRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_id: UUID
    form_url: str


class CoppaRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_id: UUID


class CoppaConsentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    parent_id: UUID
    child_id: UUID
    studio_id: UUID
    stripe_setup_intent_id: str | None
    form_url: str | None
    status: CoppaConsentStatus
    verified_at: datetime | None
    revoked_at: datetime | None
    revocation_auto_delete_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CoppaWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    received: bool
