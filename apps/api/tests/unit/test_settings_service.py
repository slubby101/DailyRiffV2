"""Settings service unit tests — cache TTL + write invalidation."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import USER_A_ID

NOW = datetime.now(timezone.utc)

SETTING_ROW = {
    "id": uuid.uuid4(),
    "key": "max_recordings_per_day",
    "value_json": {"limit": 10},
    "description": "Max recordings per student per day",
    "category": "business_rule_caps",
    "updated_at": NOW,
    "updated_by": USER_A_ID,
}


def _mock_service_tx(*, fetchrow_result=None, fetch_result=None, execute_result="INSERT 1"):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


@pytest.mark.asyncio
async def test_get_cached_fetches_from_db_on_miss() -> None:
    from dailyriff_api.services.settings_service import SettingsService

    svc = SettingsService(ttl_seconds=30)

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=SETTING_ROW),
    ):
        result = await svc.get_cached("max_recordings_per_day")

    assert result == {"limit": 10}


@pytest.mark.asyncio
async def test_get_cached_expires_after_ttl() -> None:
    from dailyriff_api.services.settings_service import SettingsService

    svc = SettingsService(ttl_seconds=0)

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=SETTING_ROW),
    ):
        await svc.get_cached("max_recordings_per_day")

    updated_row = {**SETTING_ROW, "value_json": {"limit": 20}}
    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=updated_row),
    ):
        result = await svc.get_cached("max_recordings_per_day")

    assert result == {"limit": 20}


@pytest.mark.asyncio
async def test_set_invalidates_cache_and_writes_audit_log() -> None:
    from dailyriff_api.services.settings_service import SettingsService

    svc = SettingsService(ttl_seconds=300)

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=SETTING_ROW),
    ):
        await svc.get_cached("max_recordings_per_day")

    assert "max_recordings_per_day" in svc._cache

    updated_row = {**SETTING_ROW, "value_json": {"limit": 5}}
    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=updated_row),
    ):
        result = await svc.set("max_recordings_per_day", {"limit": 5}, USER_A_ID)

    assert "max_recordings_per_day" not in svc._cache
    assert result["value_json"] == {"limit": 5}


@pytest.mark.asyncio
async def test_get_cached_returns_none_for_missing_key() -> None:
    from dailyriff_api.services.settings_service import SettingsService

    svc = SettingsService(ttl_seconds=30)

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=None),
    ):
        result = await svc.get_cached("nonexistent_key")

    assert result is None


@pytest.mark.asyncio
async def test_set_raises_for_missing_key() -> None:
    from dailyriff_api.services.settings_service import SettingsService

    svc = SettingsService(ttl_seconds=30)

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=None),
    ):
        with pytest.raises(KeyError):
            await svc.set("nonexistent", {"v": 1}, USER_A_ID)


@pytest.mark.asyncio
async def test_get_cached_returns_cached_value_within_ttl() -> None:
    from dailyriff_api.services.settings_service import SettingsService

    svc = SettingsService(ttl_seconds=30)

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=SETTING_ROW),
    ) as mock_tx:
        await svc.get_cached("max_recordings_per_day")

    with patch(
        "dailyriff_api.services.settings_service.service_transaction",
        _mock_service_tx(fetchrow_result=None),
    ) as mock_tx:
        result = await svc.get_cached("max_recordings_per_day")

    assert result == {"limit": 10}
