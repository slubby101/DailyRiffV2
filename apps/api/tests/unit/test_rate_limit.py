"""Rate limiting middleware tests — slowapi + platform_settings integration."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from dailyriff_api.rate_limit import (
    create_limiter,
    get_route_limit,
    rate_limit_exceeded_handler,
    ROUTE_DEFAULTS,
    update_rate_config,
)


def _make_app() -> tuple[FastAPI, any]:
    """Build a minimal FastAPI app with rate limiting for testing."""
    app = FastAPI()
    limiter = create_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/unlimited")
    async def unlimited():
        return {"ok": True}

    @app.get("/limited")
    @limiter.limit("2/minute")
    async def limited(request: Request):
        return {"ok": True}

    return app, limiter


class TestRateLimitExceeded:
    def test_returns_429_when_limit_exceeded(self) -> None:
        app, _limiter = _make_app()
        client = TestClient(app, raise_server_exceptions=False)

        client.get("/limited")
        client.get("/limited")
        resp = client.get("/limited")

        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]

    def test_allows_requests_within_limit(self) -> None:
        app, _limiter = _make_app()
        client = TestClient(app, raise_server_exceptions=False)

        resp1 = client.get("/limited")
        resp2 = client.get("/limited")

        assert resp1.status_code == 200
        assert resp2.status_code == 200


class TestRouteDefaults:
    def test_known_route_returns_configured_default(self) -> None:
        assert get_route_limit("device_register") == ROUTE_DEFAULTS["device_register"]

    def test_unknown_route_returns_global_default(self) -> None:
        result = get_route_limit("nonexistent_route_xyz")
        assert result == "100/minute"


class TestDynamicRateConfig:
    def test_platform_settings_override_takes_precedence(self) -> None:
        update_rate_config({"device_register": "5/minute"})
        assert get_route_limit("device_register") == "5/minute"
        update_rate_config({})

    def test_clearing_override_reverts_to_default(self) -> None:
        update_rate_config({"device_register": "5/minute"})
        update_rate_config({})
        assert get_route_limit("device_register") == ROUTE_DEFAULTS["device_register"]


class TestStorageBackendSelection:
    def test_uses_redis_when_redis_url_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
        from dailyriff_api.rate_limit import _resolve_storage_uri

        assert _resolve_storage_uri() == "redis://localhost:6379"

    def test_falls_back_to_memory_when_redis_url_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REDIS_URL", raising=False)
        from dailyriff_api.rate_limit import _resolve_storage_uri

        assert _resolve_storage_uri() == "memory://"

    def test_falls_back_to_memory_when_redis_url_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_URL", "")
        from dailyriff_api.rate_limit import _resolve_storage_uri

        assert _resolve_storage_uri() == "memory://"

    def test_create_limiter_uses_resolved_storage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_URL", "redis://myredis:6379/0")
        from dailyriff_api.rate_limit import create_limiter

        lim = create_limiter()
        assert lim._storage_uri == "redis://myredis:6379/0"


class TestRefreshFromSettings:
    @pytest.mark.asyncio
    async def test_refresh_loads_overrides_from_settings_service(self) -> None:
        from dailyriff_api.rate_limit import refresh_from_settings

        class FakeSettings:
            async def get_cached(self, key: str):
                if key == "rate_limit_overrides":
                    return {"device_register": "1/minute", "custom_route": "50/hour"}
                return None

        await refresh_from_settings(FakeSettings())

        assert get_route_limit("device_register") == "1/minute"
        assert get_route_limit("custom_route") == "50/hour"
        update_rate_config({})

    @pytest.mark.asyncio
    async def test_refresh_ignores_none_settings(self) -> None:
        from dailyriff_api.rate_limit import refresh_from_settings

        update_rate_config({"device_register": "1/minute"})

        class FakeSettings:
            async def get_cached(self, key: str):
                return None

        await refresh_from_settings(FakeSettings())
        assert get_route_limit("device_register") == "1/minute"
        update_rate_config({})
