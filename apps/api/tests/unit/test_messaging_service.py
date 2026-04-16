"""Messaging service unit tests — email fallback logic."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
CONV_ID = uuid.uuid4()
MSG_ID = uuid.uuid4()


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
async def test_find_unread_messages_needing_fallback() -> None:
    from dailyriff_api.services.messaging_service import MessagingService

    svc = MessagingService()

    unread_row = {
        "message_id": MSG_ID,
        "conversation_id": CONV_ID,
        "sender_id": USER_A_ID,
        "body": "Hello",
        "created_at": NOW - timedelta(minutes=20),
        "recipient_id": USER_B_ID,
        "recipient_email": "test-b@dailyriff.local",
    }

    with patch(
        "dailyriff_api.services.messaging_service.service_transaction",
        _mock_service_tx(fetch_result=[unread_row]),
    ):
        results = await svc.find_unread_needing_fallback(delay_minutes=15)

    assert len(results) == 1
    assert results[0]["message_id"] == MSG_ID
    assert results[0]["recipient_id"] == USER_B_ID


@pytest.mark.asyncio
async def test_find_unread_returns_empty_when_all_read() -> None:
    from dailyriff_api.services.messaging_service import MessagingService

    svc = MessagingService()

    with patch(
        "dailyriff_api.services.messaging_service.service_transaction",
        _mock_service_tx(fetch_result=[]),
    ):
        results = await svc.find_unread_needing_fallback(delay_minutes=15)

    assert results == []


@pytest.mark.asyncio
async def test_record_fallback_sent() -> None:
    from dailyriff_api.services.messaging_service import MessagingService

    svc = MessagingService()

    mock_tx = _mock_service_tx()
    with patch(
        "dailyriff_api.services.messaging_service.service_transaction",
        mock_tx,
    ):
        await svc.record_fallback_sent(MSG_ID, USER_B_ID)
