"""Lessons, attendance, absences, and ICS export endpoints.

Studio-scoped — requires auth + studio membership.

  POST   /studios/{studio_id}/lessons                           — create lesson
  GET    /studios/{studio_id}/lessons                           — list lessons
  GET    /studios/{studio_id}/lessons/{id}                      — get lesson
  PATCH  /studios/{studio_id}/lessons/{id}                      — update lesson
  DELETE /studios/{studio_id}/lessons/{id}                      — delete lesson
  POST   /studios/{studio_id}/lessons/{id}/generate-occurrences — materialize occurrences
  GET    /studios/{studio_id}/occurrences                       — list occurrences (date range)
  GET    /studios/{studio_id}/occurrences/{id}                  — get occurrence
  PATCH  /studios/{studio_id}/occurrences/{id}/attendance       — mark attendance
  PATCH  /studios/{studio_id}/occurrences/{id}/notes            — update notes
  POST   /studios/{studio_id}/occurrences/{id}/report-absence   — report absence
  GET    /studios/{studio_id}/absences                          — list absences
  PATCH  /studios/{studio_id}/absences/{id}                     — update absence status
  POST   /studios/{studio_id}/absences/{id}/schedule-makeup     — schedule makeup lesson
  GET    /studios/{studio_id}/absence-policy                    — get absence policy
  PUT    /studios/{studio_id}/absence-policy                    — upsert absence policy
  GET    /studios/{studio_id}/lessons/export.ics                — ICS calendar export
"""

from __future__ import annotations

from datetime import date, datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.lesson import (
    AbsencePolicyResponse,
    AbsencePolicyUpdateRequest,
    AbsenceReportRequest,
    AbsenceResponse,
    AttendanceMarkRequest,
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
    OccurrenceNotesRequest,
    OccurrenceResponse,
)
from dailyriff_api.services.attendance_service import (
    validate_absence_transition,
    validate_attendance_transition,
)
from dailyriff_api.services.lesson_service import (
    build_ics_calendar,
    build_ics_event,
    generate_occurrences,
)

router = APIRouter(tags=["lessons"])

LESSON_COLUMNS = (
    "id, studio_id, teacher_id, student_id, title, description, "
    "start_time, duration_minutes, start_date, end_date, is_recurring, "
    "cadence, day_of_week, cost, is_paid, is_trial, created_by, "
    "created_at, updated_at"
)

OCCURRENCE_COLUMNS = (
    "id, lesson_id, studio_id, occurrence_date, start_time, duration_minutes, "
    "attendance_status, marked_by, marked_at, teacher_notes, progress_notes, "
    "improvement_areas, strengths, next_focus, cost, is_paid, is_makeup, "
    "makeup_for_id, created_at, updated_at"
)

ABSENCE_COLUMNS = (
    "id, occurrence_id, studio_id, reported_by, reason, status, "
    "makeup_requested, makeup_occurrence_id, created_at, updated_at"
)

POLICY_COLUMNS = (
    "id, studio_id, max_absences_per_term, makeup_window_days, "
    "auto_notify_after_absences, cancellation_notice_hours, "
    "created_at, updated_at"
)

_LESSON_UPDATABLE = {
    "title", "description", "start_time", "duration_minutes",
    "end_date", "cost", "is_trial",
}


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
            detail="Only studio owners and teachers can manage lessons",
        )
    return membership["role"]


async def _require_studio_member(
    conn, studio_id: UUID, user_id: UUID
) -> str:
    """Verify caller is any member of the studio. Returns role."""
    membership = await conn.fetchrow(
        "SELECT role FROM studio_members WHERE studio_id = $1 AND user_id = $2",
        studio_id,
        user_id,
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this studio",
        )
    return membership["role"]


# ---------------------------------------------------------------------------
# Lessons CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/studios/{studio_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_lesson(
    studio_id: UUID,
    body: LessonCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> LessonResponse:
    """Create a lesson template. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        # Verify student is in the studio
        student = await conn.fetchrow(
            "SELECT user_id FROM studio_members "
            "WHERE studio_id = $1 AND user_id = $2 AND role = 'student'",
            studio_id,
            body.student_id,
        )
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in this studio",
            )

        # Validate recurrence fields
        if body.is_recurring and body.cadence == "one_time":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recurring lessons must have a cadence other than 'one_time'",
            )
        if body.is_recurring and body.day_of_week is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recurring lessons require day_of_week",
            )

        row = await conn.fetchrow(
            f"""
            INSERT INTO lessons (
                studio_id, teacher_id, student_id, title, description,
                start_time, duration_minutes, start_date, end_date,
                is_recurring, cadence, day_of_week, cost, is_trial, created_by
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $2
            )
            RETURNING {LESSON_COLUMNS}
            """,
            studio_id,
            user.id,
            body.student_id,
            body.title,
            body.description,
            body.start_time,
            body.duration_minutes,
            body.start_date,
            body.end_date,
            body.is_recurring,
            body.cadence,
            body.day_of_week,
            body.cost,
            body.is_trial,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return LessonResponse(**dict(row))


@router.get(
    "/studios/{studio_id}/lessons",
    response_model=list[LessonResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_lessons(
    studio_id: UUID,
    student_id: UUID | None = Query(None, description="Filter by student"),
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[LessonResponse]:
    """List lessons in a studio."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        if student_id:
            rows = await conn.fetch(
                f"SELECT {LESSON_COLUMNS} FROM lessons "
                f"WHERE studio_id = $1 AND student_id = $2 "
                f"ORDER BY start_date DESC LIMIT $3 OFFSET $4",
                studio_id,
                student_id,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                f"SELECT {LESSON_COLUMNS} FROM lessons "
                f"WHERE studio_id = $1 ORDER BY start_date DESC LIMIT $2 OFFSET $3",
                studio_id,
                limit,
                offset,
            )

    return [LessonResponse(**dict(r)) for r in rows]


@router.get(
    "/studios/{studio_id}/lessons/export.ics",
    responses={**PROTECTED_RESPONSES, 200: {"content": {"text/calendar": {}}}},
)
async def export_lessons_ics(
    studio_id: UUID,
    start: date | None = Query(None, description="Start date filter"),
    end: date | None = Query(None, description="End date filter"),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Export lesson occurrences as ICS calendar file."""
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        studio = await conn.fetchrow(
            "SELECT timezone FROM studios WHERE id = $1",
            studio_id,
        )
        if studio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        studio_tz = studio["timezone"]

        query = (
            f"SELECT lo.{OCCURRENCE_COLUMNS.replace('id,', 'lo.id,')}, "
            f"l.title AS lesson_title "
            f"FROM lesson_occurrences lo "
            f"JOIN lessons l ON l.id = lo.lesson_id "
            f"WHERE lo.studio_id = $1"
        )
        params: list = [studio_id]
        idx = 2

        if start:
            query += f" AND lo.occurrence_date >= ${idx}"
            params.append(start)
            idx += 1
        if end:
            query += f" AND lo.occurrence_date <= ${idx}"
            params.append(end)
            idx += 1

        query += " ORDER BY lo.occurrence_date, lo.start_time"

        rows = await conn.fetch(query, *params)

    events = []
    for r in rows:
        event = build_ics_event(
            lesson_title=r["lesson_title"],
            occurrence_date=r["occurrence_date"],
            start_time=r["start_time"],
            duration_minutes=r["duration_minutes"],
            studio_timezone=studio_tz,
            uid=f"{r['lo.id'] if 'lo.id' in r else r['id']}@dailyriff.com",
        )
        events.append(event)

    ics_body = build_ics_calendar(events, studio_tz)
    return Response(
        content=ics_body,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=lessons.ics"},
    )


@router.get(
    "/studios/{studio_id}/lessons/{lesson_id}",
    response_model=LessonResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def get_lesson(
    studio_id: UUID,
    lesson_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> LessonResponse:
    """Get a lesson by ID."""
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"SELECT {LESSON_COLUMNS} FROM lessons "
            f"WHERE id = $1 AND studio_id = $2",
            lesson_id,
            studio_id,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LessonResponse(**dict(row))


@router.patch(
    "/studios/{studio_id}/lessons/{lesson_id}",
    response_model=LessonResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def update_lesson(
    studio_id: UUID,
    lesson_id: UUID,
    body: LessonUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> LessonResponse:
    """Update a lesson. Teacher/owner only."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return await get_lesson(studio_id, lesson_id, user)

    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        columns = [c for c in updates if c in _LESSON_UPDATABLE]
        values = [updates[c] for c in columns]

        now = datetime.now(tz.utc)
        set_clause = ", ".join(
            f"{col} = ${i + 3}" for i, col in enumerate(columns)
        )
        set_clause += f", updated_at = ${len(columns) + 3}"

        sql = (
            f"UPDATE lessons SET {set_clause} "
            f"WHERE id = $1 AND studio_id = $2 "
            f"RETURNING {LESSON_COLUMNS}"
        )

        row = await conn.fetchrow(sql, lesson_id, studio_id, *values, now)

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LessonResponse(**dict(row))


@router.delete(
    "/studios/{studio_id}/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def delete_lesson(
    studio_id: UUID,
    lesson_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Delete a lesson and all its occurrences. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        result = await conn.execute(
            "DELETE FROM lessons WHERE id = $1 AND studio_id = $2",
            lesson_id,
            studio_id,
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Generate occurrences from a lesson template
# ---------------------------------------------------------------------------


@router.post(
    "/studios/{studio_id}/lessons/{lesson_id}/generate-occurrences",
    response_model=list[OccurrenceResponse],
    status_code=status.HTTP_201_CREATED,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def generate_lesson_occurrences(
    studio_id: UUID,
    lesson_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> list[OccurrenceResponse]:
    """Materialize occurrences from a lesson template. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        lesson = await conn.fetchrow(
            f"SELECT {LESSON_COLUMNS} FROM lessons "
            f"WHERE id = $1 AND studio_id = $2",
            lesson_id,
            studio_id,
        )
        if lesson is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        studio = await conn.fetchrow(
            "SELECT timezone FROM studios WHERE id = $1",
            studio_id,
        )
        if studio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        dates = generate_occurrences(
            start_date=lesson["start_date"],
            end_date=lesson["end_date"],
            cadence=lesson["cadence"],
            day_of_week=lesson["day_of_week"],
            start_time=lesson["start_time"],
            studio_timezone=studio["timezone"],
        )

        results = []
        for d in dates:
            row = await conn.fetchrow(
                f"""
                INSERT INTO lesson_occurrences (
                    lesson_id, studio_id, occurrence_date,
                    start_time, duration_minutes, cost
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (lesson_id, occurrence_date) DO NOTHING
                RETURNING {OCCURRENCE_COLUMNS}
                """,
                lesson_id,
                studio_id,
                d,
                lesson["start_time"],
                lesson["duration_minutes"],
                lesson["cost"],
            )
            if row is not None:
                results.append(OccurrenceResponse(**dict(row)))

    return results


# ---------------------------------------------------------------------------
# Occurrences
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/occurrences",
    response_model=list[OccurrenceResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_occurrences(
    studio_id: UUID,
    start: date | None = Query(None, description="Start date (inclusive)"),
    end: date | None = Query(None, description="End date (inclusive)"),
    student_id: UUID | None = Query(None, description="Filter by student"),
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[OccurrenceResponse]:
    """List lesson occurrences in a studio, optionally filtered by date range."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        query = f"SELECT lo.* FROM lesson_occurrences lo"
        conditions = ["lo.studio_id = $1"]
        params: list = [studio_id]
        idx = 2

        if student_id:
            query += " JOIN lessons l ON l.id = lo.lesson_id"
            conditions.append(f"l.student_id = ${idx}")
            params.append(student_id)
            idx += 1

        if start:
            conditions.append(f"lo.occurrence_date >= ${idx}")
            params.append(start)
            idx += 1
        if end:
            conditions.append(f"lo.occurrence_date <= ${idx}")
            params.append(end)
            idx += 1

        where = " AND ".join(conditions)
        query += f" WHERE {where} ORDER BY lo.occurrence_date, lo.start_time"
        query += f" LIMIT ${idx} OFFSET ${idx + 1}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

    return [OccurrenceResponse(**dict(r)) for r in rows]


@router.get(
    "/studios/{studio_id}/occurrences/{occurrence_id}",
    response_model=OccurrenceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def get_occurrence(
    studio_id: UUID,
    occurrence_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> OccurrenceResponse:
    """Get a single occurrence."""
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"SELECT {OCCURRENCE_COLUMNS} FROM lesson_occurrences "
            f"WHERE id = $1 AND studio_id = $2",
            occurrence_id,
            studio_id,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OccurrenceResponse(**dict(row))


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------


@router.patch(
    "/studios/{studio_id}/occurrences/{occurrence_id}/attendance",
    response_model=OccurrenceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def mark_attendance(
    studio_id: UUID,
    occurrence_id: UUID,
    body: AttendanceMarkRequest,
    user: CurrentUser = Depends(get_current_user),
) -> OccurrenceResponse:
    """Mark attendance for an occurrence. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        existing = await conn.fetchrow(
            "SELECT attendance_status FROM lesson_occurrences "
            "WHERE id = $1 AND studio_id = $2",
            occurrence_id,
            studio_id,
        )
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        current_status = existing["attendance_status"]
        if not validate_attendance_transition(current_status, body.attendance_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{current_status}' to '{body.attendance_status}'",
            )

        now = datetime.now(tz.utc)
        row = await conn.fetchrow(
            f"""
            UPDATE lesson_occurrences
            SET attendance_status = $3, marked_by = $4, marked_at = $5, updated_at = $5
            WHERE id = $1 AND studio_id = $2
            RETURNING {OCCURRENCE_COLUMNS}
            """,
            occurrence_id,
            studio_id,
            body.attendance_status,
            user.id,
            now,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OccurrenceResponse(**dict(row))


@router.patch(
    "/studios/{studio_id}/occurrences/{occurrence_id}/notes",
    response_model=OccurrenceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def update_occurrence_notes(
    studio_id: UUID,
    occurrence_id: UUID,
    body: OccurrenceNotesRequest,
    user: CurrentUser = Depends(get_current_user),
) -> OccurrenceResponse:
    """Update lesson notes for an occurrence. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        now = datetime.now(tz.utc)
        row = await conn.fetchrow(
            f"""
            UPDATE lesson_occurrences
            SET teacher_notes = COALESCE($3, teacher_notes),
                progress_notes = COALESCE($4, progress_notes),
                improvement_areas = COALESCE($5, improvement_areas),
                strengths = COALESCE($6, strengths),
                next_focus = COALESCE($7, next_focus),
                updated_at = $8
            WHERE id = $1 AND studio_id = $2
            RETURNING {OCCURRENCE_COLUMNS}
            """,
            occurrence_id,
            studio_id,
            body.teacher_notes,
            body.progress_notes,
            body.improvement_areas,
            body.strengths,
            body.next_focus,
            now,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return OccurrenceResponse(**dict(row))


# ---------------------------------------------------------------------------
# Absences
# ---------------------------------------------------------------------------


@router.post(
    "/studios/{studio_id}/occurrences/{occurrence_id}/report-absence",
    response_model=AbsenceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def report_absence(
    studio_id: UUID,
    occurrence_id: UUID,
    body: AbsenceReportRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AbsenceResponse:
    """Report an absence for a lesson occurrence. Any studio member can report."""
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        # Verify occurrence exists and belongs to studio
        occ = await conn.fetchrow(
            "SELECT id FROM lesson_occurrences WHERE id = $1 AND studio_id = $2",
            occurrence_id,
            studio_id,
        )
        if occ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        row = await conn.fetchrow(
            f"""
            INSERT INTO absences (
                occurrence_id, studio_id, reported_by, reason, makeup_requested
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING {ABSENCE_COLUMNS}
            """,
            occurrence_id,
            studio_id,
            user.id,
            body.reason,
            body.makeup_requested,
        )

        # Mark attendance as absent if currently scheduled
        await conn.execute(
            """
            UPDATE lesson_occurrences
            SET attendance_status = 'absent', marked_by = $3, marked_at = now(), updated_at = now()
            WHERE id = $1 AND studio_id = $2 AND attendance_status = 'scheduled'
            """,
            occurrence_id,
            studio_id,
            user.id,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return AbsenceResponse(**dict(row))


@router.get(
    "/studios/{studio_id}/absences",
    response_model=list[AbsenceResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_absences(
    studio_id: UUID,
    status_filter: str | None = Query(None, alias="status", description="Filter by absence status"),
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[AbsenceResponse]:
    """List absences in a studio."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        if status_filter:
            rows = await conn.fetch(
                f"SELECT {ABSENCE_COLUMNS} FROM absences "
                f"WHERE studio_id = $1 AND status = $2 "
                f"ORDER BY created_at DESC LIMIT $3 OFFSET $4",
                studio_id,
                status_filter,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                f"SELECT {ABSENCE_COLUMNS} FROM absences "
                f"WHERE studio_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                studio_id,
                limit,
                offset,
            )

    return [AbsenceResponse(**dict(r)) for r in rows]


@router.patch(
    "/studios/{studio_id}/absences/{absence_id}",
    response_model=AbsenceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def update_absence_status(
    studio_id: UUID,
    absence_id: UUID,
    target_status: str = Query(..., description="Target absence status"),
    user: CurrentUser = Depends(get_current_user),
) -> AbsenceResponse:
    """Update absence status. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        existing = await conn.fetchrow(
            "SELECT status FROM absences WHERE id = $1 AND studio_id = $2",
            absence_id,
            studio_id,
        )
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        current = existing["status"]
        if not validate_absence_transition(current, target_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{current}' to '{target_status}'",
            )

        now = datetime.now(tz.utc)
        row = await conn.fetchrow(
            f"""
            UPDATE absences SET status = $3, updated_at = $4
            WHERE id = $1 AND studio_id = $2
            RETURNING {ABSENCE_COLUMNS}
            """,
            absence_id,
            studio_id,
            target_status,
            now,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AbsenceResponse(**dict(row))


@router.post(
    "/studios/{studio_id}/absences/{absence_id}/schedule-makeup",
    response_model=AbsenceResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def schedule_makeup(
    studio_id: UUID,
    absence_id: UUID,
    makeup_date: date = Query(..., description="Date for the makeup lesson"),
    user: CurrentUser = Depends(get_current_user),
) -> AbsenceResponse:
    """Schedule a makeup lesson for an absence. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        absence = await conn.fetchrow(
            f"SELECT {ABSENCE_COLUMNS} FROM absences WHERE id = $1 AND studio_id = $2",
            absence_id,
            studio_id,
        )
        if absence is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        if absence["status"] not in ("reported", "acknowledged", "makeup_requested"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot schedule makeup from status '{absence['status']}'",
            )

        # Get the original occurrence to copy lesson details
        original = await conn.fetchrow(
            f"SELECT {OCCURRENCE_COLUMNS} FROM lesson_occurrences WHERE id = $1",
            absence["occurrence_id"],
        )
        if original is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        # Create makeup occurrence
        makeup = await conn.fetchrow(
            f"""
            INSERT INTO lesson_occurrences (
                lesson_id, studio_id, occurrence_date, start_time,
                duration_minutes, cost, is_makeup, makeup_for_id
            ) VALUES ($1, $2, $3, $4, $5, $6, true, $7)
            RETURNING {OCCURRENCE_COLUMNS}
            """,
            original["lesson_id"],
            studio_id,
            makeup_date,
            original["start_time"],
            original["duration_minutes"],
            original["cost"],
            original["id"],
        )

        # Update absence to link the makeup and transition status
        now = datetime.now(tz.utc)
        row = await conn.fetchrow(
            f"""
            UPDATE absences
            SET status = 'makeup_scheduled',
                makeup_occurrence_id = $3,
                updated_at = $4
            WHERE id = $1 AND studio_id = $2
            RETURNING {ABSENCE_COLUMNS}
            """,
            absence_id,
            studio_id,
            makeup["id"],
            now,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return AbsenceResponse(**dict(row))


# ---------------------------------------------------------------------------
# Absence policy
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/absence-policy",
    response_model=AbsencePolicyResponse | None,
    responses=PROTECTED_RESPONSES,
)
async def get_absence_policy(
    studio_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> AbsencePolicyResponse | None:
    """Get the studio's absence policy."""
    async with service_transaction() as conn:
        await _require_studio_member(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"SELECT {POLICY_COLUMNS} FROM studio_absence_policies "
            f"WHERE studio_id = $1",
            studio_id,
        )

    if row is None:
        return None
    return AbsencePolicyResponse(**dict(row))


@router.put(
    "/studios/{studio_id}/absence-policy",
    response_model=AbsencePolicyResponse,
    responses=PROTECTED_RESPONSES,
)
async def upsert_absence_policy(
    studio_id: UUID,
    body: AbsencePolicyUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AbsencePolicyResponse:
    """Create or update the studio's absence policy. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        updates = body.model_dump(exclude_none=True)
        now = datetime.now(tz.utc)

        row = await conn.fetchrow(
            f"""
            INSERT INTO studio_absence_policies (studio_id, {', '.join(updates.keys())})
            VALUES ($1, {', '.join(f'${i+2}' for i in range(len(updates)))})
            ON CONFLICT (studio_id) DO UPDATE SET
                {', '.join(f'{k} = EXCLUDED.{k}' for k in updates)},
                updated_at = ${len(updates) + 2}
            RETURNING {POLICY_COLUMNS}
            """,
            studio_id,
            *updates.values(),
            now,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return AbsencePolicyResponse(**dict(row))
