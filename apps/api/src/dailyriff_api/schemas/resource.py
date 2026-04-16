"""Resource schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResourceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studio_id: UUID
    title: str
    url: str
    description: str | None = None
    category: str | None = None


class ResourceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    url: str | None = None
    description: str | None = None
    category: str | None = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    title: str
    url: str
    description: str | None = None
    category: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
