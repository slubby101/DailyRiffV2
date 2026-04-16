"""Rate limiting middleware — slowapi + platform_settings integration."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

DEFAULT_GLOBAL_LIMIT = "100/minute"

ROUTE_DEFAULTS: dict[str, str] = {
    "device_register": "10/minute",
    "auth_login": "10/5minute",
    "auth_signup": "10/hour",
    "recordings_upload_url": "50/minute",
    "messages_send": "30/minute",
    "waitlist_submit": "5/hour",
    "coppa_vpc_charge": "3/hour",
    "password_reset": "5/hour",
}

_rate_config: dict[str, str] = {}

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def create_limiter() -> Limiter:
    return Limiter(key_func=get_remote_address, storage_uri="memory://")


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


def get_route_limit(route_key: str) -> str:
    return _rate_config.get(
        route_key, ROUTE_DEFAULTS.get(route_key, DEFAULT_GLOBAL_LIMIT)
    )


def update_rate_config(overrides: dict[str, str]) -> None:
    _rate_config.clear()
    _rate_config.update(overrides)


async def refresh_from_settings(settings_service: object) -> None:
    val = await settings_service.get_cached("rate_limit_overrides")  # type: ignore[attr-defined]
    if val and isinstance(val, dict):
        update_rate_config(val)
