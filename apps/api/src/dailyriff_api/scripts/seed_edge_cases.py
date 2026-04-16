"""Seed synthetic edge-case data on top of the Polymet baseline.

Generates states that a single happy-path music studio wouldn't naturally
exercise but that DailyRiff must handle:

- Pending-deletion child (COPPA 15-day grace)
- Mid-conversion teen (about to age out of MINOR→TEEN)
- Divorced-family multi-parent student (two parents, split permissions)
- Recording-upload-failed state (uploaded_at is NULL)

All IDs are deterministic UUIDs — fully idempotent (ON CONFLICT DO NOTHING).
Requires the Polymet seed to have run first (uses Mitchell Music Studio).

Usage:
  uv run python -m dailyriff_api.scripts.seed_edge_cases
  uv run python -m dailyriff_api.scripts.seed_edge_cases --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import secrets
import sys
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

import asyncpg

# Import studio ID from polymet seed
from dailyriff_api.scripts.seed_polymet import (
    ELLEN_ID,
    SEED_PASSWORD,
    STUDIO_ID,
    _dsn,
    _supabase_service_role,
    _supabase_url,
)


# ---------------------------------------------------------------------------
# Deterministic UUIDs for edge-case entities
# ---------------------------------------------------------------------------

# Edge-case users
PENDING_DELETE_PARENT_ID = UUID("99aaaaaa-0000-0000-0000-000000000001")
PENDING_DELETE_CHILD_ID = UUID("99aaaaaa-0000-0000-0000-000000000002")
MID_CONVERSION_STUDENT_ID = UUID("99aaaaaa-0000-0000-0000-000000000003")
MID_CONVERSION_PARENT_ID = UUID("99aaaaaa-0000-0000-0000-000000000004")
DIVORCED_CHILD_ID = UUID("99aaaaaa-0000-0000-0000-000000000005")
DIVORCED_PARENT_A_ID = UUID("99aaaaaa-0000-0000-0000-000000000006")
DIVORCED_PARENT_B_ID = UUID("99aaaaaa-0000-0000-0000-000000000007")
FAILED_UPLOAD_STUDENT_ID = UUID("99aaaaaa-0000-0000-0000-000000000008")

# Studio members
SM_PDC_PARENT = UUID("99bbbbbb-0000-0000-0000-000000000001")
SM_PDC_CHILD = UUID("99bbbbbb-0000-0000-0000-000000000002")
SM_MID_STUDENT = UUID("99bbbbbb-0000-0000-0000-000000000003")
SM_MID_PARENT = UUID("99bbbbbb-0000-0000-0000-000000000004")
SM_DIV_CHILD = UUID("99bbbbbb-0000-0000-0000-000000000005")
SM_DIV_PARENT_A = UUID("99bbbbbb-0000-0000-0000-000000000006")
SM_DIV_PARENT_B = UUID("99bbbbbb-0000-0000-0000-000000000007")
SM_FAIL_STUDENT = UUID("99bbbbbb-0000-0000-0000-000000000008")

# Parents table
PARENT_PDC = UUID("99cccccc-0000-0000-0000-000000000001")
PARENT_MID = UUID("99cccccc-0000-0000-0000-000000000002")
PARENT_DIV_A = UUID("99cccccc-0000-0000-0000-000000000003")
PARENT_DIV_B = UUID("99cccccc-0000-0000-0000-000000000004")

# Parent-children links
PC_PDC = UUID("99dddddd-0000-0000-0000-000000000001")
PC_MID = UUID("99dddddd-0000-0000-0000-000000000002")
PC_DIV_A = UUID("99dddddd-0000-0000-0000-000000000003")
PC_DIV_B = UUID("99dddddd-0000-0000-0000-000000000004")

# COPPA entities
COPPA_CONSENT_ID = UUID("99eeeeee-0000-0000-0000-000000000001")
COPPA_DELETION_ID = UUID("99eeeeee-0000-0000-0000-000000000002")

# Assignments + recordings for edge cases
ASSIGN_MID = UUID("99ffffff-0000-0000-0000-000000000001")
ASSIGN_FAIL = UUID("99ffffff-0000-0000-0000-000000000002")
REC_FAIL = UUID("99ffffff-0000-0000-0000-000000000003")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def _days_from_now(n: int) -> datetime:
    return _now() + timedelta(days=n)


async def _create_auth_users() -> None:
    """Create edge-case auth.users via Supabase Admin API."""
    import httpx

    url = _supabase_url()
    service_role = _supabase_service_role()

    if not service_role:
        print("  SKIP auth.users creation: SUPABASE_SERVICE_ROLE not set")
        return

    if "localhost" not in url and "127.0.0.1" not in url:
        print("  ABORT: refusing to seed auth.users on non-local Supabase")
        sys.exit(1)

    headers = {
        "apikey": service_role,
        "Authorization": f"Bearer {service_role}",
        "Content-Type": "application/json",
    }
    admin_endpoint = f"{url}/auth/v1/admin/users"

    users = [
        (PENDING_DELETE_PARENT_ID, "pdc.parent@dailyriff.local", "PDC Parent"),
        (PENDING_DELETE_CHILD_ID, "pdc.child@dailyriff.local", "PDC Child"),
        (MID_CONVERSION_STUDENT_ID, "mid.conv@dailyriff.local", "Alex Rivera"),
        (MID_CONVERSION_PARENT_ID, "mid.conv.parent@dailyriff.local", "Maria Rivera"),
        (DIVORCED_CHILD_ID, "div.child@dailyriff.local", "Taylor Brooks"),
        (DIVORCED_PARENT_A_ID, "div.parent.a@dailyriff.local", "Karen Brooks"),
        (DIVORCED_PARENT_B_ID, "div.parent.b@dailyriff.local", "Mike Brooks"),
        (FAILED_UPLOAD_STUDENT_ID, "fail.upload@dailyriff.local", "Noah Park"),
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for uid, email, name in users:
            body = {
                "id": str(uid),
                "email": email,
                "password": SEED_PASSWORD,
                "email_confirm": True,
                "user_metadata": {"full_name": name},
            }
            resp = await client.post(admin_endpoint, json=body, headers=headers)
            if resp.status_code in (200, 201):
                print(f"  Created: {name} ({email})")
            elif resp.status_code == 422:
                print(f"  Exists: {name} ({email})")
            else:
                print(f"  WARN: {name} -> HTTP {resp.status_code}: {resp.text}")


async def _seed_edge_cases(conn: asyncpg.Connection) -> None:
    """Insert edge-case data via ON CONFLICT DO NOTHING."""

    now = _now()

    # =========================================================================
    # EDGE CASE 1: Pending-deletion child (COPPA 15-day grace)
    # Parent initiated deletion 10 days ago — T-5 days until hard-delete.
    # =========================================================================
    print("  [Edge Case 1] Pending-deletion child (COPPA grace)...")

    for mid, uid, role, age_class in [
        (SM_PDC_PARENT, PENDING_DELETE_PARENT_ID, "parent", None),
        (SM_PDC_CHILD, PENDING_DELETE_CHILD_ID, "student", "minor"),
    ]:
        await conn.execute("""
            INSERT INTO studio_members (id, studio_id, user_id, role, age_class)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, mid, STUDIO_ID, uid, role, age_class)

    await conn.execute("""
        INSERT INTO parents (id, user_id, studio_id)
        VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING
    """, PARENT_PDC, PENDING_DELETE_PARENT_ID, STUDIO_ID)

    await conn.execute("""
        INSERT INTO parent_children
            (id, parent_id, child_user_id, is_primary_contact,
             can_manage_payments, can_view_progress, can_communicate_with_teacher)
        VALUES ($1, $2, $3, true, true, true, true)
        ON CONFLICT (id) DO NOTHING
    """, PC_PDC, PARENT_PDC, PENDING_DELETE_CHILD_ID)

    # COPPA consent (verified, then deletion scheduled)
    await conn.execute("""
        INSERT INTO coppa_consents
            (id, parent_id, child_id, studio_id, status, verified_at)
        VALUES ($1, $2, $3, $4, 'verified', $5)
        ON CONFLICT (id) DO NOTHING
    """, COPPA_CONSENT_ID, PARENT_PDC, PENDING_DELETE_CHILD_ID, STUDIO_ID,
        _days_ago(60))

    # Deletion request — scheduled 10 days ago, deletes in 5 days
    token = "edge-case-deletion-token-placeholder"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await conn.execute("""
        INSERT INTO coppa_deletion_requests
            (id, parent_id, child_id, studio_id, status,
             confirmation_token_hash, email_confirmed_at,
             scheduled_delete_at, t7_reminder_sent_at)
        VALUES ($1, $2, $3, $4, 'scheduled', $5, $6, $7, $8)
        ON CONFLICT (id) DO NOTHING
    """, COPPA_DELETION_ID, PARENT_PDC, PENDING_DELETE_CHILD_ID,
        STUDIO_ID, token_hash, _days_ago(10), _days_from_now(5),
        _days_ago(2))

    # =========================================================================
    # EDGE CASE 2: Mid-conversion teen (MINOR turning 13 → TEEN)
    # Student is currently classified as MINOR but should be reconsidered.
    # =========================================================================
    print("  [Edge Case 2] Mid-conversion teen (MINOR→TEEN)...")

    for mid, uid, role, age_class in [
        (SM_MID_STUDENT, MID_CONVERSION_STUDENT_ID, "student", "minor"),
        (SM_MID_PARENT, MID_CONVERSION_PARENT_ID, "parent", None),
    ]:
        await conn.execute("""
            INSERT INTO studio_members (id, studio_id, user_id, role, age_class)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, mid, STUDIO_ID, uid, role, age_class)

    await conn.execute("""
        INSERT INTO parents (id, user_id, studio_id)
        VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING
    """, PARENT_MID, MID_CONVERSION_PARENT_ID, STUDIO_ID)

    await conn.execute("""
        INSERT INTO parent_children
            (id, parent_id, child_user_id, is_primary_contact,
             can_manage_payments, can_view_progress, can_communicate_with_teacher)
        VALUES ($1, $2, $3, true, true, true, true)
        ON CONFLICT (id) DO NOTHING
    """, PC_MID, PARENT_MID, MID_CONVERSION_STUDENT_ID)

    # Give this student an active assignment for testing conversion with active data
    await conn.execute("""
        INSERT INTO assignments
            (id, studio_id, teacher_id, student_id, title, description,
             pieces, techniques, due_date, status)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (id) DO NOTHING
    """, ASSIGN_MID, STUDIO_ID, ELLEN_ID, MID_CONVERSION_STUDENT_ID,
        "Practice Minuet in G", "Work on the left hand accompaniment pattern.",
        ["Minuet in G"], ["hand independence"],
        _days_from_now(7), "active")

    # =========================================================================
    # EDGE CASE 3: Divorced-family multi-parent student
    # Two parents with different permission sets for the same child.
    # =========================================================================
    print("  [Edge Case 3] Divorced-family multi-parent student...")

    for mid, uid, role, age_class in [
        (SM_DIV_CHILD, DIVORCED_CHILD_ID, "student", "minor"),
        (SM_DIV_PARENT_A, DIVORCED_PARENT_A_ID, "parent", None),
        (SM_DIV_PARENT_B, DIVORCED_PARENT_B_ID, "parent", None),
    ]:
        await conn.execute("""
            INSERT INTO studio_members (id, studio_id, user_id, role, age_class)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, mid, STUDIO_ID, uid, role, age_class)

    for pid, uid in [
        (PARENT_DIV_A, DIVORCED_PARENT_A_ID),
        (PARENT_DIV_B, DIVORCED_PARENT_B_ID),
    ]:
        await conn.execute("""
            INSERT INTO parents (id, user_id, studio_id)
            VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING
        """, pid, uid, STUDIO_ID)

    # Parent A: primary contact, full permissions (custodial parent)
    await conn.execute("""
        INSERT INTO parent_children
            (id, parent_id, child_user_id, is_primary_contact,
             can_manage_payments, can_view_progress, can_communicate_with_teacher)
        VALUES ($1, $2, $3, true, true, true, true)
        ON CONFLICT (id) DO NOTHING
    """, PC_DIV_A, PARENT_DIV_A, DIVORCED_CHILD_ID)

    # Parent B: non-primary, can view progress but NOT manage payments or message teacher
    await conn.execute("""
        INSERT INTO parent_children
            (id, parent_id, child_user_id, is_primary_contact,
             can_manage_payments, can_view_progress, can_communicate_with_teacher)
        VALUES ($1, $2, $3, false, false, true, false)
        ON CONFLICT (id) DO NOTHING
    """, PC_DIV_B, PARENT_DIV_B, DIVORCED_CHILD_ID)

    # =========================================================================
    # EDGE CASE 4: Recording-upload-failed state
    # Student has a recording row but uploaded_at is NULL (upload interrupted).
    # =========================================================================
    print("  [Edge Case 4] Recording-upload-failed state...")

    await conn.execute("""
        INSERT INTO studio_members (id, studio_id, user_id, role, age_class)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO NOTHING
    """, SM_FAIL_STUDENT, STUDIO_ID, FAILED_UPLOAD_STUDENT_ID, "student", "teen")

    await conn.execute("""
        INSERT INTO assignments
            (id, studio_id, teacher_id, student_id, title, description,
             pieces, techniques, due_date, status)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (id) DO NOTHING
    """, ASSIGN_FAIL, STUDIO_ID, ELLEN_ID, FAILED_UPLOAD_STUDENT_ID,
        "Practice Sonatina in C", "Focus on the exposition section.",
        ["Sonatina in C"], ["sonata form"],
        _days_from_now(5), "active")

    # Recording with uploaded_at = NULL (upload was interrupted)
    await conn.execute("""
        INSERT INTO recordings
            (id, studio_id, student_id, assignment_id, r2_object_key,
             mime_type, duration_seconds, file_size_bytes, uploaded_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8, NULL)
        ON CONFLICT (id) DO NOTHING
    """, REC_FAIL, STUDIO_ID, FAILED_UPLOAD_STUDENT_ID, ASSIGN_FAIL,
        f"recordings/{STUDIO_ID}/{FAILED_UPLOAD_STUDENT_ID}/{REC_FAIL}.webm",
        "audio/webm", 600, 1_200_000)

    print("  Edge-case seed complete!")


async def _run(*, dry_run: bool = False) -> None:
    dsn = _dsn()
    if "localhost" not in dsn and "127.0.0.1" not in dsn:
        print("ABORT: refusing to seed a non-local database")
        sys.exit(1)

    print("=== Edge-Case Seed (layered on Polymet) ===")
    print(f"  DSN: {dsn}")

    if dry_run:
        print("  DRY RUN — no changes will be made")
        return

    print("\n[1/2] Creating auth.users...")
    await _create_auth_users()

    print("\n[2/2] Seeding edge-case data...")
    conn = await asyncpg.connect(dsn)
    try:
        await _seed_edge_cases(conn)
    finally:
        await conn.close()

    print("\n=== Done! ===")
    print("  Edge cases seeded:")
    print(f"  - Pending-deletion child (COPPA T-5 days)")
    print(f"  - Mid-conversion minor (MINOR→TEEN candidate: Alex Rivera)")
    print(f"  - Divorced family (Taylor Brooks: Karen + Mike Brooks)")
    print(f"  - Failed upload (Noah Park: recording with NULL uploaded_at)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed synthetic edge-case data on top of Polymet baseline"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()
    asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
