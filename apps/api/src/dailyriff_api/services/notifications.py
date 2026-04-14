"""Three-channel NotificationService.

Fans out to Realtime, Expo Push, and Web Push in parallel.
Preference gating: reads notification_preferences before each channel.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from uuid import UUID

import httpx

from dailyriff_api.db import get_pool, service_transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    body: str
    data: dict | None = None


@dataclass
class ChannelResult:
    channel: str
    success: bool
    error: str | None = None


@dataclass
class SendResult:
    results: list[ChannelResult] = field(default_factory=list)


@dataclass
class _Preferences:
    realtime_enabled: bool = True
    expo_push_enabled: bool = True
    web_push_enabled: bool = True


class NotificationService:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        supabase_service_key: str,
        vapid_private_key: str,
        vapid_claims: dict[str, str],
    ) -> None:
        self._http = http_client
        self._supabase_url = supabase_url.rstrip("/")
        self._service_key = supabase_service_key
        self._vapid_private_key = vapid_private_key
        self._vapid_claims = vapid_claims

    async def send(
        self, user_id: UUID, payload: NotificationPayload
    ) -> SendResult:
        prefs = await self._get_preferences(user_id)
        subs = await self._get_subscriptions(user_id)

        tasks: list[asyncio.Task[ChannelResult]] = []

        if prefs.realtime_enabled:
            tasks.append(
                asyncio.create_task(self._send_realtime(user_id, payload))
            )

        if prefs.expo_push_enabled:
            for sub in subs:
                if sub["channel"] == "expo":
                    tasks.append(
                        asyncio.create_task(self._send_expo(sub, payload))
                    )

        if prefs.web_push_enabled:
            for sub in subs:
                if sub["channel"] == "webpush":
                    tasks.append(
                        asyncio.create_task(
                            self._send_webpush(sub, payload)
                        )
                    )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        send_result = SendResult()
        for r in results:
            if isinstance(r, ChannelResult):
                send_result.results.append(r)
            elif isinstance(r, BaseException):
                send_result.results.append(
                    ChannelResult(channel="unknown", success=False, error=str(r))
                )
        return send_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_preferences(self, user_id: UUID) -> _Preferences:
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT realtime_enabled, expo_push_enabled, web_push_enabled "
            "FROM notification_preferences WHERE user_id = $1",
            user_id,
        )
        if row is None:
            return _Preferences()
        return _Preferences(
            realtime_enabled=row["realtime_enabled"],
            expo_push_enabled=row["expo_push_enabled"],
            web_push_enabled=row["web_push_enabled"],
        )

    async def _get_subscriptions(self, user_id: UUID) -> list[dict]:
        pool = get_pool()
        rows = await pool.fetch(
            "SELECT id, channel, token, keys FROM user_push_subscriptions "
            "WHERE user_id = $1",
            user_id,
        )
        return [dict(r) for r in rows]

    async def _send_realtime(
        self, user_id: UUID, payload: NotificationPayload
    ) -> ChannelResult:
        broadcast_url = (
            f"{self._supabase_url}/realtime/v1/api/broadcast"
        )
        body = {
            "messages": [
                {
                    "topic": f"user:{user_id}",
                    "event": "notification",
                    "payload": {
                        "title": payload.title,
                        "body": payload.body,
                        "data": payload.data,
                    },
                }
            ]
        }
        try:
            resp = await self._http.post(
                broadcast_url,
                json=body,
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
                },
            )
            if resp.status_code < 300:
                return ChannelResult(channel="realtime", success=True)
        except httpx.HTTPError:
            pass

        await self._insert_outbox(user_id, payload)
        return ChannelResult(
            channel="realtime",
            success=True,
            error="fell back to outbox",
        )

    async def _insert_outbox(
        self, user_id: UUID, payload: NotificationPayload
    ) -> None:
        async with service_transaction() as conn:
            await conn.execute(
                "INSERT INTO realtime_outbox (user_id, payload) VALUES ($1, $2)",
                user_id,
                json.dumps(
                    {
                        "title": payload.title,
                        "body": payload.body,
                        "data": payload.data,
                    }
                ),
            )

    async def _send_expo(
        self, sub: dict, payload: NotificationPayload
    ) -> ChannelResult:
        try:
            resp = await self._http.post(
                "https://exp.host/--/api/v2/push/send",
                json={
                    "to": sub["token"],
                    "title": payload.title,
                    "body": payload.body,
                    "data": payload.data or {},
                },
            )
            resp.raise_for_status()
            return ChannelResult(channel="expo", success=True)
        except Exception as exc:
            logger.warning("Expo push failed: %s", exc)
            return ChannelResult(
                channel="expo", success=False, error=str(exc)
            )

    async def _send_webpush(
        self, sub: dict, payload: NotificationPayload
    ) -> ChannelResult:
        from pywebpush import WebPushException, webpush

        subscription_info = {
            "endpoint": sub["token"],
            "keys": sub["keys"] or {},
        }
        data = json.dumps(
            {
                "title": payload.title,
                "body": payload.body,
                "data": payload.data,
            }
        )
        try:
            webpush(
                subscription_info=subscription_info,
                data=data,
                vapid_private_key=self._vapid_private_key,
                vapid_claims=self._vapid_claims,
            )
            return ChannelResult(channel="webpush", success=True)
        except WebPushException as exc:
            if getattr(exc, "response", None) is not None and exc.response.status_code == 410:
                await self._delete_subscription(sub["id"])
                return ChannelResult(
                    channel="webpush",
                    success=False,
                    error="410 gone — subscription deleted",
                )
            logger.warning("Web push failed: %s", exc)
            return ChannelResult(
                channel="webpush", success=False, error=str(exc)
            )

    async def _delete_subscription(self, subscription_id: UUID) -> None:
        pool = get_pool()
        await pool.execute(
            "DELETE FROM user_push_subscriptions WHERE id = $1",
            subscription_id,
        )
