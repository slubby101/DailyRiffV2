"""Recording schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecordingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studio_id: UUID
    assignment_id: UUID | None = None
    mime_type: str
    duration_seconds: int = Field(ge=300, le=3600)
    file_size_bytes: int | None = None


class RecordingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    student_id: UUID
    assignment_id: UUID | None = None
    r2_object_key: str
    mime_type: str
    duration_seconds: int
    file_size_bytes: int | None = None
    uploaded_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UploadUrlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recording_id: UUID
    upload_url: str
    r2_object_key: str


class UploadConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_size_bytes: int | None = None


class PlaybackUrlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recording_id: UUID
    playback_url: str
    expires_in_seconds: int = 300
