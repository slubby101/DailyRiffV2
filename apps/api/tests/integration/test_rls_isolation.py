"""RLS isolation test — Q10 acceptance.

Seeds users A and B, authenticates via Supabase Auth sign_in_with_password,
queries user_push_subscriptions through PostgREST, asserts cross-user SELECT
returns 0 rows. This exercises the full stack: Auth → PostgREST → RLS.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from tests.conftest import (
    SEED_PASSWORD,
    USER_A_EMAIL,
    USER_A_ID,
    USER_B_EMAIL,
    USER_B_ID,
)


def _needs_supabase():
    return pytest.mark.skipif(
        not os.environ.get("SUPABASE_SERVICE_ROLE"),
        reason="Requires running Supabase (SUPABASE_SERVICE_ROLE not set)",
    )


def _supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "http://localhost:54321")


def _anon_key() -> str:
    return os.environ.get(
        "SUPABASE_ANON_KEY",
        os.environ.get("SUPABASE_SERVICE_ROLE", ""),
    )


def _sign_in(email: str, password: str) -> str:
    """Authenticate via Supabase Auth and return the access token."""
    url = f"{_supabase_url()}/auth/v1/token?grant_type=password"
    resp = httpx.post(
        url,
        json={"email": email, "password": password},
        headers={
            "apikey": _anon_key(),
            "Content-Type": "application/json",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _insert_subscription_service_role(user_id: uuid.UUID, token: str) -> None:
    """Insert a subscription row via PostgREST using the service role key."""
    service_role = os.environ["SUPABASE_SERVICE_ROLE"]
    resp = httpx.post(
        f"{_supabase_url()}/rest/v1/user_push_subscriptions",
        json={
            "user_id": str(user_id),
            "channel": "expo",
            "token": token,
        },
        headers={
            "apikey": service_role,
            "Authorization": f"Bearer {service_role}",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates",
        },
        timeout=10.0,
    )
    resp.raise_for_status()


def _query_subscriptions(access_token: str, target_user_id: uuid.UUID) -> list:
    """Query subscriptions through PostgREST with an authenticated user token."""
    resp = httpx.get(
        f"{_supabase_url()}/rest/v1/user_push_subscriptions",
        params={"user_id": f"eq.{target_user_id}", "select": "*"},
        headers={
            "apikey": _anon_key(),
            "Authorization": f"Bearer {access_token}",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()


@_needs_supabase()
def test_rls_prevents_reading_other_users_push_subscriptions(seeded_users) -> None:
    _insert_subscription_service_role(USER_A_ID, "ExponentPushToken[rls-a]")
    _insert_subscription_service_role(USER_B_ID, "ExponentPushToken[rls-b]")

    token_a = _sign_in(USER_A_EMAIL, SEED_PASSWORD)

    other_rows = _query_subscriptions(token_a, USER_B_ID)
    assert len(other_rows) == 0, (
        f"User A should not see user B's subscriptions, but got {len(other_rows)} rows"
    )

    own_rows = _query_subscriptions(token_a, USER_A_ID)
    assert len(own_rows) >= 1, "User A should see their own subscriptions"
