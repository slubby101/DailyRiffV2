"""Studio schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StudioCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    display_name: str | None = None
    timezone: str = "America/New_York"


class StudioUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    timezone: str | None = None


class StudioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    timezone: str
    beta_cohort: bool
    state: str
    created_at: datetime
    updated_at: datetime
