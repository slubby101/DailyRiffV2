"""MFA failure alerting service.

Tracks failed MFA attempts and fires alerts when 3 failures occur within
15 minutes for the same user. Alerts go to all employee owners via
activity_logs and (future) email notification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from dailyriff_api.db import service_transaction

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3
WINDOW_MINUTES = 15


@dataclass(frozen=True)
class MfaFailureResult:
    failure_count: int
    alert_triggered: bool


class MfaAlertService:
    async def record_failure(
        self,
        user_id: UUID,
        *,
        ip_address: str | None = None,
    ) -> MfaFailureResult:
        async with service_transaction() as conn:
            # Record the failure
            await conn.execute(
                "INSERT INTO mfa_failure_log (user_id, ip_address) VALUES ($1, $2)",
                user_id,
                ip_address,
            )

            # Count failures in the window
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM mfa_failure_log "
                "WHERE user_id = $1 AND created_at > now() - interval '%s minutes'"
                % WINDOW_MINUTES,
                user_id,
            )

            alert_triggered = count >= FAILURE_THRESHOLD
            if alert_triggered:
                # Fetch owner employees to alert
                owners = await conn.fetch(
                    "SELECT user_id, role FROM dailyriff_employees WHERE role = 'owner'",
                )

                # Write activity log
                await conn.execute(
                    "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    user_id,
                    "mfa_failure_alert",
                    "mfa_failure_log",
                    str(user_id),
                    {
                        "failure_count": count,
                        "window_minutes": WINDOW_MINUTES,
                        "ip_address": ip_address,
                        "owner_count": len(owners),
                    },
                )

                logger.warning(
                    "MFA failure alert: user %s has %d failures in %d minutes",
                    user_id,
                    count,
                    WINDOW_MINUTES,
                )

        return MfaFailureResult(
            failure_count=count,
            alert_triggered=alert_triggered,
        )
