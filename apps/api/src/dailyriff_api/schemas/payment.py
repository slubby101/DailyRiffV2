"""Payment schemas for teacher payment ledger."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_user_id: UUID
    amount: Decimal
    currency: str = "USD"
    payer_user_id: UUID | None = None
    status: str = "pending"
    method: str | None = None
    memo: str | None = None


class PaymentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = None
    status: str | None = None
    method: str | None = None
    memo: str | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    student_user_id: UUID
    amount: Decimal
    currency: str
    payer_user_id: UUID | None = None
    status: str
    method: str | None = None
    memo: str | None = None
    refunded_at: datetime | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class OutstandingBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_user_id: UUID
    studio_id: UUID
    total_pending: Decimal
    total_paid: Decimal
    total_refunded: Decimal
