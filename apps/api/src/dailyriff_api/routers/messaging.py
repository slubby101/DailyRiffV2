"""Conversation and message endpoints."""

from __future__ import annotations

from datetime import datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction
from dailyriff_api.schemas.messaging import (
    ConversationCreateRequest,
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
)

router = APIRouter(tags=["messaging"])

CONVERSATION_COLUMNS = "id, studio_id, created_by, created_at, updated_at"
MESSAGE_COLUMNS = "id, conversation_id, sender_id, body, created_at"


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    responses=PROTECTED_RESPONSES,
)
async def list_conversations(
    user: CurrentUser = Depends(get_current_user),
) -> list[ConversationResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {CONVERSATION_COLUMNS} FROM conversations "
            "ORDER BY updated_at DESC",
        )
    return [ConversationResponse(**dict(r)) for r in rows]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_conversation(
    body: ConversationCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ConversationResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"INSERT INTO conversations (studio_id, created_by) "
            f"VALUES ($1, $2) RETURNING {CONVERSATION_COLUMNS}",
            body.studio_id,
            user.id,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation",
            )
        conv_id = row["id"]
        all_participants = [user.id] + [
            p for p in body.participant_ids if p != user.id
        ]
        for pid in all_participants:
            await conn.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) "
                "VALUES ($1, $2)",
                conv_id,
                pid,
            )
    return ConversationResponse(**dict(row))


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Conversation not found"}},
)
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ConversationResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"SELECT {CONVERSATION_COLUMNS} FROM conversations WHERE id = $1",
            conversation_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ConversationResponse(**dict(row))


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    responses={**PROTECTED_RESPONSES, 404: {"description": "Conversation not found"}},
)
async def list_messages(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> list[MessageResponse]:
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {MESSAGE_COLUMNS} FROM messages "
            "WHERE conversation_id = $1 ORDER BY created_at ASC",
            conversation_id,
        )
    return [MessageResponse(**dict(r)) for r in rows]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Conversation not found"}},
)
async def send_message(
    conversation_id: UUID,
    body: MessageCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> MessageResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"INSERT INTO messages (conversation_id, sender_id, body) "
            f"VALUES ($1, $2, $3) RETURNING {MESSAGE_COLUMNS}",
            conversation_id,
            user.id,
            body.body,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message",
            )
        await conn.execute(
            "UPDATE conversations SET updated_at = now() WHERE id = $1",
            conversation_id,
        )
    return MessageResponse(**dict(row))


@router.post(
    "/conversations/{conversation_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=PROTECTED_RESPONSES,
)
async def mark_conversation_read(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    async with rls_transaction(user.id) as conn:
        await conn.execute(
            "UPDATE conversation_participants SET last_read_at = now() "
            "WHERE conversation_id = $1 AND user_id = $2",
            conversation_id,
            user.id,
        )
