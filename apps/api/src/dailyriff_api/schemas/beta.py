"""Beta rollout request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


BetaFeedbackCategory = Literal["bug", "feature_request", "usability", "performance", "other"]
BetaFeedbackSeverity = Literal["critical", "high", "medium", "low"]


class BetaFeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: BetaFeedbackCategory = "other"
    severity: BetaFeedbackSeverity = "medium"
    body: str


class BetaFeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    submitted_by: UUID
    category: BetaFeedbackCategory
    severity: BetaFeedbackSeverity
    body: str
    submitted_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BetaFeedbackResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BetaLandingTokenCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None


class BetaLandingTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    token: str
    description: str | None
    is_active: bool
    created_by: UUID
    created_at: datetime


class BetaLandingValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
