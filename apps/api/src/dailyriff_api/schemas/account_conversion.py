"""Account conversion request/response schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


AgeClass = Literal["minor", "teen", "adult"]


class ConversionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: AgeClass
    requires_parent_consent: bool
    requires_new_credentials: bool
    message: str


class ConversionEligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: AgeClass
    conversions: list[ConversionOption]


class ConvertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_age_class: AgeClass
    parent_consent_given: bool = False
    new_email: str | None = None


class ConvertResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_user_id: UUID
    studio_id: UUID
    previous_age_class: AgeClass
    new_age_class: AgeClass
    parent_access_removed: bool
    message: str
