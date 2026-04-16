"""DailyRiff employees endpoints — superadmin only."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    SUPERADMIN_RESPONSES,
    CurrentUser,
    require_superadmin,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.employee import (
    EmployeeCreateRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
)

router = APIRouter(prefix="/employees", tags=["employees"])

EMPLOYEE_COLUMNS = "id, user_id, role, created_by, notes, created_at"


@router.get("", response_model=list[EmployeeResponse], responses=SUPERADMIN_RESPONSES)
async def list_employees(
    user: CurrentUser = Depends(require_superadmin),
) -> list[EmployeeResponse]:
    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {EMPLOYEE_COLUMNS} FROM dailyriff_employees ORDER BY created_at DESC",
        )
    return [EmployeeResponse(**dict(r)) for r in rows]


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    responses=SUPERADMIN_RESPONSES,
)
async def create_employee(
    body: EmployeeCreateRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> EmployeeResponse:
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO dailyriff_employees (user_id, role, created_by, notes) "
            f"VALUES ($1, $2, $3, $4) "
            f"RETURNING {EMPLOYEE_COLUMNS}",
            body.user_id,
            body.role,
            user.id,
            body.notes,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create employee",
            )
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "create",
            "dailyriff_employee",
            str(body.user_id),
            {"role": body.role},
        )
    return EmployeeResponse(**dict(row))


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Employee not found"}},
)
async def get_employee(
    employee_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> EmployeeResponse:
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"SELECT {EMPLOYEE_COLUMNS} FROM dailyriff_employees WHERE id = $1",
            employee_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return EmployeeResponse(**dict(row))


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Employee not found"}},
)
async def update_employee(
    employee_id: UUID,
    body: EmployeeUpdateRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> EmployeeResponse:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return await get_employee(employee_id, user)

    columns = list(updates.keys())
    values = [updates[c] for c in columns]

    set_clause = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(columns))
    sql = (
        f"UPDATE dailyriff_employees SET {set_clause} "
        f"WHERE id = $1 "
        f"RETURNING {EMPLOYEE_COLUMNS}"
    )

    async with service_transaction() as conn:
        row = await conn.fetchrow(sql, employee_id, *values)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "update",
            "dailyriff_employee",
            str(employee_id),
            updates,
        )
    return EmployeeResponse(**dict(row))


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Employee not found"}},
)
async def delete_employee(
    employee_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> None:
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            "DELETE FROM dailyriff_employees WHERE id = $1 RETURNING id, user_id",
            employee_id,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "delete",
            "dailyriff_employee",
            str(employee_id),
            {"deleted_user_id": str(row["user_id"])},
        )
