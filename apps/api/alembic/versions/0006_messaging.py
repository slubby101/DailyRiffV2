"""Messaging: conversations, participants, messages, email fallback tracking.

Revision ID: 0006_messaging
Revises: 0005_rate_limiting
Create Date: 2026-04-16

PRD §Slice 13: in-app messaging with Supabase Realtime primary path
and 15-min email fallback for unread messages. Studio-scoped,
participant-only RLS.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_messaging"
down_revision = "0005_rate_limiting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- conversations ---------------------------------------------------------
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "studio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("conversations_studio_id_idx", "conversations", ["studio_id"])

    op.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY conversations_insert ON conversations "
        "FOR INSERT TO authenticated "
        "WITH CHECK (created_by = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid)"
    )

    # ---- conversation_participants ---------------------------------------------
    op.create_table(
        "conversation_participants",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("conversation_id", "user_id"),
    )
    op.create_index(
        "conversation_participants_user_id_idx",
        "conversation_participants",
        ["user_id"],
    )

    op.execute("ALTER TABLE conversation_participants ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY cp_select ON conversation_participants "
        "FOR SELECT TO authenticated "
        "USING (EXISTS ("
        "  SELECT 1 FROM conversation_participants cp2 "
        "  WHERE cp2.conversation_id = conversation_participants.conversation_id "
        "  AND cp2.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid"
        "))"
    )
    op.execute(
        "CREATE POLICY cp_insert ON conversation_participants "
        "FOR INSERT TO authenticated "
        "WITH CHECK (EXISTS ("
        "  SELECT 1 FROM conversations c "
        "  WHERE c.id = conversation_id "
        "  AND c.created_by = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid"
        "))"
    )
    op.execute(
        "CREATE POLICY cp_update ON conversation_participants "
        "FOR UPDATE TO authenticated "
        "USING (user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid)"
    )

    # conversations SELECT policy (deferred — needs conversation_participants to exist)
    op.execute(
        "CREATE POLICY conversations_participant_select ON conversations "
        "FOR SELECT TO authenticated "
        "USING (EXISTS ("
        "  SELECT 1 FROM conversation_participants cp "
        "  WHERE cp.conversation_id = id "
        "  AND cp.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid"
        "))"
    )

    # ---- messages --------------------------------------------------------------
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("messages_conversation_id_idx", "messages", ["conversation_id"])
    op.create_index("messages_created_at_idx", "messages", ["created_at"])

    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY messages_participant_select ON messages "
        "FOR SELECT TO authenticated "
        "USING (EXISTS ("
        "  SELECT 1 FROM conversation_participants cp "
        "  WHERE cp.conversation_id = messages.conversation_id "
        "  AND cp.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid"
        "))"
    )
    op.execute(
        "CREATE POLICY messages_participant_insert ON messages "
        "FOR INSERT TO authenticated "
        "WITH CHECK ("
        "  sender_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid "
        "  AND EXISTS ("
        "    SELECT 1 FROM conversation_participants cp "
        "    WHERE cp.conversation_id = messages.conversation_id "
        "    AND cp.user_id = (current_setting('request.jwt.claims', true)::json->>'sub')::uuid"
        "  )"
        ")"
    )

    # ---- message_email_fallbacks -----------------------------------------------
    op.create_table(
        "message_email_fallbacks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "message_id", "recipient_id", name="message_email_fallbacks_msg_recipient_uniq"
        ),
    )
    op.create_index(
        "message_email_fallbacks_message_id_idx",
        "message_email_fallbacks",
        ["message_id"],
    )

    # ---- Seed notification_delay platform_setting ------------------------------
    op.execute(
        "INSERT INTO platform_settings (key, value_json, description, category) VALUES "
        "('messaging_email_fallback_delay_minutes', "
        "'15', "
        "'Minutes before unread message triggers email fallback', "
        "'notification_delays') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM platform_settings WHERE key = 'messaging_email_fallback_delay_minutes'"
    )
    op.execute("DROP TABLE IF EXISTS message_email_fallbacks")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversation_participants")
    op.execute("DROP TABLE IF EXISTS conversations")
