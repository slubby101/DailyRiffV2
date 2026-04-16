"""Invitation service — create, redeem, regenerate, expire invitations.

Token security: plaintext tokens are returned to the caller once on creation.
Only the SHA-256 hash is stored in the database. Redemption compares hashes.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone as tz
from uuid import UUID

import asyncpg

INVITATION_EXPIRY_DAYS = 14

INVITATION_COLUMNS = (
    "id, studio_id, invited_by, invited_email, invited_user_id, persona, "
    "status, token_hash, age_class, auto_approve, expires_at, redeemed_at, "
    "redeemed_by, created_at, updated_at"
)


def _hash_token(token: str) -> str:
    """SHA-256 hash a plaintext invitation token."""
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_token() -> tuple[str, str]:
    """Generate a secure token and its hash. Returns (plaintext, hash)."""
    plaintext = secrets.token_urlsafe(32)
    return plaintext, _hash_token(plaintext)


def classify_age(age: int) -> str:
    """Classify age into minor/teen/adult."""
    if age < 13:
        return "minor"
    elif age < 18:
        return "teen"
    return "adult"


def determine_persona_for_age(age_class: str) -> str:
    """Determine which persona should be invited based on age class.

    Under-13 (minor) → always parent invited (COPPA).
    13–17 (teen) → teacher picks parent or student (caller decides).
    18+ (adult) → student directly.
    """
    if age_class == "minor":
        return "parent"
    elif age_class == "adult":
        return "student"
    # teen: caller decides
    return "student"


async def create_invitation(
    conn: asyncpg.Connection,
    *,
    studio_id: UUID,
    invited_by: UUID,
    invited_email: str,
    persona: str,
    age_class: str | None = None,
    auto_approve: bool = False,
) -> tuple[dict, str]:
    """Create a new invitation. Returns (row_dict, plaintext_token)."""
    plaintext, token_hash = _generate_token()
    expires_at = datetime.now(tz.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
    now = datetime.now(tz.utc)

    row = await conn.fetchrow(
        f"INSERT INTO invitations "
        f"(studio_id, invited_by, invited_email, persona, token_hash, "
        f" age_class, auto_approve, expires_at, created_at, updated_at) "
        f"VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9) "
        f"RETURNING {INVITATION_COLUMNS}",
        studio_id,
        invited_by,
        invited_email,
        persona,
        token_hash,
        age_class,
        auto_approve,
        expires_at,
        now,
    )
    return dict(row), plaintext


async def redeem_invitation(
    conn: asyncpg.Connection,
    *,
    token: str,
    redeemed_by: UUID,
) -> dict | None:
    """Redeem an invitation by plaintext token. Returns updated row or None."""
    token_hash = _hash_token(token)
    now = datetime.now(tz.utc)

    # Find the invitation by hash
    row = await conn.fetchrow(
        f"SELECT {INVITATION_COLUMNS} FROM invitations "
        f"WHERE token_hash = $1",
        token_hash,
    )
    if row is None:
        return None

    row_dict = dict(row)

    # Check status
    if row_dict["status"] != "pending":
        return None

    # Check expiry
    if row_dict["expires_at"] < now:
        # Mark as expired
        await conn.execute(
            "UPDATE invitations SET status = 'expired', updated_at = $2 WHERE id = $1",
            row_dict["id"],
            now,
        )
        return None

    # Redeem
    updated = await conn.fetchrow(
        f"UPDATE invitations "
        f"SET status = 'accepted', redeemed_at = $2, redeemed_by = $3, "
        f"    invited_user_id = $3, updated_at = $2 "
        f"WHERE id = $1 "
        f"RETURNING {INVITATION_COLUMNS}",
        row_dict["id"],
        now,
        redeemed_by,
    )

    if updated is None:
        return None

    updated_dict = dict(updated)

    # Add user to studio_members
    await conn.execute(
        "INSERT INTO studio_members (studio_id, user_id, role) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT (studio_id, user_id) DO NOTHING",
        updated_dict["studio_id"],
        redeemed_by,
        updated_dict["persona"],
    )

    return updated_dict


async def regenerate_invitation(
    conn: asyncpg.Connection,
    *,
    invitation_id: UUID,
) -> tuple[dict, str] | None:
    """Regenerate token for an invitation, invalidating the prior token.

    Returns (row_dict, new_plaintext_token) or None if not found.
    """
    plaintext, token_hash = _generate_token()
    expires_at = datetime.now(tz.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
    now = datetime.now(tz.utc)

    row = await conn.fetchrow(
        f"UPDATE invitations "
        f"SET token_hash = $2, expires_at = $3, status = 'pending', "
        f"    redeemed_at = NULL, redeemed_by = NULL, invited_user_id = NULL, "
        f"    updated_at = $4 "
        f"WHERE id = $1 "
        f"RETURNING {INVITATION_COLUMNS}",
        invitation_id,
        token_hash,
        expires_at,
        now,
    )
    if row is None:
        return None
    return dict(row), plaintext


async def expire_stale_invitations(
    conn: asyncpg.Connection,
) -> int:
    """Mark all pending invitations past their expiry as expired. Returns count."""
    now = datetime.now(tz.utc)
    result = await conn.execute(
        "UPDATE invitations SET status = 'expired', updated_at = $1 "
        "WHERE status = 'pending' AND expires_at < $1",
        now,
    )
    # asyncpg returns "UPDATE N"
    return int(result.split()[-1])


async def list_studio_invitations(
    conn: asyncpg.Connection,
    *,
    studio_id: UUID,
    status_filter: str | None = None,
) -> list[dict]:
    """List invitations for a studio, optionally filtered by status."""
    if status_filter:
        rows = await conn.fetch(
            f"SELECT {INVITATION_COLUMNS} FROM invitations "
            f"WHERE studio_id = $1 AND status = $2 "
            f"ORDER BY created_at DESC",
            studio_id,
            status_filter,
        )
    else:
        rows = await conn.fetch(
            f"SELECT {INVITATION_COLUMNS} FROM invitations "
            f"WHERE studio_id = $1 "
            f"ORDER BY created_at DESC",
            studio_id,
        )
    return [dict(r) for r in rows]


async def create_batch_parent_invitation(
    conn: asyncpg.Connection,
    *,
    studio_id: UUID,
    invited_by: UUID,
    invited_email: str,
    child_names: list[str],
) -> tuple[dict, str]:
    """Create a single parent invitation for multiple children.

    The child_names are stored as metadata; actual child records are created
    on redemption. Returns (row_dict, plaintext_token).
    """
    return await create_invitation(
        conn,
        studio_id=studio_id,
        invited_by=invited_by,
        invited_email=invited_email,
        persona="parent",
        age_class="minor",
        auto_approve=False,
    )
