"""Recording playback authorization — default-deny allow-list policy.

Single policy function `can_play_recording` centralizes all playback access
decisions. Allow-list: student themselves, parents/guardians (with
can_view_progress), assigned teachers, studio owner. Superadmin only via
active impersonation session.
"""

from __future__ import annotations

from typing import Any

import asyncpg

from dailyriff_api.auth import CurrentUser


async def can_play_recording(
    conn: asyncpg.Connection,
    user: CurrentUser,
    recording: dict[str, Any],
) -> bool:
    """Return True if *user* is allowed to play *recording*, False otherwise.

    Default-deny: every path must be explicitly allowed.
    """
    student_id = recording["student_id"]
    studio_id = recording["studio_id"]

    # 1. Superadmin with active impersonation session — short-circuit
    if (
        user.role == "superadmin"
        and user.impersonation_session_id is not None
    ):
        return True

    # 2. Student who recorded it (includes grace-period — deleted_at doesn't block)
    if user.id == student_id:
        return True

    # 3. Parent/guardian with can_view_progress permission
    parent_child = await conn.fetchrow(
        "SELECT pc.can_view_progress "
        "FROM parent_children pc "
        "JOIN parents p ON p.id = pc.parent_id "
        "WHERE p.user_id = $1 AND pc.child_user_id = $2",
        user.id,
        student_id,
    )
    if parent_child and parent_child["can_view_progress"]:
        return True

    # 4. Teacher who has an assignment with this student in this studio
    assignment = await conn.fetchrow(
        "SELECT id FROM assignments "
        "WHERE teacher_id = $1 AND student_id = $2 AND studio_id = $3 "
        "LIMIT 1",
        user.id,
        student_id,
        studio_id,
    )
    if assignment is not None:
        return True

    # 5. Studio owner
    membership = await conn.fetchrow(
        "SELECT role FROM studio_members "
        "WHERE user_id = $1 AND studio_id = $2",
        user.id,
        studio_id,
    )
    if membership and membership["role"] == "owner":
        return True

    # Default deny
    return False
