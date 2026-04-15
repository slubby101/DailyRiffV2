"""Platform settings service with in-process TTL cache."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from dailyriff_api.db import service_transaction


class SettingsService:
    def __init__(self, *, ttl_seconds: int = 30) -> None:
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, Any]] = {}

    async def get_cached(self, key: str) -> Any | None:
        cached = self._cache.get(key)
        if cached is not None:
            ts, value = cached
            if time.monotonic() - ts < self._ttl_seconds:
                return value
            del self._cache[key]

        async with service_transaction() as conn:
            row = await conn.fetchrow(
                "SELECT value_json FROM platform_settings WHERE key = $1",
                key,
            )
        if row is None:
            return None
        value = row["value_json"]
        self._cache[key] = (time.monotonic(), value)
        return value

    async def set(self, key: str, value: Any, user_id: UUID) -> dict[str, Any]:
        self._cache.pop(key, None)

        async with service_transaction() as conn:
            row = await conn.fetchrow(
                "UPDATE platform_settings "
                "SET value_json = $1, updated_at = now(), updated_by = $2 "
                "WHERE key = $3 "
                "RETURNING id, key, value_json, description, category, updated_at, updated_by",
                value,
                user_id,
                key,
            )
            if row is not None:
                await conn.execute(
                    "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    user_id,
                    "update",
                    "platform_setting",
                    key,
                    {"new_value": value},
                )
        if row is None:
            raise KeyError(f"Setting '{key}' not found")
        return dict(row)
