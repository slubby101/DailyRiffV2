"""Assignment endpoints — create, list, get, feedback, acknowledgements."""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction
from dailyriff_api.schemas.assignment import (
    AcknowledgementResponse,
    AssignmentCreateRequest,
    AssignmentFeedbackRequest,
    AssignmentResponse,
)
from dailyriff_api.services.assignment_service import AssignmentValidator

router = APIRouter(prefix="/assignments", tags=["assignments"])

ASSIGNMENT_COLUMNS = (
    "id, studio_id, teacher_id, student_id, title, description, "
    "pieces, techniques, due_date, status, feedback_text, feedback_rating, "
    "created_at, updated_at"
)

ACK_COLUMNS = "id, assignment_id, recording_id, status, acknowledged_at, created_at"


@router.get("", response_model=list[AssignmentResponse], responses=PROTECTED_RESPONSES)
async def list_assignments(
    user: CurrentUser = Depends(get_current_user),
) -> list[AssignmentResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {ASSIGNMENT_COLUMNS} FROM assignments ORDER BY created_at DESC",
        )
    return [AssignmentResponse(**dict(r)) for r in rows]


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_assignment(
    body: AssignmentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AssignmentResponse:
    errors = AssignmentValidator.validate(
        studio_id=body.studio_id,
        teacher_id=user.id,
        student_id=body.student_id,
        title=body.title,
        due_date=body.due_date,
        pieces=body.pieces,
        techniques=body.techniques,
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors,
        )

    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"INSERT INTO assignments "
            f"(studio_id, teacher_id, student_id, title, description, pieces, techniques, due_date) "
            f"VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
            f"RETURNING {ASSIGNMENT_COLUMNS}",
            body.studio_id,
            user.id,
            body.student_id,
            body.title,
            body.description,
            body.pieces,
            body.techniques,
            body.due_date,
        )
        # Create a pending acknowledgement for this assignment
        if row is not None:
            await conn.execute(
                "INSERT INTO assignment_acknowledgements (assignment_id) VALUES ($1)",
                row["id"],
            )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create assignment",
        )
    return AssignmentResponse(**dict(row))


@router.get(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Assignment not found"}},
)
async def get_assignment(
    assignment_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> AssignmentResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"SELECT {ASSIGNMENT_COLUMNS} FROM assignments WHERE id = $1",
            assignment_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AssignmentResponse(**dict(row))


@router.post(
    "/{assignment_id}/feedback",
    response_model=AssignmentResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Assignment not found"}},
)
async def add_feedback(
    assignment_id: UUID,
    body: AssignmentFeedbackRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AssignmentResponse:
    now = datetime.now(tz.utc)
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"UPDATE assignments "
            f"SET feedback_text = $2, feedback_rating = $3, updated_at = $4 "
            f"WHERE id = $1 "
            f"RETURNING {ASSIGNMENT_COLUMNS}",
            assignment_id,
            body.feedback_text,
            body.feedback_rating,
            now,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AssignmentResponse(**dict(row))


@router.get(
    "/{assignment_id}/acknowledgements",
    response_model=list[AcknowledgementResponse],
    responses={**PROTECTED_RESPONSES, 404: {"description": "Assignment not found"}},
)
async def list_acknowledgements(
    assignment_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> list[AcknowledgementResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {ACK_COLUMNS} FROM assignment_acknowledgements "
            f"WHERE assignment_id = $1 ORDER BY created_at DESC",
            assignment_id,
        )
    return [AcknowledgementResponse(**dict(r)) for r in rows]
