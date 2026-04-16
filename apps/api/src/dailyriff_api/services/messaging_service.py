"""Messaging service — email fallback logic for unread messages."""

from __future__ import annotations

from uuid import UUID

from dailyriff_api.db import service_transaction


class MessagingService:

    async def find_unread_needing_fallback(
        self, *, delay_minutes: int = 15
    ) -> list[dict]:
        async with service_transaction() as conn:
            rows = await conn.fetch(
                "SELECT m.id AS message_id, m.conversation_id, m.sender_id, "
                "m.body, m.created_at, cp.user_id AS recipient_id, "
                "u.email AS recipient_email "
                "FROM messages m "
                "JOIN conversation_participants cp "
                "  ON cp.conversation_id = m.conversation_id "
                "  AND cp.user_id != m.sender_id "
                "LEFT JOIN auth.users u ON u.id = cp.user_id "
                "WHERE m.created_at < now() - make_interval(mins => $1) "
                "AND (cp.last_read_at IS NULL OR cp.last_read_at < m.created_at) "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM message_email_fallbacks mef "
                "  WHERE mef.message_id = m.id AND mef.recipient_id = cp.user_id"
                ")",
                delay_minutes,
            )
        return [dict(r) for r in rows]

    async def record_fallback_sent(
        self, message_id: UUID, recipient_id: UUID
    ) -> None:
        async with service_transaction() as conn:
            await conn.execute(
                "INSERT INTO message_email_fallbacks (message_id, recipient_id) "
                "VALUES ($1, $2) ON CONFLICT DO NOTHING",
                message_id,
                recipient_id,
            )
