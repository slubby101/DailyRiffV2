"""Payment schemas for teacher payment ledger."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PaymentStatus = Literal["pending", "paid", "refunded"]


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_user_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    payer_user_id: UUID | None = None
    method: str | None = None
    memo: str | None = None


class PaymentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(None, gt=0)
    status: PaymentStatus | None = None
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
