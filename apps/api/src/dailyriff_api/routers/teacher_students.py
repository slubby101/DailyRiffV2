"""Teacher-students endpoints: student list/detail, parent permissions, loans.

Studio-scoped — requires auth + owner/teacher membership.

  GET    /studios/{studio_id}/students                 — list students
  GET    /studios/{studio_id}/students/{user_id}       — student detail (parents, loans)
  PATCH  /studios/{studio_id}/parent-children/{id}     — update permission flags
  GET    /studios/{studio_id}/loans                    — list all loans
  POST   /studios/{studio_id}/loans                    — create loan
  GET    /studios/{studio_id}/loans/{id}               — get loan
  PATCH  /studios/{studio_id}/loans/{id}               — update loan (mark returned)
  DELETE /studios/{studio_id}/loans/{id}               — delete loan
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
from dailyriff_api.schemas.teacher_students import (
    LoanCreateRequest,
    LoanResponse,
    LoanUpdateRequest,
    ParentChildPermissions,
    ParentChildPermissionUpdate,
    ParentInfo,
    StudentDetail,
    StudentListItem,
)

router = APIRouter(tags=["teacher-students"])

LOAN_COLUMNS = (
    "id, studio_id, student_user_id, item_name, description, "
    "loaned_at, returned_at, created_by, created_at, updated_at"
)

_LOAN_UPDATABLE = {"item_name", "description", "returned_at"}


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
            detail="Only studio owners and teachers can manage students",
        )
    return membership["role"]


# ---------------------------------------------------------------------------
# Student list
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/students",
    response_model=list[StudentListItem],
    responses=PROTECTED_RESPONSES,
)
async def list_students(
    studio_id: UUID,
    search: str | None = Query(None, description="Search by email"),
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[StudentListItem]:
    """List all students in a studio. Teacher/owner only."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        if search:
            rows = await conn.fetch(
                """
                SELECT sm.user_id, au.email, sm.role, sm.joined_at
                FROM studio_members sm
                LEFT JOIN auth.users au ON au.id = sm.user_id
                WHERE sm.studio_id = $1
                  AND sm.role = 'student'
                  AND (au.email ILIKE '%' || $2 || '%')
                ORDER BY sm.joined_at DESC
                LIMIT $3 OFFSET $4
                """,
                studio_id,
                search,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT sm.user_id, au.email, sm.role, sm.joined_at
                FROM studio_members sm
                LEFT JOIN auth.users au ON au.id = sm.user_id
                WHERE sm.studio_id = $1 AND sm.role = 'student'
                ORDER BY sm.joined_at DESC
                LIMIT $2 OFFSET $3
                """,
                studio_id,
                limit,
                offset,
            )

    return [StudentListItem(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Student detail
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/students/{student_user_id}",
    response_model=StudentDetail,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Student not found"}},
)
async def get_student_detail(
    studio_id: UUID,
    student_user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> StudentDetail:
    """Get student detail including parents and loans. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        # Get student membership
        student = await conn.fetchrow(
            """
            SELECT sm.user_id, au.email, sm.role, sm.joined_at
            FROM studio_members sm
            LEFT JOIN auth.users au ON au.id = sm.user_id
            WHERE sm.studio_id = $1 AND sm.user_id = $2 AND sm.role = 'student'
            """,
            studio_id,
            student_user_id,
        )
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in this studio",
            )

        # Get parents of this student
        parent_rows = await conn.fetch(
            """
            SELECT pc.id, pc.parent_id, p.user_id AS parent_user_id,
                   pc.child_user_id, pc.is_primary_contact,
                   pc.can_manage_payments, pc.can_view_progress,
                   pc.can_communicate_with_teacher, pc.created_at
            FROM parent_children pc
            JOIN parents p ON p.id = pc.parent_id
            WHERE pc.child_user_id = $1 AND p.studio_id = $2
            ORDER BY pc.created_at
            """,
            student_user_id,
            studio_id,
        )

        # Group by parent
        parents_map: dict[UUID, ParentInfo] = {}
        for pr in parent_rows:
            pid = pr["parent_id"]
            if pid not in parents_map:
                parents_map[pid] = ParentInfo(
                    parent_id=pid,
                    user_id=pr["parent_user_id"],
                    children=[],
                )
            parents_map[pid].children.append(
                ParentChildPermissions(**dict(pr))
            )

        # Get loans for this student
        loan_rows = await conn.fetch(
            f"SELECT {LOAN_COLUMNS} FROM loans WHERE studio_id = $1 AND student_user_id = $2 ORDER BY loaned_at DESC",
            studio_id,
            student_user_id,
        )

    return StudentDetail(
        user_id=student["user_id"],
        email=student["email"],
        role=student["role"],
        joined_at=student["joined_at"],
        parents=list(parents_map.values()),
        loans=[LoanResponse(**dict(r)) for r in loan_rows],
    )


# ---------------------------------------------------------------------------
# Parent-child permission editing
# ---------------------------------------------------------------------------


@router.patch(
    "/studios/{studio_id}/parent-children/{pc_id}",
    response_model=ParentChildPermissions,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Not found"}},
)
async def update_parent_child_permissions(
    studio_id: UUID,
    pc_id: UUID,
    body: ParentChildPermissionUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> ParentChildPermissions:
    """Update per-child permission flags. Teacher/owner only."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        # Verify the parent_children row belongs to this studio
        existing = await conn.fetchrow(
            """
            SELECT pc.id FROM parent_children pc
            JOIN parents p ON p.id = pc.parent_id
            WHERE pc.id = $1 AND p.studio_id = $2
            """,
            pc_id,
            studio_id,
        )
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent-child relationship not found in this studio",
            )

        updatable = {"is_primary_contact", "can_manage_payments", "can_view_progress", "can_communicate_with_teacher"}
        columns = [c for c in updates if c in updatable]
        values = [updates[c] for c in columns]

        set_clause = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(columns))
        sql = f"""
            UPDATE parent_children SET {set_clause} WHERE id = $1
            RETURNING id, parent_id, child_user_id,
                      is_primary_contact, can_manage_payments,
                      can_view_progress, can_communicate_with_teacher, created_at
        """

        row = await conn.fetchrow(sql, pc_id, *values)

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Fetch parent_user_id for the response
    async with service_transaction() as conn:
        parent = await conn.fetchrow(
            "SELECT user_id FROM parents WHERE id = $1",
            row["parent_id"],
        )

    return ParentChildPermissions(
        **dict(row),
        parent_user_id=parent["user_id"] if parent else row["parent_id"],
    )


# ---------------------------------------------------------------------------
# Loans CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/studios/{studio_id}/loans",
    response_model=list[LoanResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_loans(
    studio_id: UUID,
    student_user_id: UUID | None = Query(None, description="Filter by student"),
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[LoanResponse]:
    """List loans in a studio. Teacher/owner only."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        if student_user_id:
            rows = await conn.fetch(
                f"SELECT {LOAN_COLUMNS} FROM loans WHERE studio_id = $1 AND student_user_id = $2 ORDER BY loaned_at DESC LIMIT $3 OFFSET $4",
                studio_id,
                student_user_id,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                f"SELECT {LOAN_COLUMNS} FROM loans WHERE studio_id = $1 ORDER BY loaned_at DESC LIMIT $2 OFFSET $3",
                studio_id,
                limit,
                offset,
            )

    return [LoanResponse(**dict(r)) for r in rows]


@router.post(
    "/studios/{studio_id}/loans",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_loan(
    studio_id: UUID,
    body: LoanCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> LoanResponse:
    """Create a loan record. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"""
            INSERT INTO loans (studio_id, student_user_id, item_name, description, loaned_at, created_by)
            VALUES ($1, $2, $3, $4, COALESCE($5, now()), $6)
            RETURNING {LOAN_COLUMNS}
            """,
            studio_id,
            body.student_user_id,
            body.item_name,
            body.description,
            body.loaned_at,
            user.id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create loan",
        )
    return LoanResponse(**dict(row))


@router.get(
    "/studios/{studio_id}/loans/{loan_id}",
    response_model=LoanResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Loan not found"}},
)
async def get_loan(
    studio_id: UUID,
    loan_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> LoanResponse:
    """Get a loan by ID. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        row = await conn.fetchrow(
            f"SELECT {LOAN_COLUMNS} FROM loans WHERE id = $1 AND studio_id = $2",
            loan_id,
            studio_id,
        )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LoanResponse(**dict(row))


@router.patch(
    "/studios/{studio_id}/loans/{loan_id}",
    response_model=LoanResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Loan not found"}},
)
async def update_loan(
    studio_id: UUID,
    loan_id: UUID,
    body: LoanUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> LoanResponse:
    """Update a loan (e.g. mark returned). Teacher/owner only."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return await get_loan(studio_id, loan_id, user)

    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        columns = [c for c in updates if c in _LOAN_UPDATABLE]
        values = [updates[c] for c in columns]

        set_clause = ", ".join(f"{col} = ${i + 3}" for i, col in enumerate(columns))
        now = datetime.now(tz.utc)
        set_clause += f", updated_at = ${len(columns) + 3}"

        sql = (
            f"UPDATE loans SET {set_clause} "
            f"WHERE id = $1 AND studio_id = $2 "
            f"RETURNING {LOAN_COLUMNS}"
        )

        row = await conn.fetchrow(sql, loan_id, studio_id, *values, now)

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LoanResponse(**dict(row))


@router.delete(
    "/studios/{studio_id}/loans/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Loan not found"}},
)
async def delete_loan(
    studio_id: UUID,
    loan_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Delete a loan record. Teacher/owner only."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        result = await conn.execute(
            "DELETE FROM loans WHERE id = $1 AND studio_id = $2",
            loan_id,
            studio_id,
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
