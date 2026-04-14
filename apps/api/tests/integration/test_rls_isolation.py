"""RLS isolation test — Q10 acceptance.

Seeds users A and B, authenticates Supabase client as A, selects from
user_push_subscriptions filtered on B's user_id, asserts 0 rows.
This bypasses FastAPI entirely to prove RLS works at the database level.
"""

from __future__ import annotations

import json
import os
import uuid

import asyncpg
import pytest

from tests.conftest import SEED_PASSWORD, USER_A_EMAIL, USER_A_ID, USER_B_EMAIL, USER_B_ID


def _needs_supabase():
    return pytest.mark.skipif(
        not os.environ.get("SUPABASE_SERVICE_ROLE"),
        reason="Requires running Supabase (SUPABASE_SERVICE_ROLE not set)",
    )


async def _insert_subscription_as_service(conn, user_id, token):
    """Insert a subscription row using the default (superuser) role."""
    await conn.execute(
        "INSERT INTO user_push_subscriptions (user_id, channel, token) "
        "VALUES ($1, 'expo', $2) "
        "ON CONFLICT (user_id, channel, token) DO NOTHING",
        user_id,
        token,
    )


async def _count_subscriptions_as_user(conn, acting_user_id, target_user_id):
    """Query subscriptions with RLS set to acting_user_id, filtering for target."""
    await conn.execute(
        "SELECT set_config('role', 'authenticated', true)"
    )
    claims = json.dumps({"sub": str(acting_user_id)})
    await conn.execute(
        "SELECT set_config('request.jwt.claims', $1, true)", claims
    )
    row = await conn.fetchrow(
        "SELECT count(*) AS cnt FROM user_push_subscriptions WHERE user_id = $1",
        target_user_id,
    )
    return row["cnt"]


@_needs_supabase()
@pytest.mark.asyncio
async def test_rls_prevents_reading_other_users_push_subscriptions(seeded_users) -> None:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:54322/postgres",
    )
    conn = await asyncpg.connect(dsn)
    try:
        await _insert_subscription_as_service(
            conn, USER_A_ID, "ExponentPushToken[rls-a]"
        )
        await _insert_subscription_as_service(
            conn, USER_B_ID, "ExponentPushToken[rls-b]"
        )

        async with conn.transaction():
            count = await _count_subscriptions_as_user(
                conn, acting_user_id=USER_A_ID, target_user_id=USER_B_ID
            )
        assert count == 0, (
            f"User A should not see user B's subscriptions, but got {count} rows"
        )

        async with conn.transaction():
            own_count = await _count_subscriptions_as_user(
                conn, acting_user_id=USER_A_ID, target_user_id=USER_A_ID
            )
        assert own_count >= 1, "User A should see their own subscriptions"
    finally:
        await conn.close()
