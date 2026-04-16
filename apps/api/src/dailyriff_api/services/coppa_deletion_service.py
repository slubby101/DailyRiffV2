"""COPPA 15-day grace deletion service.

Handles parent-initiated child data deletion: initiate → confirm → schedule →
T-7/T-1 reminders → T-0 hard-delete. Parent can cancel any time before T-0.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone as tz
from typing import Any
from uuid import UUID


COPPA_DELETION_COLUMNS = (
    "id, parent_id, child_id, studio_id, status, confirmation_token_hash, "
    "email_confirmed_at, scheduled_delete_at, t7_reminder_sent_at, "
    "t1_reminder_sent_at, completed_at, cancelled_at, created_at, updated_at"
)

_DEFAULT_GRACE_DAYS = 15


class CoppaDeletionService:
    @staticmethod
    async def initiate_deletion(
        *,
        conn: Any,
        parent_id: UUID,
        child_id: UUID,
        studio_id: UUID,
    ) -> dict[str, Any]:
        """Create a pending deletion request. Returns dict with confirmation_token."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        row = await conn.fetchrow(
            f"INSERT INTO coppa_deletion_requests "
            f"(parent_id, child_id, studio_id, confirmation_token_hash) "
            f"VALUES ($1, $2, $3, $4) "
            f"RETURNING {COPPA_DELETION_COLUMNS}",
            parent_id,
            child_id,
            studio_id,
            token_hash,
        )

        result = dict(row)
        result["confirmation_token"] = token
        return result

    @staticmethod
    async def confirm_deletion(
        *,
        conn: Any,
        request_id: UUID,
        confirmation_token: str,
        grace_days: int = _DEFAULT_GRACE_DAYS,
    ) -> dict[str, Any] | None:
        """Confirm a pending deletion request via email token. Schedules hard-delete."""
        row = await conn.fetchrow(
            f"SELECT {COPPA_DELETION_COLUMNS} FROM coppa_deletion_requests "
            f"WHERE id = $1",
            request_id,
        )
        if row is None or row["status"] != "pending_confirmation":
            return None

        token_hash = hashlib.sha256(confirmation_token.encode()).hexdigest()
        if token_hash != row["confirmation_token_hash"]:
            return None

        now = datetime.now(tz.utc)
        scheduled_at = now + timedelta(days=grace_days)

        updated = await conn.fetchrow(
            f"UPDATE coppa_deletion_requests "
            f"SET status = 'scheduled', email_confirmed_at = $2, "
            f"    scheduled_delete_at = $3, updated_at = $2 "
            f"WHERE id = $1 AND status = 'pending_confirmation' "
            f"RETURNING {COPPA_DELETION_COLUMNS}",
            request_id,
            now,
            scheduled_at,
        )
        if updated is None:
            return None
        return dict(updated)

    @staticmethod
    async def cancel_deletion(
        *,
        conn: Any,
        request_id: UUID,
        parent_id: UUID,
    ) -> dict[str, Any] | None:
        """Cancel a scheduled (or pending) deletion request."""
        row = await conn.fetchrow(
            f"SELECT {COPPA_DELETION_COLUMNS} FROM coppa_deletion_requests "
            f"WHERE id = $1 AND parent_id = $2",
            request_id,
            parent_id,
        )
        if row is None or row["status"] not in ("pending_confirmation", "scheduled"):
            return None

        now = datetime.now(tz.utc)
        updated = await conn.fetchrow(
            f"UPDATE coppa_deletion_requests "
            f"SET status = 'cancelled', cancelled_at = $2, updated_at = $2 "
            f"WHERE id = $1 AND status IN ('pending_confirmation', 'scheduled') "
            f"RETURNING {COPPA_DELETION_COLUMNS}",
            request_id,
            now,
        )
        if updated is None:
            return None
        return dict(updated)

    @staticmethod
    async def get_deletion_status(
        *,
        conn: Any,
        parent_id: UUID,
        child_id: UUID,
        studio_id: UUID,
    ) -> dict[str, Any] | None:
        """Get the most recent active deletion request for a child."""
        row = await conn.fetchrow(
            f"SELECT {COPPA_DELETION_COLUMNS} FROM coppa_deletion_requests "
            f"WHERE parent_id = $1 AND child_id = $2 AND studio_id = $3 "
            f"  AND status IN ('pending_confirmation', 'scheduled') "
            f"ORDER BY created_at DESC LIMIT 1",
            parent_id,
            child_id,
            studio_id,
        )
        if row is None:
            return None
        return dict(row)

    @staticmethod
    async def run_hard_delete_worker(*, conn: Any) -> int:
        """Python wrapper for the pg_cron hard-delete SQL function."""
        result = await conn.fetchval("SELECT public.coppa_hard_delete_worker()")
        return result or 0
