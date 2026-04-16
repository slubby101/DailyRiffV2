"""Invitation endpoints — studio-scoped invite management + public redemption.

Studio-scoped (requires auth + studio membership):
  POST   /studios/{studio_id}/invitations           — create invitation
  GET    /studios/{studio_id}/invitations           — list studio invitations
  POST   /studios/{studio_id}/invitations/batch     — multi-child batch invite
  POST   /studios/{studio_id}/invitations/{id}/regenerate — regenerate token

Public (requires auth):
  POST   /invitations/redeem                        — redeem invitation by token
"""

from __future__ import annotations

from datetime import datetime, timezone as tz
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dailyriff_api.auth import CurrentUser, get_current_user
from dailyriff_api.db import service_transaction
from dailyriff_api.schemas.invitation import (
    InvitationBatchCreateRequest,
    InvitationCreateRequest,
    InvitationRedeemRequest,
    InvitationRedeemResponse,
    InvitationResponse,
    InvitationStatus,
)
from dailyriff_api.services.invitation_service import (
    create_batch_parent_invitation,
    create_invitation,
    list_studio_invitations,
    redeem_invitation,
    regenerate_invitation,
)

studio_router = APIRouter(tags=["invitations"])
public_router = APIRouter(tags=["invitations"])

INVITATION_RESPONSE_FIELDS = {
    "id", "studio_id", "invited_by", "invited_email", "invited_user_id",
    "persona", "status", "age_class", "auto_approve", "expires_at",
    "redeemed_at", "redeemed_by", "created_at", "updated_at",
}


def _to_response(row: dict) -> InvitationResponse:
    """Convert a DB row dict to an InvitationResponse, excluding token_hash."""
    return InvitationResponse(**{k: v for k, v in row.items() if k in INVITATION_RESPONSE_FIELDS})


# ---------------------------------------------------------------------------
# Studio-scoped: create invitation
# ---------------------------------------------------------------------------


@studio_router.post(
    "/studios/{studio_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_studio_invitation(
    studio_id: UUID,
    body: InvitationCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> InvitationResponse:
    """Create an invitation for a person to join this studio."""
    async with service_transaction() as conn:
        # Verify caller is owner or teacher in the studio
        membership = await conn.fetchrow(
            "SELECT role FROM studio_members WHERE studio_id = $1 AND user_id = $2",
            studio_id,
            user.id,
        )
        if membership is None or membership["role"] not in ("owner", "teacher"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only studio owners and teachers can send invitations",
            )

        row, _token = await create_invitation(
            conn,
            studio_id=studio_id,
            invited_by=user.id,
            invited_email=body.invited_email,
            persona=body.persona,
            age_class=body.age_class,
        )

        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "create_invitation",
            "invitation",
            str(row["id"]),
            {"email": body.invited_email, "persona": body.persona},
        )

    return _to_response(row)


# ---------------------------------------------------------------------------
# Studio-scoped: list invitations
# ---------------------------------------------------------------------------


@studio_router.get(
    "/studios/{studio_id}/invitations",
    response_model=list[InvitationResponse],
)
async def list_invitations(
    studio_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    status_filter: Optional[InvitationStatus] = Query(None, alias="status"),
) -> list[InvitationResponse]:
    """List invitations for a studio."""
    async with service_transaction() as conn:
        membership = await conn.fetchrow(
            "SELECT role FROM studio_members WHERE studio_id = $1 AND user_id = $2",
            studio_id,
            user.id,
        )
        if membership is None or membership["role"] not in ("owner", "teacher"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only studio owners and teachers can view invitations",
            )

        rows = await list_studio_invitations(
            conn, studio_id=studio_id, status_filter=status_filter
        )

    return [_to_response(r) for r in rows]


# ---------------------------------------------------------------------------
# Studio-scoped: batch invite (multi-child)
# ---------------------------------------------------------------------------


@studio_router.post(
    "/studios/{studio_id}/invitations/batch",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_invitation(
    studio_id: UUID,
    body: InvitationBatchCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> InvitationResponse:
    """Create a single parent invitation for multiple children."""
    if not body.child_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="child_names must contain at least one name",
        )

    async with service_transaction() as conn:
        membership = await conn.fetchrow(
            "SELECT role FROM studio_members WHERE studio_id = $1 AND user_id = $2",
            studio_id,
            user.id,
        )
        if membership is None or membership["role"] not in ("owner", "teacher"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only studio owners and teachers can send invitations",
            )

        row, _token = await create_batch_parent_invitation(
            conn,
            studio_id=studio_id,
            invited_by=user.id,
            invited_email=body.invited_email,
            child_names=body.child_names,
        )

        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "create_batch_invitation",
            "invitation",
            str(row["id"]),
            {"email": body.invited_email, "children": body.child_names},
        )

    return _to_response(row)


# ---------------------------------------------------------------------------
# Studio-scoped: regenerate token
# ---------------------------------------------------------------------------


@studio_router.post(
    "/studios/{studio_id}/invitations/{invitation_id}/regenerate",
    response_model=InvitationResponse,
)
async def regenerate_invitation_token(
    studio_id: UUID,
    invitation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> InvitationResponse:
    """Regenerate the token for an invitation, invalidating the prior token."""
    async with service_transaction() as conn:
        membership = await conn.fetchrow(
            "SELECT role FROM studio_members WHERE studio_id = $1 AND user_id = $2",
            studio_id,
            user.id,
        )
        if membership is None or membership["role"] not in ("owner", "teacher"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only studio owners and teachers can regenerate invitations",
            )

        result = await regenerate_invitation(conn, invitation_id=invitation_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        row, _token = result

        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "regenerate_invitation",
            "invitation",
            str(invitation_id),
            {},
        )

    return _to_response(row)


# ---------------------------------------------------------------------------
# Public: redeem invitation
# ---------------------------------------------------------------------------


@public_router.post(
    "/invitations/redeem",
    response_model=InvitationRedeemResponse,
)
async def redeem_invitation_endpoint(
    body: InvitationRedeemRequest,
    user: CurrentUser = Depends(get_current_user),
) -> InvitationRedeemResponse:
    """Redeem an invitation token, joining the studio."""
    async with service_transaction() as conn:
        result = await redeem_invitation(
            conn, token=body.token, redeemed_by=user.id
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or already-used invitation token",
            )

        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "redeem_invitation",
            "invitation",
            str(result["id"]),
            {"studio_id": str(result["studio_id"]), "persona": result["persona"]},
        )

    return InvitationRedeemResponse(
        invitation_id=result["id"],
        studio_id=result["studio_id"],
        persona=result["persona"],
        status=result["status"],
    )


# Main router combines both
router = studio_router
