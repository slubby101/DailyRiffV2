"""NotificationService unit tests.

All external calls mocked at httpx.AsyncClient and pywebpush.webpush boundaries.
Database calls mocked via asyncpg pool patch.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from dailyriff_api.services.notifications import (
    ChannelResult,
    NotificationPayload,
    NotificationService,
)

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SUB_EXPO = {
    "id": uuid.uuid4(),
    "channel": "expo",
    "token": "ExponentPushToken[xxx]",
    "keys": None,
}
SUB_WEBPUSH = {
    "id": uuid.uuid4(),
    "channel": "webpush",
    "token": "https://push.example.com/sub/abc",
    "keys": {"p256dh": "key1", "auth": "key2"},
}
PAYLOAD = NotificationPayload(title="Test", body="Hello world")


def _make_service(http_client: httpx.AsyncClient | None = None) -> NotificationService:
    return NotificationService(
        http_client=http_client or httpx.AsyncClient(),
        supabase_url="http://localhost:54321",
        supabase_service_key="test-service-key",
        vapid_private_key="test-vapid-key",
        vapid_claims={"sub": "mailto:dev@dailyriff.local"},
    )


def _mock_pool(prefs_row=None, subs=None):
    """Return a mock asyncpg pool."""
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=prefs_row)
    pool.fetch = AsyncMock(return_value=subs or [])
    pool.execute = AsyncMock()
    return pool


@dataclass
class _FakeResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                str(self.status_code),
                request=MagicMock(),
                response=self,
            )


@pytest.mark.asyncio
async def test_send_all_channels_enabled() -> None:
    prefs_row = {
        "realtime_enabled": True,
        "expo_push_enabled": True,
        "web_push_enabled": True,
    }
    pool = _mock_pool(prefs_row=prefs_row, subs=[SUB_EXPO, SUB_WEBPUSH])
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_FakeResponse(status_code=200))

    svc = _make_service(http_client=http)

    with (
        patch("dailyriff_api.services.notifications.get_pool", return_value=pool),
        patch("dailyriff_api.services.notifications.service_transaction") as st_mock,
        patch("pywebpush.webpush") as wp_mock,
    ):
        st_conn = AsyncMock()
        st_mock.return_value.__aenter__ = AsyncMock(return_value=st_conn)
        st_mock.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await svc.send(USER_ID, PAYLOAD)

    channels = {r.channel for r in result.results}
    assert "realtime" in channels
    assert "expo" in channels
    assert "webpush" in channels
    assert all(r.success for r in result.results)


@pytest.mark.asyncio
async def test_realtime_disabled_skips_realtime() -> None:
    prefs_row = {
        "realtime_enabled": False,
        "expo_push_enabled": True,
        "web_push_enabled": True,
    }
    pool = _mock_pool(prefs_row=prefs_row, subs=[SUB_EXPO, SUB_WEBPUSH])
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_FakeResponse(status_code=200))

    svc = _make_service(http_client=http)

    with (
        patch("dailyriff_api.services.notifications.get_pool", return_value=pool),
        patch("pywebpush.webpush"),
    ):
        result = await svc.send(USER_ID, PAYLOAD)

    channels = {r.channel for r in result.results}
    assert "realtime" not in channels
    assert "expo" in channels
    assert "webpush" in channels


@pytest.mark.asyncio
async def test_expo_http_error_does_not_block_webpush() -> None:
    prefs_row = {
        "realtime_enabled": False,
        "expo_push_enabled": True,
        "web_push_enabled": True,
    }
    pool = _mock_pool(prefs_row=prefs_row, subs=[SUB_EXPO, SUB_WEBPUSH])

    async def _side_effect(url, **kwargs):
        if "exp.host" in url:
            raise httpx.HTTPStatusError(
                "500", request=MagicMock(), response=_FakeResponse(status_code=500)
            )
        return _FakeResponse(status_code=200)

    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(side_effect=_side_effect)

    svc = _make_service(http_client=http)

    with (
        patch("dailyriff_api.services.notifications.get_pool", return_value=pool),
        patch("pywebpush.webpush"),
    ):
        result = await svc.send(USER_ID, PAYLOAD)

    expo_results = [r for r in result.results if r.channel == "expo"]
    webpush_results = [r for r in result.results if r.channel == "webpush"]

    assert len(expo_results) == 1
    assert not expo_results[0].success
    assert len(webpush_results) == 1
    assert webpush_results[0].success


@pytest.mark.asyncio
async def test_webpush_410_deletes_subscription() -> None:
    from pywebpush import WebPushException

    prefs_row = {
        "realtime_enabled": False,
        "expo_push_enabled": False,
        "web_push_enabled": True,
    }
    pool = _mock_pool(prefs_row=prefs_row, subs=[SUB_WEBPUSH])
    http = AsyncMock(spec=httpx.AsyncClient)

    mock_response = MagicMock()
    mock_response.status_code = 410

    exc = WebPushException("Gone")
    exc.response = mock_response

    svc = _make_service(http_client=http)

    with (
        patch("dailyriff_api.services.notifications.get_pool", return_value=pool),
        patch("pywebpush.webpush", side_effect=exc),
    ):
        result = await svc.send(USER_ID, PAYLOAD)

    webpush_results = [r for r in result.results if r.channel == "webpush"]
    assert len(webpush_results) == 1
    assert not webpush_results[0].success
    assert "410" in (webpush_results[0].error or "")

    pool.execute.assert_called_once()
    call_args = pool.execute.call_args
    assert "DELETE" in call_args[0][0]
    assert call_args[0][1] == SUB_WEBPUSH["id"]
