"""Student dashboard endpoints — streak, assignments, recording history.

Provides the aggregated data for the student web dashboard.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.student_dashboard import (
    AssignmentSummary,
    RecordingHistoryItem,
    StreakResponse,
    StudentDashboardResponse,
)
from dailyriff_api.services.streak_service import compute_streaks, compute_weekly_minutes

router = APIRouter(prefix="/student", tags=["student-dashboard"])


@router.get(
    "/dashboard",
    response_model=StudentDashboardResponse,
    responses=PROTECTED_RESPONSES,
)
async def get_student_dashboard(
    user: CurrentUser = Depends(get_current_user),
) -> StudentDashboardResponse:
    """Aggregated student dashboard: streak, upcoming assignments, recent recordings."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    async with rls_transaction(user.id) as conn:
        # Practice dates for streak computation (all uploaded recording dates)
        practice_rows = await conn.fetch(
            "SELECT DATE(uploaded_at AT TIME ZONE 'UTC') as practice_date "
            "FROM recordings WHERE student_id = $1 AND uploaded_at IS NOT NULL "
            "AND deleted_at IS NULL "
            "AND uploaded_at >= now() - interval '1 year' "
            "ORDER BY uploaded_at DESC",
            user.id,
        )
        practice_dates = [row["practice_date"] for row in practice_rows]

        # Weekly recording durations for weekly minutes
        weekly_rows = await conn.fetch(
            "SELECT duration_seconds FROM recordings "
            "WHERE student_id = $1 AND uploaded_at IS NOT NULL "
            "AND deleted_at IS NULL "
            "AND DATE(uploaded_at AT TIME ZONE 'UTC') >= $2",
            user.id,
            week_ago,
        )
        weekly_durations = [row["duration_seconds"] for row in weekly_rows]

        # Upcoming assignments (pending/active, ordered by due date)
        assignment_rows = await conn.fetch(
            "SELECT id, title, due_date, status, created_at "
            "FROM assignments WHERE student_id = $1 "
            "AND status IN ('pending', 'active') "
            "ORDER BY due_date ASC NULLS LAST, created_at DESC "
            "LIMIT 10",
            user.id,
        )

        # Recent recordings (last 5)
        recording_rows = await conn.fetch(
            "SELECT id, assignment_id, duration_seconds, uploaded_at, created_at "
            "FROM recordings WHERE student_id = $1 AND uploaded_at IS NOT NULL "
            "AND deleted_at IS NULL "
            "ORDER BY uploaded_at DESC LIMIT 5",
            user.id,
        )

    streak_result = compute_streaks(practice_dates, today=today)
    weekly_mins = compute_weekly_minutes(weekly_durations)

    return StudentDashboardResponse(
        streak=StreakResponse(
            current_streak=streak_result.current_streak,
            longest_streak=streak_result.longest_streak,
            is_active=streak_result.is_active,
            total_practice_days=streak_result.total_practice_days,
            weekly_minutes=weekly_mins,
        ),
        upcoming_assignments=[
            AssignmentSummary(**dict(r)) for r in assignment_rows
        ],
        recent_recordings=[
            RecordingHistoryItem(**dict(r)) for r in recording_rows
        ],
    )


@router.get(
    "/streak",
    response_model=StreakResponse,
    responses=PROTECTED_RESPONSES,
)
async def get_streak(
    user: CurrentUser = Depends(get_current_user),
) -> StreakResponse:
    """Current streak and weekly minutes for the authenticated student."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    async with rls_transaction(user.id) as conn:
        practice_rows = await conn.fetch(
            "SELECT DATE(uploaded_at AT TIME ZONE 'UTC') as practice_date "
            "FROM recordings WHERE student_id = $1 AND uploaded_at IS NOT NULL "
            "AND deleted_at IS NULL",
            user.id,
        )
        practice_dates = [row["practice_date"] for row in practice_rows]

        weekly_rows = await conn.fetch(
            "SELECT duration_seconds FROM recordings "
            "WHERE student_id = $1 AND uploaded_at IS NOT NULL "
            "AND deleted_at IS NULL "
            "AND DATE(uploaded_at AT TIME ZONE 'UTC') >= $2",
            user.id,
            week_ago,
        )
        weekly_durations = [row["duration_seconds"] for row in weekly_rows]

    streak_result = compute_streaks(practice_dates, today=today)
    weekly_mins = compute_weekly_minutes(weekly_durations)

    return StreakResponse(
        current_streak=streak_result.current_streak,
        longest_streak=streak_result.longest_streak,
        is_active=streak_result.is_active,
        total_practice_days=streak_result.total_practice_days,
        weekly_minutes=weekly_mins,
    )


@router.get(
    "/assignments",
    response_model=list[AssignmentSummary],
    responses=PROTECTED_RESPONSES,
)
async def list_student_assignments(
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[AssignmentSummary]:
    """List assignments for the authenticated student."""
    limit, offset = pagination
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            "SELECT id, title, due_date, status, created_at "
            "FROM assignments WHERE student_id = $1 "
            "ORDER BY due_date ASC NULLS LAST, created_at DESC "
            "LIMIT $2 OFFSET $3",
            user.id,
            limit,
            offset,
        )
    return [AssignmentSummary(**dict(r)) for r in rows]


@router.get(
    "/recordings",
    response_model=list[RecordingHistoryItem],
    responses=PROTECTED_RESPONSES,
)
async def list_student_recordings(
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[RecordingHistoryItem]:
    """Recording history for the authenticated student."""
    limit, offset = pagination
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            "SELECT id, assignment_id, duration_seconds, uploaded_at, created_at "
            "FROM recordings WHERE student_id = $1 AND uploaded_at IS NOT NULL "
            "AND deleted_at IS NULL "
            "ORDER BY uploaded_at DESC LIMIT $2 OFFSET $3",
            user.id,
            limit,
            offset,
        )
    return [RecordingHistoryItem(**dict(r)) for r in rows]
