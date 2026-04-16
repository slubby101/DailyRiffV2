"""Parent dashboard endpoints — children, schedule, progress, payments.

Parent-scoped — requires auth + parent relationship.

  GET  /parent/children                          — list children with summary
  GET  /parent/children/{child_user_id}/schedule  — child lesson schedule
  GET  /parent/children/{child_user_id}/progress  — child streaks + recordings
  GET  /parent/children/{child_user_id}/payments  — child payment history (read-only)
"""

from __future__ import annotations

from datetime import date, timedelta, timezone as tz
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.parent_dashboard import (
    ChildPaymentItem,
    ChildPaymentsResponse,
    ChildPermissions,
    ChildProgressResponse,
    ChildRecordingItem,
    ChildScheduleItem,
    ChildSummary,
    ParentDashboardResponse,
)
from dailyriff_api.services.streak_service import compute_streaks, compute_weekly_minutes

router = APIRouter(prefix="/parent", tags=["parent-dashboard"])


async def _require_parent(conn, user_id: UUID) -> dict:
    """Verify user is a parent. Returns parent row or raises 403."""
    parent = await conn.fetchrow(
        "SELECT id, user_id, studio_id FROM parents WHERE user_id = $1", user_id
    )
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents can access parent dashboard",
        )
    return parent


async def _verify_parent_child(conn, parent_id: UUID, child_user_id: UUID) -> dict:
    """Verify parent-child relationship. Returns parent_children row or raises 403."""
    link = await conn.fetchrow(
        """SELECT pc.id, pc.parent_id, pc.child_user_id,
                  pc.is_primary_contact, pc.can_manage_payments,
                  pc.can_view_progress, pc.can_communicate_with_teacher,
                  p.studio_id
           FROM parent_children pc
           JOIN parents p ON p.id = pc.parent_id
           WHERE pc.parent_id = $1 AND pc.child_user_id = $2""",
        parent_id,
        child_user_id,
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No parent-child relationship found",
        )
    return link


# ---------------------------------------------------------------------------
# Children list (dashboard)
# ---------------------------------------------------------------------------


@router.get(
    "/children",
    response_model=ParentDashboardResponse,
    responses=PROTECTED_RESPONSES,
)
async def list_children(
    user: CurrentUser = Depends(get_current_user),
) -> ParentDashboardResponse:
    """List all children with dashboard summary data."""
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)

        # Get all children linked to this parent
        children_rows = await conn.fetch(
            """SELECT pc.id AS parent_child_id, pc.child_user_id,
                      pc.is_primary_contact, pc.can_manage_payments,
                      pc.can_view_progress, pc.can_communicate_with_teacher,
                      p.studio_id, s.name AS studio_name,
                      au.email
               FROM parent_children pc
               JOIN parents p ON p.id = pc.parent_id
               JOIN studios s ON s.id = p.studio_id
               LEFT JOIN auth.users au ON au.id = pc.child_user_id
               WHERE pc.parent_id = $1
               ORDER BY pc.created_at""",
            parent["id"],
        )

        children = []
        for cr in children_rows:
            # Next lesson for this child
            next_lesson = await conn.fetchrow(
                """SELECT lo.start_date
                   FROM lesson_occurrences lo
                   JOIN lessons l ON l.id = lo.lesson_id
                   WHERE l.student_id = $1 AND l.studio_id = $2
                     AND lo.start_date >= CURRENT_DATE
                     AND lo.status = 'scheduled'
                   ORDER BY lo.start_date ASC LIMIT 1""",
                cr["child_user_id"],
                cr["studio_id"],
            )

            # Latest assignment
            latest_assignment = await conn.fetchrow(
                """SELECT title FROM assignments
                   WHERE student_id = $1 AND studio_id = $2
                   ORDER BY created_at DESC LIMIT 1""",
                cr["child_user_id"],
                cr["studio_id"],
            )

            # Streak (only if can_view_progress)
            current_streak = 0
            if cr["can_view_progress"]:
                practice_rows = await conn.fetch(
                    """SELECT DATE(uploaded_at AT TIME ZONE 'UTC') as practice_date
                       FROM recordings WHERE student_id = $1
                       AND uploaded_at IS NOT NULL AND deleted_at IS NULL""",
                    cr["child_user_id"],
                )
                practice_dates = [r["practice_date"] for r in practice_rows]
                streak_result = compute_streaks(practice_dates, today=date.today())
                current_streak = streak_result.current_streak

            children.append(
                ChildSummary(
                    child_user_id=cr["child_user_id"],
                    email=cr["email"],
                    studio_id=cr["studio_id"],
                    studio_name=cr["studio_name"],
                    parent_child_id=cr["parent_child_id"],
                    permissions=ChildPermissions(
                        is_primary_contact=cr["is_primary_contact"],
                        can_manage_payments=cr["can_manage_payments"],
                        can_view_progress=cr["can_view_progress"],
                        can_communicate_with_teacher=cr["can_communicate_with_teacher"],
                    ),
                    next_lesson_date=next_lesson["start_date"] if next_lesson else None,
                    latest_assignment_title=latest_assignment["title"] if latest_assignment else None,
                    current_streak=current_streak,
                )
            )

    return ParentDashboardResponse(children=children)


# ---------------------------------------------------------------------------
# Child schedule
# ---------------------------------------------------------------------------


@router.get(
    "/children/{child_user_id}/schedule",
    response_model=list[ChildScheduleItem],
    responses=PROTECTED_RESPONSES,
)
async def get_child_schedule(
    child_user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[ChildScheduleItem]:
    """Upcoming lesson schedule for a child."""
    limit, offset = pagination
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)
        await _verify_parent_child(conn, parent["id"], child_user_id)

        rows = await conn.fetch(
            """SELECT l.id AS lesson_id, lo.id AS occurrence_id,
                      lo.start_date, lo.start_time, lo.end_time,
                      l.duration_minutes, lo.status,
                      au.email AS teacher_email
               FROM lesson_occurrences lo
               JOIN lessons l ON l.id = lo.lesson_id
               LEFT JOIN auth.users au ON au.id = l.teacher_id
               WHERE l.student_id = $1 AND lo.start_date >= CURRENT_DATE
               ORDER BY lo.start_date ASC
               LIMIT $2 OFFSET $3""",
            child_user_id,
            limit,
            offset,
        )

    return [ChildScheduleItem(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Child progress
# ---------------------------------------------------------------------------


@router.get(
    "/children/{child_user_id}/progress",
    response_model=ChildProgressResponse,
    responses=PROTECTED_RESPONSES,
)
async def get_child_progress(
    child_user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ChildProgressResponse:
    """Streaks, assignment completion, recent recordings for a child."""
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)
        link = await _verify_parent_child(conn, parent["id"], child_user_id)

        if not link["can_view_progress"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this child's progress",
            )

        studio_id = link["studio_id"]
        today = date.today()
        week_ago = today - timedelta(days=7)

        # Practice dates for streak
        practice_rows = await conn.fetch(
            """SELECT DATE(uploaded_at AT TIME ZONE 'UTC') as practice_date
               FROM recordings WHERE student_id = $1
               AND uploaded_at IS NOT NULL AND deleted_at IS NULL""",
            child_user_id,
        )
        practice_dates = [r["practice_date"] for r in practice_rows]

        # Weekly durations
        weekly_rows = await conn.fetch(
            """SELECT duration_seconds FROM recordings
               WHERE student_id = $1 AND uploaded_at IS NOT NULL
               AND deleted_at IS NULL
               AND DATE(uploaded_at AT TIME ZONE 'UTC') >= $2""",
            child_user_id,
            week_ago,
        )
        weekly_durations = [r["duration_seconds"] for r in weekly_rows]

        # Assignment counts
        assignment_counts = await conn.fetchrow(
            """SELECT
                 COUNT(*) AS total,
                 COUNT(*) FILTER (WHERE status = 'completed') AS completed
               FROM assignments
               WHERE student_id = $1 AND studio_id = $2""",
            child_user_id,
            studio_id,
        )

        # Recent recordings (last 5)
        recording_rows = await conn.fetch(
            """SELECT id, assignment_id, duration_seconds, uploaded_at, created_at
               FROM recordings WHERE student_id = $1
               AND uploaded_at IS NOT NULL AND deleted_at IS NULL
               ORDER BY uploaded_at DESC LIMIT 5""",
            child_user_id,
        )

    streak_result = compute_streaks(practice_dates, today=today)
    weekly_mins = compute_weekly_minutes(weekly_durations)

    return ChildProgressResponse(
        child_user_id=child_user_id,
        current_streak=streak_result.current_streak,
        longest_streak=streak_result.longest_streak,
        is_active=streak_result.is_active,
        total_practice_days=streak_result.total_practice_days,
        weekly_minutes=weekly_mins,
        total_assignments=assignment_counts["total"] if assignment_counts else 0,
        completed_assignments=assignment_counts["completed"] if assignment_counts else 0,
        recent_recordings=[ChildRecordingItem(**dict(r)) for r in recording_rows],
    )


# ---------------------------------------------------------------------------
# Child payments (read-only)
# ---------------------------------------------------------------------------


@router.get(
    "/children/{child_user_id}/payments",
    response_model=ChildPaymentsResponse,
    responses=PROTECTED_RESPONSES,
)
async def get_child_payments(
    child_user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> ChildPaymentsResponse:
    """Read-only payment history + outstanding balance for a child."""
    limit, offset = pagination
    async with service_transaction() as conn:
        parent = await _require_parent(conn, user.id)
        link = await _verify_parent_child(conn, parent["id"], child_user_id)

        if not link["can_manage_payments"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this child's payments",
            )

        studio_id = link["studio_id"]

        # Outstanding balance
        balance = await conn.fetchrow(
            """SELECT
                 COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) AS total_pending,
                 COALESCE(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END), 0) AS total_paid,
                 COALESCE(SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END), 0) AS total_refunded
               FROM payments
               WHERE studio_id = $1 AND student_user_id = $2""",
            studio_id,
            child_user_id,
        )

        # Payment history
        payment_rows = await conn.fetch(
            """SELECT id, amount, currency, status, method, memo, created_at
               FROM payments
               WHERE studio_id = $1 AND student_user_id = $2
               ORDER BY created_at DESC
               LIMIT $3 OFFSET $4""",
            studio_id,
            child_user_id,
            limit,
            offset,
        )

    return ChildPaymentsResponse(
        child_user_id=child_user_id,
        studio_id=studio_id,
        total_pending=balance["total_pending"],
        total_paid=balance["total_paid"],
        total_refunded=balance["total_refunded"],
        payments=[ChildPaymentItem(**dict(r)) for r in payment_rows],
    )
