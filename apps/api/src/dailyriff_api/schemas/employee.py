"""DailyRiff employee schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


EmployeeRole = Literal["owner", "support", "verifier"]


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    role: EmployeeRole
    created_by: UUID | None = None
    notes: str | None = None
    created_at: datetime


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role: EmployeeRole
    notes: str | None = None


class EmployeeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: EmployeeRole | None = None
    notes: str | None = None
