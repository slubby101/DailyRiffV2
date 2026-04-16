"""Assignment and recording schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studio_id: UUID
    student_id: UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    pieces: list[str] | None = Field(default=None, max_length=10)
    techniques: list[str] | None = Field(default=None, max_length=15)
    due_date: datetime


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    teacher_id: UUID
    student_id: UUID
    title: str
    description: str | None = None
    pieces: list[str] | None = None
    techniques: list[str] | None = None
    due_date: datetime
    status: str
    feedback_text: str | None = None
    feedback_rating: int | None = None
    created_at: datetime
    updated_at: datetime


class AssignmentFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_text: str = Field(min_length=1, max_length=5000)
    feedback_rating: int = Field(ge=1, le=5)


class AcknowledgementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    assignment_id: UUID
    recording_id: UUID | None = None
    status: str
    acknowledged_at: datetime | None = None
    created_at: datetime
