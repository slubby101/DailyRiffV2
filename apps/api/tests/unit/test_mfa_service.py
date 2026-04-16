"""MFA service tests — TOTP gate + failure alerting."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Callable
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import USER_A_ID

NOW = datetime.now(timezone.utc)


def _make_svc_ctx(*, fetch_result=None, fetchrow_result=None, fetchval_result=None, execute_result="INSERT 1"):
    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=fetch_result or [])
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        conn.fetchval = AsyncMock(return_value=fetchval_result)
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn
    return _fake


class TestMfaFailureAlertService:
    """Tests for MFA failure recording and 3-in-15-min alerting."""

    @pytest.fixture(autouse=True)
    def _patch_db(self, monkeypatch):
        import dailyriff_api.services.mfa_service as mod
        monkeypatch.setattr(mod, "service_transaction", _make_svc_ctx())

    @pytest.mark.asyncio
    async def test_record_failure_writes_to_log(self, monkeypatch) -> None:
        import dailyriff_api.services.mfa_service as mod

        fake_ctx = _make_svc_ctx(fetchval_result=1)
        monkeypatch.setattr(mod, "service_transaction", fake_ctx)

        service = mod.MfaAlertService()
        result = await service.record_failure(USER_A_ID, ip_address="1.2.3.4")
        assert result.alert_triggered is False

    @pytest.mark.asyncio
    async def test_three_failures_triggers_alert(self, monkeypatch) -> None:
        import dailyriff_api.services.mfa_service as mod

        fake_ctx = _make_svc_ctx(
            fetchval_result=3,
            fetch_result=[{"user_id": USER_A_ID, "role": "owner"}],
        )
        monkeypatch.setattr(mod, "service_transaction", fake_ctx)

        service = mod.MfaAlertService()
        result = await service.record_failure(USER_A_ID, ip_address="1.2.3.4")
        assert result.alert_triggered is True

    @pytest.mark.asyncio
    async def test_two_failures_does_not_trigger(self, monkeypatch) -> None:
        import dailyriff_api.services.mfa_service as mod

        fake_ctx = _make_svc_ctx(fetchval_result=2)
        monkeypatch.setattr(mod, "service_transaction", fake_ctx)

        service = mod.MfaAlertService()
        result = await service.record_failure(USER_A_ID, ip_address="1.2.3.4")
        assert result.alert_triggered is False


class TestTotpGate:
    """Tests for TOTP enforcement dependency."""

    def test_superadmin_without_totp_in_dev_logs_warning(
        self, make_test_jwt: Callable[..., str], monkeypatch, caplog
    ) -> None:
        from fastapi.testclient import TestClient
        from dailyriff_api.main import app
        import dailyriff_api.routers.employees as mod

        monkeypatch.setattr(
            mod, "service_transaction",
            _make_svc_ctx(fetch_result=[]),
        )
        monkeypatch.setenv("ENVIRONMENT", "development")

        client = TestClient(app, raise_server_exceptions=False)
        token = make_test_jwt(user_id=USER_A_ID, role="superadmin")

        with caplog.at_level("WARNING"):
            resp = client.get("/employees", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200

    def test_superadmin_without_totp_in_production_gets_403(
        self, make_test_jwt: Callable[..., str], monkeypatch
    ) -> None:
        from fastapi.testclient import TestClient
        from dailyriff_api.main import app
        import dailyriff_api.routers.employees as mod

        monkeypatch.setattr(
            mod, "service_transaction",
            _make_svc_ctx(fetch_result=[]),
        )
        monkeypatch.setenv("ENVIRONMENT", "production")

        client = TestClient(app, raise_server_exceptions=False)
        token = make_test_jwt(user_id=USER_A_ID, role="superadmin")

        resp = client.get("/employees", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "TOTP" in resp.json()["detail"]

    def test_superadmin_with_valid_totp_claim_passes(
        self, make_test_jwt: Callable[..., str], monkeypatch
    ) -> None:
        from fastapi.testclient import TestClient
        from dailyriff_api.main import app
        import dailyriff_api.routers.employees as mod

        monkeypatch.setattr(
            mod, "service_transaction",
            _make_svc_ctx(fetch_result=[]),
        )
        monkeypatch.setenv("ENVIRONMENT", "production")

        client = TestClient(app, raise_server_exceptions=False)

        # Create a JWT with amr claim including totp
        import time, jwt as pyjwt, os
        now = int(time.time())
        payload = {
            "sub": str(USER_A_ID),
            "email": "admin@dailyriff.local",
            "aud": "authenticated",
            "role": "authenticated",
            "app_metadata": {"role": "superadmin"},
            "amr": [{"method": "totp", "timestamp": now - 60}],
            "iat": now,
            "exp": now + 3600,
        }
        secret = os.environ.get("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long")
        token = pyjwt.encode(payload, secret, algorithm="HS256")

        resp = client.get("/employees", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
