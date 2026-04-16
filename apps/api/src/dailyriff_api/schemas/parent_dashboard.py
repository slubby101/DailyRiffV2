"""Parent dashboard schemas — children, schedule, progress, payments."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChildPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_primary_contact: bool
    can_manage_payments: bool
    can_view_progress: bool
    can_communicate_with_teacher: bool


class ChildSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_user_id: UUID
    email: str | None = None
    studio_id: UUID
    studio_name: str
    parent_child_id: UUID
    permissions: ChildPermissions
    next_lesson_date: date | None = None
    latest_assignment_title: str | None = None
    current_streak: int = 0


class ParentDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    children: list[ChildSummary]


class ChildScheduleItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_id: UUID
    occurrence_id: UUID | None = None
    start_date: date
    start_time: str | None = None
    end_time: str | None = None
    duration_minutes: int | None = None
    teacher_email: str | None = None
    status: str | None = None


class ChildProgressResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_user_id: UUID
    current_streak: int = 0
    longest_streak: int = 0
    is_active: bool = False
    total_practice_days: int = 0
    weekly_minutes: int = 0
    total_assignments: int = 0
    completed_assignments: int = 0
    recent_recordings: list[ChildRecordingItem] = []


class ChildRecordingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    assignment_id: UUID | None = None
    duration_seconds: int
    uploaded_at: datetime | None = None
    created_at: datetime


# Fix forward reference
ChildProgressResponse.model_rebuild()


class ChildPaymentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    amount: Decimal
    currency: str
    status: str
    method: str | None = None
    memo: str | None = None
    created_at: datetime


class ChildPaymentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_user_id: UUID
    studio_id: UUID
    total_pending: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    total_refunded: Decimal = Decimal("0")
    payments: list[ChildPaymentItem] = []
