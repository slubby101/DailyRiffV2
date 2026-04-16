"""Messaging schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studio_id: UUID
    participant_ids: list[UUID]


class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    studio_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    user_id: UUID
    joined_at: datetime
    last_read_at: datetime | None = None


class MessageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    conversation_id: UUID
    sender_id: UUID
    body: str
    created_at: datetime
