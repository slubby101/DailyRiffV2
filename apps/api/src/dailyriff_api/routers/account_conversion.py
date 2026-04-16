"""Account conversion endpoints: eligibility check + manual convert.

Studio-scoped — requires auth + owner/teacher membership.

  GET   /studios/{studio_id}/students/{child_user_id}/conversion-eligibility
  POST  /studios/{studio_id}/students/{child_user_id}/convert
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.account_conversion import (
    ConversionEligibilityResponse,
    ConvertRequest,
    ConvertResponse,
)
from dailyriff_api.services.account_conversion_service import (
    AccountConversionService,
)

router = APIRouter(tags=["account-conversion"])

_svc = AccountConversionService()


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
            detail="Only studio owners and teachers can manage account conversions",
        )
    return membership["role"]


@router.get(
    "/studios/{studio_id}/students/{child_user_id}/conversion-eligibility",
    response_model=ConversionEligibilityResponse,
    responses={
        **PROTECTED_RESPONSES,
        404: {"description": "Student not found in studio"},
    },
)
async def get_conversion_eligibility(
    studio_id: UUID,
    child_user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ConversionEligibilityResponse:
    """Check what account conversions are available for a student."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        student = await conn.fetchrow(
            "SELECT age_class FROM studio_members "
            "WHERE studio_id = $1 AND user_id = $2 AND role = 'student'",
            studio_id,
            child_user_id,
        )
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in studio",
            )

        current_age_class = student["age_class"]
        if current_age_class is None:
            # No age class set — no conversions available
            return ConversionEligibilityResponse(
                current="adult", conversions=[]
            )

        result = _svc.check_eligibility(current_age_class)
        return ConversionEligibilityResponse(**result)


@router.post(
    "/studios/{studio_id}/students/{child_user_id}/convert",
    response_model=ConvertResponse,
    responses={
        **PROTECTED_RESPONSES,
        404: {"description": "Student not found"},
        422: {"description": "Conversion requirements not met"},
    },
)
async def convert_account(
    studio_id: UUID,
    child_user_id: UUID,
    body: ConvertRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ConvertResponse:
    """Perform a manual account conversion for a student."""
    async with service_transaction() as conn:
        await _require_teacher_or_owner(conn, studio_id, user.id)

        student = await conn.fetchrow(
            "SELECT age_class FROM studio_members "
            "WHERE studio_id = $1 AND user_id = $2 AND role = 'student'",
            studio_id,
            child_user_id,
        )
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in studio",
            )

        current_age_class = student["age_class"]
        if current_age_class is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Student has no age class set — cannot convert",
            )

    try:
        result = await _svc.convert(
            child_user_id=child_user_id,
            studio_id=studio_id,
            current_age_class=current_age_class,
            target_age_class=body.target_age_class,
            converted_by=user.id,
            parent_consent_given=body.parent_consent_given,
            new_email=body.new_email,
        )
        return ConvertResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
