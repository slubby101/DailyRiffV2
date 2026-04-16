"""Seed the database with Polymet's Mitchell Music Studio mock data.

Verbatim port of the Polymet demo state: one studio, one teacher/owner,
five students across age classes, parent relationships, assignments with
real music pieces, recordings, lessons, conversations, messages, payments,
and resources.

All IDs are deterministic UUIDs so the script is fully idempotent — safe to
re-run without duplicating data (ON CONFLICT DO NOTHING everywhere).

Usage:
  uv run python -m dailyriff_api.scripts.seed_polymet
  uv run python -m dailyriff_api.scripts.seed_polymet --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID


import asyncpg


# ---------------------------------------------------------------------------
# Deterministic UUIDs — stable across re-runs for idempotency
# ---------------------------------------------------------------------------

# Studio
STUDIO_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")

# Users (auth.users) — Ellen is the teacher/owner
ELLEN_ID = UUID("bbbbbbbb-0000-0000-0000-000000000001")   # owner/teacher
SARAH_ID = UUID("bbbbbbbb-0000-0000-0000-000000000002")   # student (16, teen)
MARCUS_ID = UUID("bbbbbbbb-0000-0000-0000-000000000003")  # student (10, minor)
LILY_ID = UUID("bbbbbbbb-0000-0000-0000-000000000004")    # student (14, teen)
JAKE_ID = UUID("bbbbbbbb-0000-0000-0000-000000000005")    # student (18, adult)
EMMA_ID = UUID("bbbbbbbb-0000-0000-0000-000000000006")    # student (8, minor)

# Parents
AMY_ID = UUID("bbbbbbbb-0000-0000-0000-000000000011")     # Sarah's mom
DAVID_ID = UUID("bbbbbbbb-0000-0000-0000-000000000012")   # Marcus's dad
WEI_ID = UUID("bbbbbbbb-0000-0000-0000-000000000013")     # Lily's parent
JENNIFER_ID = UUID("bbbbbbbb-0000-0000-0000-000000000014")  # Emma's mom

# Assignments
ASSIGN_SARAH_1 = UUID("cccccccc-0000-0000-0000-000000000001")
ASSIGN_SARAH_2 = UUID("cccccccc-0000-0000-0000-000000000002")
ASSIGN_MARCUS_1 = UUID("cccccccc-0000-0000-0000-000000000003")
ASSIGN_LILY_1 = UUID("cccccccc-0000-0000-0000-000000000004")
ASSIGN_JAKE_1 = UUID("cccccccc-0000-0000-0000-000000000005")
ASSIGN_EMMA_1 = UUID("cccccccc-0000-0000-0000-000000000006")

# Recordings
REC_SARAH_1 = UUID("dddddddd-0000-0000-0000-000000000001")
REC_SARAH_2 = UUID("dddddddd-0000-0000-0000-000000000002")
REC_MARCUS_1 = UUID("dddddddd-0000-0000-0000-000000000003")
REC_JAKE_1 = UUID("dddddddd-0000-0000-0000-000000000004")

# Lessons
LESSON_SARAH = UUID("eeeeeeee-0000-0000-0000-000000000001")
LESSON_MARCUS = UUID("eeeeeeee-0000-0000-0000-000000000002")
LESSON_LILY = UUID("eeeeeeee-0000-0000-0000-000000000003")
LESSON_JAKE = UUID("eeeeeeee-0000-0000-0000-000000000004")
LESSON_EMMA = UUID("eeeeeeee-0000-0000-0000-000000000005")

# Conversations
CONV_ELLEN_AMY = UUID("ffffffff-0000-0000-0000-000000000001")
CONV_ELLEN_DAVID = UUID("ffffffff-0000-0000-0000-000000000002")
CONV_ELLEN_WEI = UUID("ffffffff-0000-0000-0000-000000000003")

# Messages
MSG_1 = UUID("11111111-0000-0000-0000-000000000001")
MSG_2 = UUID("11111111-0000-0000-0000-000000000002")
MSG_3 = UUID("11111111-0000-0000-0000-000000000003")
MSG_4 = UUID("11111111-0000-0000-0000-000000000004")
MSG_5 = UUID("11111111-0000-0000-0000-000000000005")
MSG_6 = UUID("11111111-0000-0000-0000-000000000006")

# Payments
PAY_1 = UUID("22222222-0000-0000-0000-000000000001")
PAY_2 = UUID("22222222-0000-0000-0000-000000000002")
PAY_3 = UUID("22222222-0000-0000-0000-000000000003")
PAY_4 = UUID("22222222-0000-0000-0000-000000000004")

# Resources
RES_1 = UUID("33333333-0000-0000-0000-000000000001")
RES_2 = UUID("33333333-0000-0000-0000-000000000002")
RES_3 = UUID("33333333-0000-0000-0000-000000000003")

# Parents table IDs
PARENT_AMY = UUID("44444444-0000-0000-0000-000000000001")
PARENT_DAVID = UUID("44444444-0000-0000-0000-000000000002")
PARENT_WEI = UUID("44444444-0000-0000-0000-000000000003")
PARENT_JENNIFER = UUID("44444444-0000-0000-0000-000000000004")

# Parent-children links
PC_AMY_SARAH = UUID("55555555-0000-0000-0000-000000000001")
PC_DAVID_MARCUS = UUID("55555555-0000-0000-0000-000000000002")
PC_WEI_LILY = UUID("55555555-0000-0000-0000-000000000003")
PC_JENNIFER_EMMA = UUID("55555555-0000-0000-0000-000000000004")

# Loans
LOAN_1 = UUID("66666666-0000-0000-0000-000000000001")

# Studio members IDs
SM_ELLEN = UUID("77777777-0000-0000-0000-000000000001")
SM_SARAH = UUID("77777777-0000-0000-0000-000000000002")
SM_MARCUS = UUID("77777777-0000-0000-0000-000000000003")
SM_LILY = UUID("77777777-0000-0000-0000-000000000004")
SM_JAKE = UUID("77777777-0000-0000-0000-000000000005")
SM_EMMA = UUID("77777777-0000-0000-0000-000000000006")
SM_AMY = UUID("77777777-0000-0000-0000-000000000011")
SM_DAVID = UUID("77777777-0000-0000-0000-000000000012")
SM_WEI = UUID("77777777-0000-0000-0000-000000000013")
SM_JENNIFER = UUID("77777777-0000-0000-0000-000000000014")

# Acknowledgements
ACK_SARAH_1 = UUID("88888888-0000-0000-0000-000000000001")
ACK_SARAH_2 = UUID("88888888-0000-0000-0000-000000000002")
ACK_MARCUS_1 = UUID("88888888-0000-0000-0000-000000000003")
ACK_JAKE_1 = UUID("88888888-0000-0000-0000-000000000005")

SEED_PASSWORD = "polymet-seed-do-not-use-in-prod"


def _dsn() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:54322/postgres",
    )


def _supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "http://localhost:54321")


def _supabase_service_role() -> str:
    return os.environ.get("SUPABASE_SERVICE_ROLE", "")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def _days_from_now(n: int) -> datetime:
    return _now() + timedelta(days=n)


async def _create_auth_users() -> None:
    """Create auth.users via Supabase Admin API (idempotent: 422 = already exists)."""
    import httpx

    url = _supabase_url()
    service_role = _supabase_service_role()

    if not service_role:
        print("  SKIP auth.users creation: SUPABASE_SERVICE_ROLE not set")
        print("  (users must already exist in auth.users for FK constraints)")
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
        (ELLEN_ID, "ellen.mitchell@dailyriff.local", "Ellen Mitchell"),
        (SARAH_ID, "sarah.chen@dailyriff.local", "Sarah Chen"),
        (MARCUS_ID, "marcus.johnson@dailyriff.local", "Marcus Johnson"),
        (LILY_ID, "lily.wang@dailyriff.local", "Lily Wang"),
        (JAKE_ID, "jake.thompson@dailyriff.local", "Jake Thompson"),
        (EMMA_ID, "emma.davis@dailyriff.local", "Emma Davis"),
        (AMY_ID, "amy.chen@dailyriff.local", "Amy Chen"),
        (DAVID_ID, "david.johnson@dailyriff.local", "David Johnson"),
        (WEI_ID, "wei.wang@dailyriff.local", "Wei Wang"),
        (JENNIFER_ID, "jennifer.davis@dailyriff.local", "Jennifer Davis"),
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
                print(f"  Created auth user: {name} ({email})")
            elif resp.status_code == 422:
                print(f"  Exists: {name} ({email})")
            else:
                print(f"  WARN: {name} -> HTTP {resp.status_code}: {resp.text}")


async def _seed_database(conn: asyncpg.Connection) -> None:
    """Insert all Polymet mock data via ON CONFLICT DO NOTHING for idempotency."""

    now = _now()

    # -- Studio ---------------------------------------------------------------
    print("  Seeding studio...")
    await conn.execute("""
        INSERT INTO studios (id, name, display_name, primary_color, timezone,
                             beta_cohort, state, auto_approve_parents)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (id) DO NOTHING
    """, STUDIO_ID, "mitchell-music-studio", "Mitchell Music Studio",
        "#D97706", "America/New_York", True, "active", False)

    # -- Studio members -------------------------------------------------------
    print("  Seeding studio members...")
    members = [
        (SM_ELLEN, STUDIO_ID, ELLEN_ID, "owner", None),
        (SM_SARAH, STUDIO_ID, SARAH_ID, "student", "teen"),
        (SM_MARCUS, STUDIO_ID, MARCUS_ID, "student", "minor"),
        (SM_LILY, STUDIO_ID, LILY_ID, "student", "teen"),
        (SM_JAKE, STUDIO_ID, JAKE_ID, "student", "adult"),
        (SM_EMMA, STUDIO_ID, EMMA_ID, "student", "minor"),
        (SM_AMY, STUDIO_ID, AMY_ID, "parent", None),
        (SM_DAVID, STUDIO_ID, DAVID_ID, "parent", None),
        (SM_WEI, STUDIO_ID, WEI_ID, "parent", None),
        (SM_JENNIFER, STUDIO_ID, JENNIFER_ID, "parent", None),
    ]
    for mid, sid, uid, role, age_class in members:
        await conn.execute("""
            INSERT INTO studio_members (id, studio_id, user_id, role, age_class)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, mid, sid, uid, role, age_class)

    # -- Parents + parent_children --------------------------------------------
    print("  Seeding parents and parent-children relationships...")
    parents = [
        (PARENT_AMY, AMY_ID, STUDIO_ID),
        (PARENT_DAVID, DAVID_ID, STUDIO_ID),
        (PARENT_WEI, WEI_ID, STUDIO_ID),
        (PARENT_JENNIFER, JENNIFER_ID, STUDIO_ID),
    ]
    for pid, uid, sid in parents:
        await conn.execute("""
            INSERT INTO parents (id, user_id, studio_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING
        """, pid, uid, sid)

    parent_children = [
        (PC_AMY_SARAH, PARENT_AMY, SARAH_ID, True, True, True, True),
        (PC_DAVID_MARCUS, PARENT_DAVID, MARCUS_ID, True, True, True, True),
        (PC_WEI_LILY, PARENT_WEI, LILY_ID, True, True, True, True),
        (PC_JENNIFER_EMMA, PARENT_JENNIFER, EMMA_ID, True, True, True, True),
    ]
    for pcid, pid, child_id, primary, pay, progress, comm in parent_children:
        await conn.execute("""
            INSERT INTO parent_children
                (id, parent_id, child_user_id, is_primary_contact,
                 can_manage_payments, can_view_progress, can_communicate_with_teacher)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO NOTHING
        """, pcid, pid, child_id, primary, pay, progress, comm)

    # -- Assignments ----------------------------------------------------------
    print("  Seeding assignments...")
    assignments = [
        (ASSIGN_SARAH_1, STUDIO_ID, ELLEN_ID, SARAH_ID,
         "Practice Clair de Lune — mm. 1-16",
         "Focus on the triplet arpeggios in the right hand. Use metronome starting at 60 BPM.",
         json.dumps(["Clair de Lune"]), json.dumps(["legato", "arpeggios", "dynamics"]),
         _days_ago(7), "completed", "Beautiful phrasing on the opening! Watch the pedaling in m. 12.", 4),
        (ASSIGN_SARAH_2, STUDIO_ID, ELLEN_ID, SARAH_ID,
         "Bach Invention No. 13 — hands separate",
         "Learn the right hand part measures 1-8. Pay attention to the articulation markings.",
         json.dumps(["Bach Invention No. 13"]), json.dumps(["counterpoint", "articulation"]),
         _days_from_now(5), "active", None, None),
        (ASSIGN_MARCUS_1, STUDIO_ID, ELLEN_ID, MARCUS_ID,
         "Practice scales — C Major and G Major",
         "Two octaves, hands together. Quarter notes at 80 BPM, then eighth notes at 60 BPM.",
         json.dumps(["C Major Scale", "G Major Scale"]), json.dumps(["scales", "rhythm"]),
         _days_from_now(3), "active", None, None),
        (ASSIGN_LILY_1, STUDIO_ID, ELLEN_ID, LILY_ID,
         "Für Elise — Section A memorization",
         "Memorize the first 24 measures. Practice without looking at the score.",
         json.dumps(["Für Elise"]), json.dumps(["memorization", "expression"]),
         _days_from_now(7), "active", None, None),
        (ASSIGN_JAKE_1, STUDIO_ID, ELLEN_ID, JAKE_ID,
         "Chopin Nocturne Op. 9 No. 2 — expression and rubato",
         "Work on the ornamental passages in mm. 9-16. Listen to the Rubinstein recording for reference.",
         json.dumps(["Chopin Nocturne Op. 9 No. 2"]), json.dumps(["rubato", "ornamentation", "phrasing"]),
         _days_from_now(10), "active", None, None),
        (ASSIGN_EMMA_1, STUDIO_ID, ELLEN_ID, EMMA_ID,
         "Twinkle Twinkle Little Star — both hands",
         "Play the melody with the right hand and whole notes with the left. Steady tempo!",
         json.dumps(["Twinkle Twinkle Little Star"]), json.dumps(["hand coordination", "tempo"]),
         _days_from_now(4), "active", None, None),
    ]
    for (aid, sid, tid, stid, title, desc, pieces, techniques,
         due, status, feedback, rating) in assignments:
        await conn.execute("""
            INSERT INTO assignments
                (id, studio_id, teacher_id, student_id, title, description,
                 pieces, techniques, due_date, status, feedback_text, feedback_rating)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (id) DO NOTHING
        """, aid, sid, tid, stid, title, desc,
            json.loads(pieces), json.loads(techniques),
            due, status, feedback, rating)

    # -- Recordings -----------------------------------------------------------
    print("  Seeding recordings...")
    recordings = [
        (REC_SARAH_1, STUDIO_ID, SARAH_ID, ASSIGN_SARAH_1,
         f"recordings/{STUDIO_ID}/{SARAH_ID}/{REC_SARAH_1}.webm",
         "audio/webm", 1200, 2_400_000, _days_ago(5)),
        (REC_SARAH_2, STUDIO_ID, SARAH_ID, ASSIGN_SARAH_1,
         f"recordings/{STUDIO_ID}/{SARAH_ID}/{REC_SARAH_2}.webm",
         "audio/webm", 900, 1_800_000, _days_ago(3)),
        (REC_MARCUS_1, STUDIO_ID, MARCUS_ID, ASSIGN_MARCUS_1,
         f"recordings/{STUDIO_ID}/{MARCUS_ID}/{REC_MARCUS_1}.webm",
         "audio/webm", 600, 1_200_000, _days_ago(1)),
        (REC_JAKE_1, STUDIO_ID, JAKE_ID, ASSIGN_JAKE_1,
         f"recordings/{STUDIO_ID}/{JAKE_ID}/{REC_JAKE_1}.webm",
         "audio/webm", 1800, 3_600_000, _days_ago(2)),
    ]
    for rid, sid, stid, aid, key, mime, dur, size, uploaded in recordings:
        await conn.execute("""
            INSERT INTO recordings
                (id, studio_id, student_id, assignment_id, r2_object_key,
                 mime_type, duration_seconds, file_size_bytes, uploaded_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO NOTHING
        """, rid, sid, stid, aid, key, mime, dur, size, uploaded)

    # -- Assignment acknowledgements ------------------------------------------
    print("  Seeding acknowledgements...")
    acks = [
        (ACK_SARAH_1, ASSIGN_SARAH_1, REC_SARAH_1, "acknowledged", _days_ago(5)),
        (ACK_SARAH_2, ASSIGN_SARAH_1, REC_SARAH_2, "acknowledged", _days_ago(3)),
        (ACK_MARCUS_1, ASSIGN_MARCUS_1, REC_MARCUS_1, "acknowledged", _days_ago(1)),
        (ACK_JAKE_1, ASSIGN_JAKE_1, REC_JAKE_1, "acknowledged", _days_ago(2)),
    ]
    for aid, assign_id, rec_id, status, ack_at in acks:
        await conn.execute("""
            INSERT INTO assignment_acknowledgements
                (id, assignment_id, recording_id, status, acknowledged_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, aid, assign_id, rec_id, status, ack_at)

    # -- Lessons (recurring weekly) -------------------------------------------
    print("  Seeding lessons...")
    lessons = [
        (LESSON_SARAH, STUDIO_ID, ELLEN_ID, SARAH_ID,
         "Piano — Sarah Chen", "Weekly piano lesson",
         time(15, 30), 45, date.today() - timedelta(days=60), None,
         True, "weekly", 2, 50.00, False, False),  # Tuesday 3:30pm
        (LESSON_MARCUS, STUDIO_ID, ELLEN_ID, MARCUS_ID,
         "Piano — Marcus Johnson", "Weekly piano lesson (beginner)",
         time(16, 0), 30, date.today() - timedelta(days=45), None,
         True, "weekly", 3, 40.00, False, False),  # Wednesday 4:00pm
        (LESSON_LILY, STUDIO_ID, ELLEN_ID, LILY_ID,
         "Piano — Lily Wang", "Weekly piano lesson",
         time(15, 0), 45, date.today() - timedelta(days=30), None,
         True, "weekly", 4, 50.00, False, False),  # Thursday 3:00pm
        (LESSON_JAKE, STUDIO_ID, ELLEN_ID, JAKE_ID,
         "Piano — Jake Thompson", "Weekly piano lesson (advanced)",
         time(17, 0), 60, date.today() - timedelta(days=90), None,
         True, "weekly", 1, 65.00, False, False),  # Monday 5:00pm
        (LESSON_EMMA, STUDIO_ID, ELLEN_ID, EMMA_ID,
         "Piano — Emma Davis", "Weekly piano lesson (young beginner)",
         time(10, 0), 30, date.today() - timedelta(days=20), None,
         True, "weekly", 6, 35.00, False, True),  # Saturday 10:00am (trial)
    ]
    for (lid, sid, tid, stid, title, desc, st, dur, sd, ed,
         recurring, cadence, dow, cost, paid, trial) in lessons:
        await conn.execute("""
            INSERT INTO lessons
                (id, studio_id, teacher_id, student_id, title, description,
                 start_time, duration_minutes, start_date, end_date,
                 is_recurring, cadence, day_of_week, cost, is_paid, is_trial,
                 created_by)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$3)
            ON CONFLICT (id) DO NOTHING
        """, lid, sid, tid, stid, title, desc, st, dur, sd, ed,
            recurring, cadence, dow, cost, paid, trial)

    # -- Conversations + messages ---------------------------------------------
    print("  Seeding conversations and messages...")
    convos = [
        (CONV_ELLEN_AMY, STUDIO_ID, ELLEN_ID),
        (CONV_ELLEN_DAVID, STUDIO_ID, ELLEN_ID),
        (CONV_ELLEN_WEI, STUDIO_ID, ELLEN_ID),
    ]
    for cid, sid, created_by in convos:
        await conn.execute("""
            INSERT INTO conversations (id, studio_id, created_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING
        """, cid, sid, created_by)

    participants = [
        (CONV_ELLEN_AMY, ELLEN_ID), (CONV_ELLEN_AMY, AMY_ID),
        (CONV_ELLEN_DAVID, ELLEN_ID), (CONV_ELLEN_DAVID, DAVID_ID),
        (CONV_ELLEN_WEI, ELLEN_ID), (CONV_ELLEN_WEI, WEI_ID),
    ]
    for cid, uid in participants:
        await conn.execute("""
            INSERT INTO conversation_participants (conversation_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT (conversation_id, user_id) DO NOTHING
        """, cid, uid)

    messages = [
        (MSG_1, CONV_ELLEN_AMY, ELLEN_ID,
         "Hi Amy! Sarah did a wonderful job on Clair de Lune this week. "
         "Her phrasing is really coming along.", _days_ago(5)),
        (MSG_2, CONV_ELLEN_AMY, AMY_ID,
         "Thank you, Ellen! She's been practicing every day. She really loves that piece.",
         _days_ago(5) + timedelta(hours=2)),
        (MSG_3, CONV_ELLEN_AMY, ELLEN_ID,
         "That dedication shows! I've assigned Bach Invention No. 13 for next week — "
         "it'll challenge her counterpoint skills.",
         _days_ago(4)),
        (MSG_4, CONV_ELLEN_DAVID, ELLEN_ID,
         "Hi David! Marcus is making great progress with his scales. "
         "He's ready to start simple pieces next month.",
         _days_ago(3)),
        (MSG_5, CONV_ELLEN_DAVID, DAVID_ID,
         "That's great to hear! He talks about piano all the time now.",
         _days_ago(3) + timedelta(hours=1)),
        (MSG_6, CONV_ELLEN_WEI, ELLEN_ID,
         "Hi Wei! Just wanted to let you know Lily's memorization of Für Elise is "
         "coming along nicely. She has a real ear for Beethoven.",
         _days_ago(2)),
    ]
    for mid, cid, sender, body, created in messages:
        await conn.execute("""
            INSERT INTO messages (id, conversation_id, sender_id, body, created_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
        """, mid, cid, sender, body, created)

    # -- Payments (manual ledger) ---------------------------------------------
    print("  Seeding payments...")
    payments = [
        (PAY_1, STUDIO_ID, SARAH_ID, 200.00, "USD", AMY_ID,
         "paid", "check", "January tuition — 4 lessons", ELLEN_ID, _days_ago(30)),
        (PAY_2, STUDIO_ID, SARAH_ID, 200.00, "USD", AMY_ID,
         "paid", "venmo", "February tuition — 4 lessons", ELLEN_ID, _days_ago(15)),
        (PAY_3, STUDIO_ID, MARCUS_ID, 160.00, "USD", DAVID_ID,
         "paid", "cash", "January tuition — 4 lessons", ELLEN_ID, _days_ago(28)),
        (PAY_4, STUDIO_ID, JAKE_ID, 260.00, "USD", JAKE_ID,
         "pending", "venmo", "February tuition — 4 lessons", ELLEN_ID, _days_ago(5)),
    ]
    for (pid, sid, stid, amount, currency, payer,
         status, method, memo, created_by, created) in payments:
        await conn.execute("""
            INSERT INTO payments
                (id, studio_id, student_user_id, amount, currency, payer_user_id,
                 status, method, memo, created_by, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            ON CONFLICT (id) DO NOTHING
        """, pid, sid, stid, amount, currency, payer,
            status, method, memo, created_by, created)

    # -- Resources ------------------------------------------------------------
    print("  Seeding resources...")
    resources = [
        (RES_1, STUDIO_ID, "IMSLP — Free Sheet Music",
         "https://imslp.org/", "International Music Score Library Project — "
         "free public domain sheet music downloads.",
         "sheet-music", ELLEN_ID),
        (RES_2, STUDIO_ID, "Metronome Online",
         "https://www.metronomeonline.com/",
         "Free online metronome for practice sessions.",
         "tools", ELLEN_ID),
        (RES_3, STUDIO_ID, "Music Theory Fundamentals",
         "https://www.musictheory.net/",
         "Interactive music theory lessons and exercises.",
         "theory", ELLEN_ID),
    ]
    for rid, sid, title, url, desc, cat, created_by in resources:
        await conn.execute("""
            INSERT INTO resources
                (id, studio_id, title, url, description, category, created_by)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (id) DO NOTHING
        """, rid, sid, title, url, desc, cat, created_by)

    # -- Loans ----------------------------------------------------------------
    print("  Seeding loans...")
    await conn.execute("""
        INSERT INTO loans
            (id, studio_id, student_user_id, item_name, description,
             loaned_at, returned_at, created_by)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (id) DO NOTHING
    """, LOAN_1, STUDIO_ID, MARCUS_ID,
        "Yamaha P-45 Digital Piano",
        "Loaner instrument for home practice until family purchases their own.",
        _days_ago(30), None, ELLEN_ID)

    print("  Polymet seed complete!")


async def _run(*, dry_run: bool = False) -> None:
    # Safety: refuse to run against non-local databases
    dsn = _dsn()
    if "localhost" not in dsn and "127.0.0.1" not in dsn:
        print("ABORT: refusing to seed a non-local database")
        sys.exit(1)

    print("=== Polymet Seed: Mitchell Music Studio ===")
    print(f"  DSN: {dsn}")

    if dry_run:
        print("  DRY RUN — no changes will be made")
        return

    # Step 1: Create auth.users via Supabase Admin API
    print("\n[1/2] Creating auth.users...")
    await _create_auth_users()

    # Step 2: Seed all app tables via direct SQL
    print("\n[2/2] Seeding application tables...")
    conn = await asyncpg.connect(dsn)
    try:
        await _seed_database(conn)
    finally:
        await conn.close()

    print("\n=== Done! ===")
    print(f"  Studio: Mitchell Music Studio ({STUDIO_ID})")
    print(f"  Teacher: Ellen Mitchell ({ELLEN_ID})")
    print(f"  Students: Sarah, Marcus, Lily, Jake, Emma")
    print(f"  Parents: Amy, David, Wei, Jennifer")
    print(f"  Password for all users: {SEED_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Mitchell Music Studio (Polymet mock data)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()
    asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
