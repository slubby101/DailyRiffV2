"""Retention cleanup service tests.

Verifies that cleanup functions correctly call the SQL functions and
return the deletion count.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from dailyriff_api.services.retention_service import (
    cleanup_mfa_failure_log,
    cleanup_idempotency_log,
)


def _mock_service_tx(*, fetchval_result=0):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        yield conn
    return _fake


class TestCleanupMfaFailureLog:
    @pytest.mark.asyncio
    async def test_returns_zero_when_nothing_to_delete(self) -> None:
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            _mock_service_tx(fetchval_result=0),
        ):
            count = await cleanup_mfa_failure_log()
        assert count == 0

    @pytest.mark.asyncio
    async def test_returns_deleted_count(self) -> None:
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            _mock_service_tx(fetchval_result=42),
        ):
            count = await cleanup_mfa_failure_log()
        assert count == 42

    @pytest.mark.asyncio
    async def test_calls_correct_sql_function(self) -> None:
        mock_tx = _mock_service_tx(fetchval_result=0)
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            mock_tx,
        ):
            await cleanup_mfa_failure_log()

        # Re-invoke to capture the conn mock
        async with mock_tx() as conn:
            pass
        # Verify via a fresh call that tracks the SQL
        conn_mock = AsyncMock()
        conn_mock.fetchval = AsyncMock(return_value=5)

        @asynccontextmanager
        async def tracking_tx():
            yield conn_mock

        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            tracking_tx,
        ):
            await cleanup_mfa_failure_log()

        conn_mock.fetchval.assert_called_once_with(
            "SELECT public.cleanup_mfa_failure_log()"
        )

    @pytest.mark.asyncio
    async def test_handles_none_return_as_zero(self) -> None:
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            _mock_service_tx(fetchval_result=None),
        ):
            count = await cleanup_mfa_failure_log()
        assert count == 0


class TestCleanupIdempotencyLog:
    @pytest.mark.asyncio
    async def test_returns_zero_when_nothing_to_delete(self) -> None:
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            _mock_service_tx(fetchval_result=0),
        ):
            count = await cleanup_idempotency_log()
        assert count == 0

    @pytest.mark.asyncio
    async def test_returns_deleted_count(self) -> None:
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            _mock_service_tx(fetchval_result=150),
        ):
            count = await cleanup_idempotency_log()
        assert count == 150

    @pytest.mark.asyncio
    async def test_calls_correct_sql_function(self) -> None:
        conn_mock = AsyncMock()
        conn_mock.fetchval = AsyncMock(return_value=0)

        @asynccontextmanager
        async def tracking_tx():
            yield conn_mock

        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            tracking_tx,
        ):
            await cleanup_idempotency_log()

        conn_mock.fetchval.assert_called_once_with(
            "SELECT public.cleanup_idempotency_log()"
        )

    @pytest.mark.asyncio
    async def test_handles_none_return_as_zero(self) -> None:
        with patch(
            "dailyriff_api.services.retention_service.service_transaction",
            _mock_service_tx(fetchval_result=None),
        ):
            count = await cleanup_idempotency_log()
        assert count == 0
