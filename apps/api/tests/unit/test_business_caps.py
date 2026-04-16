"""Business-rule caps service tests — per-entity daily limits."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from dailyriff_api.services.business_caps import BusinessCapsService, DEFAULT_CAPS


def _mock_service_tx(*, fetchval_result=0):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        yield conn
    return _fake


class TestCheckCap:
    @pytest.mark.asyncio
    async def test_allows_when_under_cap(self) -> None:
        from unittest.mock import patch

        svc = BusinessCapsService()
        with patch(
            "dailyriff_api.services.business_caps.service_transaction",
            _mock_service_tx(fetchval_result=10),
        ):
            allowed = await svc.check_cap(
                "recordings_per_student_per_day",
                entity_id="user-123",
                table="recordings",
                entity_column="student_id",
            )
        assert allowed is True

    @pytest.mark.asyncio
    async def test_rejects_when_at_cap(self) -> None:
        from unittest.mock import patch

        svc = BusinessCapsService()
        with patch(
            "dailyriff_api.services.business_caps.service_transaction",
            _mock_service_tx(fetchval_result=50),
        ):
            allowed = await svc.check_cap(
                "recordings_per_student_per_day",
                entity_id="user-123",
                table="recordings",
                entity_column="student_id",
            )
        assert allowed is False

    @pytest.mark.asyncio
    async def test_uses_custom_cap_from_settings(self) -> None:
        from unittest.mock import patch

        class FakeSettings:
            async def get_cached(self, key: str):
                if key == "cap_recordings_per_student_per_day":
                    return 5
                return None

        svc = BusinessCapsService(settings_service=FakeSettings())
        with patch(
            "dailyriff_api.services.business_caps.service_transaction",
            _mock_service_tx(fetchval_result=5),
        ):
            allowed = await svc.check_cap(
                "recordings_per_student_per_day",
                entity_id="user-123",
                table="recordings",
                entity_column="student_id",
            )
        assert allowed is False


class TestDefaultCaps:
    def test_all_expected_caps_defined(self) -> None:
        expected = [
            "recordings_per_student_per_day",
            "messages_per_user_per_day",
            "waitlist_per_email_lifetime",
            "waitlist_per_ip_lifetime",
            "push_per_user_per_day",
            "coppa_vpc_per_parent_per_day",
        ]
        for cap in expected:
            assert cap in DEFAULT_CAPS, f"Missing default cap: {cap}"

    def test_cap_values_are_positive_integers(self) -> None:
        for key, val in DEFAULT_CAPS.items():
            assert isinstance(val, int) and val > 0, f"{key} must be positive int"
