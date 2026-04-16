"""Business-rule caps — per-entity daily/lifetime limits read from platform_settings."""

from __future__ import annotations

from typing import Any

from dailyriff_api.db import service_transaction

DEFAULT_CAPS: dict[str, int] = {
    "recordings_per_student_per_day": 50,
    "messages_per_user_per_day": 200,
    "waitlist_per_email_lifetime": 1,
    "waitlist_per_ip_lifetime": 3,
    "push_per_user_per_day": 20,
    "coppa_vpc_per_parent_per_day": 3,
}


_ALLOWED_TABLES: dict[str, set[str]] = {
    "recordings": {"student_id", "user_id"},
    "messages": {"sender_id", "user_id"},
    "waitlist_entries": {"email", "ip_address"},
    "user_push_subscriptions": {"user_id"},
    "coppa_consents": {"parent_id"},
}


class BusinessCapsService:
    def __init__(self, *, settings_service: Any | None = None) -> None:
        self._settings = settings_service

    async def _get_cap(self, cap_key: str) -> int:
        if self._settings is not None:
            val = await self._settings.get_cached(f"cap_{cap_key}")
            if val is not None and isinstance(val, int):
                return val
        return DEFAULT_CAPS[cap_key]

    async def check_cap(
        self,
        cap_key: str,
        *,
        entity_id: str,
        table: str,
        entity_column: str,
        time_window: str = "today",
    ) -> bool:
        allowed_cols = _ALLOWED_TABLES.get(table)
        if allowed_cols is None:
            raise ValueError(f"Table {table!r} not in business caps allowlist")
        if entity_column not in allowed_cols:
            raise ValueError(f"Column {entity_column!r} not allowed for table {table!r}")

        cap = await self._get_cap(cap_key)

        if time_window == "today":
            where_time = "AND created_at >= CURRENT_DATE"
        else:
            where_time = ""

        async with service_transaction() as conn:
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM {table} "
                f"WHERE {entity_column} = $1 {where_time}",
                entity_id,
            )

        return count < cap
