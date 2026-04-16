"""Payment endpoints: teacher-entered payment ledger.

Studio-scoped — requires auth + owner/teacher membership.

  GET    /studios/{studio_id}/payments                              — list payments
  POST   /studios/{studio_id}/payments                              — add payment
  GET    /studios/{studio_id}/payments/{payment_id}                 — get payment
  PATCH  /studios/{studio_id}/payments/{payment_id}                 — update payment
  POST   /studios/{studio_id}/payments/{payment_id}/refund          — refund payment
  GET    /studios/{studio_id}/payments/outstanding/{student_user_id} — outstanding balance
"""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.payment import (
    OutstandingBalanceResponse,
    PaymentCreateRequest,
    PaymentResponse,
    PaymentUpdateRequest,
)

router = APIRouter(tags=["payments"])

PAYMENT_COLUMNS = (
    "id, studio_id, student_user_id, amount, currency, payer_user_id, "
    "status, method, memo, refunded_at, created_by, created_at, updated_at"
)

_UPDATABLE_COLUMNS = {"amount", "status", "method", "memo"}


async def _require_teacher_or_owner(
    conn, studio_id: UUID, user_id: UUID
) -> str:
    """Verify caller is owner or teacher in the studio. Returns role."""
    membership = await conn.fetchrow(
        "SELECT role FROM studio_members WHERE studio_id = $1 AND user_id = $2",
        studio_id,
        user_id,
    )
    if membership is None or membership["role"] not in ("owner", "teacher"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only studio owners and teachers can manage payments",
        )
    return membership["role"]


# ---------------------------------------------------------------------------
# List payments
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/payments",
    response_model=list[PaymentResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_payments(
    studio_id: UUID,
    student_user_id: UUID | None = Query(None, description="Filter by student"),
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[PaymentResponse]:
    """List payments in a studio. Teacher/owner only."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        if student_user_id:
            rows = await conn.fetch(
                f"SELECT {PAYMENT_COLUMNS} FROM payments "
                f"WHERE studio_id = $1 AND student_user_id = $2 "
                f"ORDER BY created_at DESC LIMIT $3 OFFSET $4",
                studio_id,
                student_user_id,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                f"SELECT {PAYMENT_COLUMNS} FROM payments "
                f"WHERE studio_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                studio_id,
                limit,
                offset,
            )

    return [PaymentResponse(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Add payment
# ---------------------------------------------------------------------------


@router.post(
    "/studios/{studio_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def add_payment(
    studio_id: UUID,
    body: PaymentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> PaymentResponse:
    """Add a payment record. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        student = await conn.fetchrow(
            "SELECT user_id FROM studio_members WHERE studio_id = $1 AND user_id = $2 AND role = 'student'",
            studio_id,
            body.student_user_id,
        )
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in this studio",
            )

        row = await conn.fetchrow(
            f"""
            INSERT INTO payments (
                studio_id, student_user_id, amount, currency,
                payer_user_id, status, method, memo, created_by
            )
            VALUES ($1, $2, $3, $4, $5, 'pending', $6, $7, $8)
            RETURNING {PAYMENT_COLUMNS}
            """,
            studio_id,
            body.student_user_id,
            body.amount,
            body.currency,
            body.payer_user_id,
            body.method,
            body.memo,
            user.id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment",
        )
    return PaymentResponse(**dict(row))


# ---------------------------------------------------------------------------
# Outstanding balance (must be before {payment_id} to avoid path conflict)
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/payments/outstanding/{student_user_id}",
    response_model=OutstandingBalanceResponse,
    responses=PROTECTED_RESPONSES,
)
async def get_outstanding_balance(
    studio_id: UUID,
    student_user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> OutstandingBalanceResponse:
    """Get outstanding balance for a student. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) AS total_pending,
                COALESCE(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END), 0) AS total_paid,
                COALESCE(SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END), 0) AS total_refunded
            FROM payments
            WHERE studio_id = $1 AND student_user_id = $2
            """,
            studio_id,
            student_user_id,
        )

    return OutstandingBalanceResponse(
        student_user_id=student_user_id,
        studio_id=studio_id,
        total_pending=row["total_pending"],
        total_paid=row["total_paid"],
        total_refunded=row["total_refunded"],
    )


# ---------------------------------------------------------------------------
# Get payment
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/payments/{payment_id}",
    response_model=PaymentResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Payment not found"}},
)
async def get_payment(
    studio_id: UUID,
    payment_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> PaymentResponse:
    """Get a payment by ID. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"SELECT {PAYMENT_COLUMNS} FROM payments WHERE id = $1 AND studio_id = $2",
            payment_id,
            studio_id,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PaymentResponse(**dict(row))


# ---------------------------------------------------------------------------
# Update payment
# ---------------------------------------------------------------------------


@router.patch(
    "/studios/{studio_id}/payments/{payment_id}",
    response_model=PaymentResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Payment not found"}},
)
async def update_payment(
    studio_id: UUID,
    payment_id: UUID,
    body: PaymentUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> PaymentResponse:
    """Update a payment. Teacher/owner only."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return await get_payment(studio_id, payment_id, user)

    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        columns = [c for c in updates if c in _UPDATABLE_COLUMNS]
        values = [updates[c] for c in columns]

        set_clause = ", ".join(f"{col} = ${i + 3}" for i, col in enumerate(columns))
        now = datetime.now(tz.utc)
        set_clause += f", updated_at = ${len(columns) + 3}"

        sql = (
            f"UPDATE payments SET {set_clause} "
            f"WHERE id = $1 AND studio_id = $2 "
            f"RETURNING {PAYMENT_COLUMNS}"
        )

        row = await conn.fetchrow(sql, payment_id, studio_id, *values, now)

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PaymentResponse(**dict(row))


# ---------------------------------------------------------------------------
# Refund payment
# ---------------------------------------------------------------------------


@router.post(
    "/studios/{studio_id}/payments/{payment_id}/refund",
    response_model=PaymentResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Payment not found"}},
)
async def refund_payment(
    studio_id: UUID,
    payment_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> PaymentResponse:
    """Refund a payment. Teacher/owner only."""
    now = datetime.now(tz.utc)
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"UPDATE payments SET status = 'refunded', refunded_at = $3, updated_at = $3 "
            f"WHERE id = $1 AND studio_id = $2 AND status = 'paid' "
            f"RETURNING {PAYMENT_COLUMNS}",
            payment_id,
            studio_id,
            now,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found or not in 'paid' status",
        )
    return PaymentResponse(**dict(row))
