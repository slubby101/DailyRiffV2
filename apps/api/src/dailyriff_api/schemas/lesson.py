"""Lesson, attendance, and absence schemas."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LessonCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studio_id: UUID
    student_id: UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    start_time: time
    duration_minutes: int = Field(ge=15, le=180)
    start_date: date
    end_date: date | None = None
    is_recurring: bool = False
    cadence: str = "one_time"
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    cost: float | None = None
    is_trial: bool = False


class LessonUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=180)
    end_date: date | None = None
    cost: float | None = None
    is_trial: bool | None = None


class LessonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    teacher_id: UUID
    student_id: UUID
    title: str
    description: str | None = None
    start_time: time
    duration_minutes: int
    start_date: date
    end_date: date | None = None
    is_recurring: bool
    cadence: str
    day_of_week: int | None = None
    cost: float | None = None
    is_paid: bool
    is_trial: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class OccurrenceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_id: UUID
    occurrence_date: date
    start_time: time
    duration_minutes: int = Field(ge=15, le=180)
    cost: float | None = None
    is_makeup: bool = False
    makeup_for_id: UUID | None = None


class OccurrenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    lesson_id: UUID
    studio_id: UUID
    occurrence_date: date
    start_time: time
    duration_minutes: int
    attendance_status: str
    marked_by: UUID | None = None
    marked_at: datetime | None = None
    teacher_notes: str | None = None
    progress_notes: str | None = None
    improvement_areas: str | None = None
    strengths: str | None = None
    next_focus: str | None = None
    cost: float | None = None
    is_paid: bool
    is_makeup: bool
    makeup_for_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AttendanceMarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attendance_status: str = Field(
        pattern="^(present|absent|late|excused|cancelled)$"
    )


class OccurrenceNotesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    teacher_notes: str | None = None
    progress_notes: str | None = None
    improvement_areas: str | None = None
    strengths: str | None = None
    next_focus: str | None = None


class AbsenceReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None
    makeup_requested: bool = False


class AbsenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    occurrence_id: UUID
    studio_id: UUID
    reported_by: UUID
    reason: str | None = None
    status: str
    makeup_requested: bool
    makeup_occurrence_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AbsencePolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    max_absences_per_term: int
    makeup_window_days: int
    auto_notify_after_absences: int
    cancellation_notice_hours: int
    created_at: datetime
    updated_at: datetime


class AbsencePolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_absences_per_term: int | None = Field(default=None, ge=1, le=50)
    makeup_window_days: int | None = Field(default=None, ge=1, le=365)
    auto_notify_after_absences: int | None = Field(default=None, ge=1, le=50)
    cancellation_notice_hours: int | None = Field(default=None, ge=0, le=168)
