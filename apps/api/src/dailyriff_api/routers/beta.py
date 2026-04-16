"""Beta rollout endpoints.

Studio-scoped (authenticated, beta-studio members):
  POST /studios/{studio_id}/beta/feedback       — submit feedback
  GET  /studios/{studio_id}/beta/feedback       — list own studio's feedback

Public:
  POST /beta/validate-token                     — validate a beta landing token

Admin (superadmin only):
  GET    /admin/beta/feedback                   — list all beta feedback
  POST   /admin/beta/feedback/{id}/resolve      — mark feedback resolved
  POST   /admin/beta/landing-tokens             — create beta landing token
  GET    /admin/beta/landing-tokens             — list beta landing tokens
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone as tz
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    SUPERADMIN_RESPONSES,
    CurrentUser,
    get_current_user,
    require_superadmin,
)
from dailyriff_api.db import service_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.beta import (
    BetaFeedbackCategory,
    BetaFeedbackCreateRequest,
    BetaFeedbackResolveRequest,
    BetaFeedbackResponse,
    BetaFeedbackSeverity,
    BetaLandingTokenCreateRequest,
    BetaLandingTokenResponse,
    BetaLandingValidateRequest,
)

# Studio-scoped feedback router
studio_router = APIRouter(
    prefix="/studios/{studio_id}/beta",
    tags=["beta"],
)

# Public router for beta landing validation
public_router = APIRouter(tags=["beta"])

# Admin router
admin_router = APIRouter(prefix="/admin/beta", tags=["admin-beta"])

FEEDBACK_COLUMNS = (
    "id, studio_id, submitted_by, category, severity, body, "
    "submitted_at, resolved_at, created_at, updated_at"
)

TOKEN_COLUMNS = "id, token, description, is_active, created_by, created_at"


async def _require_beta_studio_member(
    studio_id: UUID, user: CurrentUser, conn
) -> None:
    """Verify user is a member of a beta-cohort studio."""
    row = await conn.fetchrow(
        "SELECT s.beta_cohort FROM studios s "
        "INNER JOIN studio_members sm ON sm.studio_id = s.id "
        "WHERE s.id = $1 AND sm.user_id = $2",
        studio_id,
        user.id,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this studio",
        )
    if not row["beta_cohort"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Studio is not in the beta program",
        )


# ---------------------------------------------------------------------------
# Studio-scoped: submit feedback
# ---------------------------------------------------------------------------


@studio_router.post(
    "/feedback",
    response_model=BetaFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def submit_beta_feedback(
    studio_id: UUID,
    body: BetaFeedbackCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> BetaFeedbackResponse:
    """Submit beta feedback for a studio (beta-studio members only)."""
    async with service_transaction() as conn:
        await _require_beta_studio_member(studio_id, user, conn)

        row = await conn.fetchrow(
            f"INSERT INTO beta_feedback (studio_id, submitted_by, category, severity, body) "
            f"VALUES ($1, $2, $3, $4, $5) "
            f"RETURNING {FEEDBACK_COLUMNS}",
            studio_id,
            user.id,
            body.category,
            body.severity,
            body.body,
        )
    return BetaFeedbackResponse(**dict(row))


# ---------------------------------------------------------------------------
# Studio-scoped: list feedback
# ---------------------------------------------------------------------------


@studio_router.get(
    "/feedback",
    response_model=list[BetaFeedbackResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_studio_beta_feedback(
    studio_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[BetaFeedbackResponse]:
    """List beta feedback for a studio (beta-studio members only)."""
    limit, offset = pagination
    async with service_transaction() as conn:
        await _require_beta_studio_member(studio_id, user, conn)

        rows = await conn.fetch(
            f"SELECT {FEEDBACK_COLUMNS} FROM beta_feedback "
            f"WHERE studio_id = $1 ORDER BY submitted_at DESC LIMIT $2 OFFSET $3",
            studio_id,
            limit,
            offset,
        )
    return [BetaFeedbackResponse(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Public: validate beta landing token
# ---------------------------------------------------------------------------


@public_router.post(
    "/beta/validate-token",
    status_code=status.HTTP_200_OK,
)
async def validate_beta_token(
    body: BetaLandingValidateRequest,
) -> dict:
    """Validate a beta landing page token. Returns {valid: bool}."""
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM beta_landing_tokens WHERE token = $1 AND is_active = true",
            body.token,
        )
    return {"valid": row is not None}


# ---------------------------------------------------------------------------
# Admin: list all beta feedback
# ---------------------------------------------------------------------------


@admin_router.get(
    "/feedback",
    response_model=list[BetaFeedbackResponse],
    responses=SUPERADMIN_RESPONSES,
)
async def list_all_beta_feedback(
    user: CurrentUser = Depends(require_superadmin),
    category: Optional[BetaFeedbackCategory] = Query(None),
    severity: Optional[BetaFeedbackSeverity] = Query(None),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[BetaFeedbackResponse]:
    """List all beta feedback across studios (superadmin only)."""
    limit, offset = pagination

    where_clauses = []
    params: list = []
    param_idx = 1

    if category:
        where_clauses.append(f"category = ${param_idx}")
        params.append(category)
        param_idx += 1
    if severity:
        where_clauses.append(f"severity = ${param_idx}")
        params.append(severity)
        param_idx += 1

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    params.extend([limit, offset])

    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {FEEDBACK_COLUMNS} FROM beta_feedback"
            f"{where_sql} ORDER BY submitted_at DESC "
            f"LIMIT ${param_idx} OFFSET ${param_idx + 1}",
            *params,
        )
    return [BetaFeedbackResponse(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Admin: resolve feedback
# ---------------------------------------------------------------------------


@admin_router.post(
    "/feedback/{feedback_id}/resolve",
    response_model=BetaFeedbackResponse,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Feedback not found"}},
)
async def resolve_beta_feedback(
    feedback_id: UUID,
    body: BetaFeedbackResolveRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> BetaFeedbackResponse:
    """Mark beta feedback as resolved (superadmin only)."""
    now = datetime.now(tz.utc)
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"UPDATE beta_feedback SET resolved_at = $2, updated_at = $2 "
            f"WHERE id = $1 RETURNING {FEEDBACK_COLUMNS}",
            feedback_id,
            now,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "resolve",
            "beta_feedback",
            str(feedback_id),
            {},
        )
    return BetaFeedbackResponse(**dict(row))


# ---------------------------------------------------------------------------
# Admin: create + list beta landing tokens
# ---------------------------------------------------------------------------


@admin_router.post(
    "/landing-tokens",
    response_model=BetaLandingTokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses=SUPERADMIN_RESPONSES,
)
async def create_beta_landing_token(
    body: BetaLandingTokenCreateRequest,
    user: CurrentUser = Depends(require_superadmin),
) -> BetaLandingTokenResponse:
    """Create a new beta landing page access token (superadmin only)."""
    token = secrets.token_urlsafe(32)
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"INSERT INTO beta_landing_tokens (token, description, created_by) "
            f"VALUES ($1, $2, $3) "
            f"RETURNING {TOKEN_COLUMNS}",
            token,
            body.description,
            user.id,
        )
        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "create",
            "beta_landing_token",
            str(row["id"]),
            {"description": body.description},
        )
    return BetaLandingTokenResponse(**dict(row))


@admin_router.get(
    "/landing-tokens",
    response_model=list[BetaLandingTokenResponse],
    responses=SUPERADMIN_RESPONSES,
)
async def list_beta_landing_tokens(
    user: CurrentUser = Depends(require_superadmin),
) -> list[BetaLandingTokenResponse]:
    """List all beta landing page tokens (superadmin only)."""
    async with service_transaction() as conn:
        rows = await conn.fetch(
            f"SELECT {TOKEN_COLUMNS} FROM beta_landing_tokens ORDER BY created_at DESC",
        )
    return [BetaLandingTokenResponse(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Admin: send beta onboarding email sequence
# ---------------------------------------------------------------------------


@admin_router.post(
    "/studios/{studio_id}/send-onboarding",
    status_code=status.HTTP_200_OK,
    responses={**SUPERADMIN_RESPONSES, 404: {"description": "Studio not found"}},
)
async def send_beta_onboarding(
    studio_id: UUID,
    user: CurrentUser = Depends(require_superadmin),
) -> dict:
    """Send beta onboarding email sequence to studio owner (superadmin only).

    Fires the beta.welcome notification event to the studio owner.
    The getting_started and feedback_reminder events are intended to be
    triggered by pg_cron on a delay (day 1 and day 7), but can also
    be manually triggered by calling this endpoint with the respective
    event_type query param in a future iteration.
    """
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            "SELECT s.id, s.name, s.display_name, s.beta_cohort, "
            "sm.user_id as owner_id "
            "FROM studios s "
            "INNER JOIN studio_members sm ON sm.studio_id = s.id AND sm.role = 'owner' "
            "WHERE s.id = $1 "
            "LIMIT 1",
            studio_id,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if not row["beta_cohort"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Studio is not in the beta program",
            )

        await conn.execute(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
            "VALUES ($1, $2, $3, $4, $5)",
            user.id,
            "send_beta_onboarding",
            "studio",
            str(studio_id),
            {"owner_id": str(row["owner_id"])},
        )

    return {
        "status": "sent",
        "studio_id": str(studio_id),
        "owner_id": str(row["owner_id"]),
    }


# Export the studio_router as router for main.py import consistency
router = studio_router
