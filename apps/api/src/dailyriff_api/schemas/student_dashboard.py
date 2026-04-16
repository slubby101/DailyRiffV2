"""Student dashboard schemas — streak, weekly minutes, assignment summary."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StreakResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_streak: int
    longest_streak: int
    is_active: bool
    total_practice_days: int
    weekly_minutes: int


class AssignmentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    due_date: date | None = None
    status: str
    created_at: datetime


class RecordingHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    assignment_id: UUID | None = None
    duration_seconds: int
    uploaded_at: datetime | None = None
    created_at: datetime


class StudentDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    streak: StreakResponse
    upcoming_assignments: list[AssignmentSummary]
    recent_recordings: list[RecordingHistoryItem]
