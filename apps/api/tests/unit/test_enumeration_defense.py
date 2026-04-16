"""Enumeration defense tests — constant-time response utilities."""

from __future__ import annotations

import asyncio
import time

import pytest

from dailyriff_api.services.enumeration_defense import constant_time_response


class TestConstantTimeResponse:
    @pytest.mark.asyncio
    async def test_fast_operation_is_padded_to_minimum(self) -> None:
        async def fast_op():
            return {"status": "ok"}

        start = time.monotonic()
        result = await constant_time_response(fast_op, min_duration=0.1)
        elapsed = time.monotonic() - start

        assert result == {"status": "ok"}
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_slow_operation_is_not_delayed_further(self) -> None:
        async def slow_op():
            await asyncio.sleep(0.05)
            return {"status": "ok"}

        start = time.monotonic()
        result = await constant_time_response(slow_op, min_duration=0.02)
        elapsed = time.monotonic() - start

        assert result == {"status": "ok"}
        assert elapsed < 0.15

    @pytest.mark.asyncio
    async def test_exception_still_respects_minimum_duration(self) -> None:
        async def failing_op():
            raise ValueError("not found")

        start = time.monotonic()
        with pytest.raises(ValueError, match="not found"):
            await constant_time_response(failing_op, min_duration=0.1)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.1
