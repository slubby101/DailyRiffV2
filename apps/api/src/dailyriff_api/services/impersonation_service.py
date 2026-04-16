"""Impersonation service — start/end sessions, scope restrictions, audit.

Superadmin can impersonate any user with a mandatory reason. Sessions support
silent mode (delayed notification) and live mode (red banner on every page).
Hard-enforced scope restrictions prevent dangerous operations while impersonating.
"""

from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Operations that are hard-blocked during impersonation.
# Attempts return 403 with a clear error message.
BLOCKED_ACTIONS: frozenset[str] = frozenset(
    {
        "change_password",
        "delete_account",
        "change_email",
        "change_2fa",
        "authorize_oauth",
        "delete_recording",
        "delete_message",
        "delete_child_data",
    }
)


def is_action_blocked_during_impersonation(action: str) -> bool:
    """Check whether *action* is forbidden during an impersonation session."""
    return action in BLOCKED_ACTIONS


async def start_session(
    conn: asyncpg.Connection,
    *,
    impersonator_id: UUID,
    target_user_id: UUID,
    reason: str,
    mode: str = "silent",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Start an impersonation session.

    Validates:
    - Target user exists in auth.users
    - No active session already exists for this impersonator
    - Impersonator is not targeting themselves
    """
    if impersonator_id == target_user_id:
        raise ValueError("Cannot impersonate yourself")

    # Check target user exists
    target = await conn.fetchrow(
        "SELECT id FROM auth.users WHERE id = $1", target_user_id
    )
    if target is None:
        raise ValueError("Target user not found")

    # Check no active session
    active = await conn.fetchrow(
        "SELECT id FROM impersonation_sessions "
        "WHERE impersonator_user_id = $1 AND ended_at IS NULL",
        impersonator_id,
    )
    if active is not None:
        raise ValueError("An active impersonation session already exists")

    row = await conn.fetchrow(
        "INSERT INTO impersonation_sessions "
        "(impersonator_user_id, target_user_id, reason, mode, ip_address, user_agent) "
        "VALUES ($1, $2, $3, $4::impersonation_mode, $5, $6) "
        "RETURNING id, impersonator_user_id, target_user_id, studio_id, "
        "reason, mode, ip_address, user_agent, started_at, ended_at, "
        "notification_sent_at",
        impersonator_id,
        target_user_id,
        reason.strip(),
        mode,
        ip_address,
        user_agent,
    )

    # Audit log
    await conn.execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
        "VALUES ($1, $2, $3, $4, $5)",
        impersonator_id,
        "impersonation_start",
        "user",
        str(target_user_id),
        {"reason": reason.strip(), "mode": mode, "session_id": str(row["id"])},
    )

    logger.info(
        "Impersonation session %s started: %s → %s (mode=%s)",
        row["id"],
        impersonator_id,
        target_user_id,
        mode,
    )
    return dict(row)


async def end_session(
    conn: asyncpg.Connection,
    *,
    session_id: UUID,
    impersonator_id: UUID,
) -> dict:
    """End an active impersonation session."""
    row = await conn.fetchrow(
        "UPDATE impersonation_sessions "
        "SET ended_at = now() "
        "WHERE id = $1 AND impersonator_user_id = $2 AND ended_at IS NULL "
        "RETURNING id, impersonator_user_id, target_user_id, studio_id, "
        "reason, mode, ip_address, user_agent, started_at, ended_at, "
        "notification_sent_at",
        session_id,
        impersonator_id,
    )
    if row is None:
        raise ValueError("No active session found")

    # Audit log
    await conn.execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
        "VALUES ($1, $2, $3, $4, $5)",
        impersonator_id,
        "impersonation_end",
        "user",
        str(row["target_user_id"]),
        {"session_id": str(session_id)},
    )

    logger.info("Impersonation session %s ended", session_id)
    return dict(row)


async def get_active_session(
    conn: asyncpg.Connection,
    *,
    impersonator_id: UUID,
) -> dict | None:
    """Get the currently active impersonation session for an impersonator."""
    row = await conn.fetchrow(
        "SELECT id, impersonator_user_id, target_user_id, studio_id, "
        "reason, mode, ip_address, user_agent, started_at, ended_at, "
        "notification_sent_at "
        "FROM impersonation_sessions "
        "WHERE impersonator_user_id = $1 AND ended_at IS NULL",
        impersonator_id,
    )
    return dict(row) if row else None


async def validate_session(
    conn: asyncpg.Connection,
    *,
    session_id: UUID,
) -> dict | None:
    """Validate a session is active and return its details. Used by auth middleware."""
    row = await conn.fetchrow(
        "SELECT id, impersonator_user_id, target_user_id, mode "
        "FROM impersonation_sessions "
        "WHERE id = $1 AND ended_at IS NULL "
        "AND started_at > now() - interval '8 hours'",
        session_id,
    )
    return dict(row) if row else None


async def list_sessions_for_target(
    conn: asyncpg.Connection,
    *,
    target_user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List impersonation sessions where the given user was the target.

    Used to populate the Account Access Log on the user's settings page.
    Includes playback count from impersonation_playback_log.
    """
    rows = await conn.fetch(
        "SELECT s.id AS session_id, s.impersonator_user_id, s.reason, "
        "s.mode, s.started_at, s.ended_at, "
        "COALESCE(p.playback_count, 0)::int AS playback_count "
        "FROM impersonation_sessions s "
        "LEFT JOIN LATERAL ("
        "  SELECT COUNT(*)::int AS playback_count "
        "  FROM impersonation_playback_log pl "
        "  WHERE pl.session_id = s.id"
        ") p ON TRUE "
        "WHERE s.target_user_id = $1 "
        "ORDER BY s.started_at DESC "
        "LIMIT $2 OFFSET $3",
        target_user_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


async def mark_notification_sent(
    conn: asyncpg.Connection,
    *,
    session_id: UUID,
) -> None:
    """Mark that the target user has been notified about this impersonation session."""
    await conn.execute(
        "UPDATE impersonation_sessions SET notification_sent_at = now() "
        "WHERE id = $1",
        session_id,
    )
