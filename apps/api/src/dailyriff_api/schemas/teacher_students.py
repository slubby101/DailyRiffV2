"""Teacher-students schemas: student list, detail, parent-child permissions, loans."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Student list / detail
# ---------------------------------------------------------------------------


class StudentListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    email: str | None = None
    role: str
    joined_at: datetime


class ParentChildPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    parent_id: UUID
    parent_user_id: UUID
    child_user_id: UUID
    is_primary_contact: bool
    can_manage_payments: bool
    can_view_progress: bool
    can_communicate_with_teacher: bool
    created_at: datetime


class ParentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: UUID
    user_id: UUID
    children: list[ParentChildPermissions] = []


class StudentDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    email: str | None = None
    role: str
    joined_at: datetime
    parents: list[ParentInfo] = []
    loans: list["LoanResponse"] = []


# ---------------------------------------------------------------------------
# Parent-child permission update
# ---------------------------------------------------------------------------


class ParentChildPermissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_primary_contact: bool | None = None
    can_manage_payments: bool | None = None
    can_view_progress: bool | None = None
    can_communicate_with_teacher: bool | None = None


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------


class LoanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studio_id: UUID
    student_user_id: UUID
    item_name: str
    description: str | None = None
    loaned_at: datetime | None = None


class LoanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_name: str | None = None
    description: str | None = None
    returned_at: datetime | None = None


class LoanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    student_user_id: UUID
    item_name: str
    description: str | None = None
    loaned_at: datetime
    returned_at: datetime | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
