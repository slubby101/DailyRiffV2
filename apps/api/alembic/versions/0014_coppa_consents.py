"""COPPA verifiable parental consent table.

Revision ID: 0014_coppa_consents
Revises: 0013_impersonation_playback_log
Create Date: 2026-04-16

PRD §Slice 10a: COPPA VPC — Stripe Setup Intent flow, signed-form escape
hatch, revocation with 30-day auto-delete. Status enum tracks consent
lifecycle: pending → verified → (revoked|expired).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_coppa_consents"
down_revision = "0013_impersonation_playback_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- coppa_consent_status enum ----------------------------------------
    consent_status = postgresql.ENUM(
        "pending", "verified", "revoked", "expired",
        name="coppa_consent_status",
        create_type=False,
    )
    op.execute(
        "CREATE TYPE coppa_consent_status AS ENUM "
        "('pending', 'verified', 'revoked', 'expired')"
    )

    # ---- coppa_consents table ---------------------------------------------
    op.create_table(
        "coppa_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Stripe Setup Intent for micro-charge VPC
        sa.Column("stripe_setup_intent_id", sa.Text(), nullable=True),
        # Signed-form escape hatch URL
        sa.Column("form_url", sa.Text(), nullable=True),
        sa.Column(
            "status",
            consent_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "verified_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        # 30 days after revocation, auto-delete triggers
        sa.Column(
            "revocation_auto_delete_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
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
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["parents.id"],
            ondelete="CASCADE",
            name="coppa_consents_parent_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["studio_id"],
            ["studios.id"],
            ondelete="CASCADE",
            name="coppa_consents_studio_id_fkey",
        ),
    )

    # Indices
    op.create_index(
        "coppa_consents_parent_id_idx", "coppa_consents", ["parent_id"]
    )
    op.create_index(
        "coppa_consents_child_id_idx", "coppa_consents", ["child_id"]
    )
    op.create_index(
        "coppa_consents_studio_id_idx", "coppa_consents", ["studio_id"]
    )
    op.create_index(
        "coppa_consents_status_idx", "coppa_consents", ["status"]
    )
    op.create_index(
        "coppa_consents_stripe_si_idx",
        "coppa_consents",
        ["stripe_setup_intent_id"],
        unique=True,
        postgresql_where=sa.text("stripe_setup_intent_id IS NOT NULL"),
    )

    # ---- RLS ---------------------------------------------------------------
    op.execute("ALTER TABLE coppa_consents ENABLE ROW LEVEL SECURITY")

    # Parents can read their own consents
    op.execute(
        "CREATE POLICY coppa_consents_parent_select ON coppa_consents "
        "FOR SELECT TO authenticated "
        "USING (parent_id IN ("
        "  SELECT id FROM parents WHERE user_id = "
        "  (current_setting('request.jwt.claims', true)::jsonb ->> 'sub')::uuid"
        "))"
    )

    # Superadmin (service role) can do anything — handled by service_transaction
    # bypassing RLS entirely.

    # ---- Seed COPPA grace window platform_settings -------------------------
    op.execute(
        "INSERT INTO platform_settings (key, value_json, description, category) VALUES "
        "('coppa_revocation_auto_delete_days', "
        "'30', "
        "'Days after COPPA consent revocation before auto-deleting child data', "
        "'coppa_grace_windows'), "
        "('coppa_consent_expiry_days', "
        "'365', "
        "'Days before a COPPA consent expires and needs renewal', "
        "'coppa_grace_windows') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS coppa_consents")
    op.execute("DROP TYPE IF EXISTS coppa_consent_status")
    op.execute(
        "DELETE FROM platform_settings WHERE key IN ("
        "'coppa_revocation_auto_delete_days', "
        "'coppa_consent_expiry_days'"
        ")"
    )
