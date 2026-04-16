"""Pytest configuration and shared fixtures for the DailyRiff API test suite.

Provides:
- `make_test_jwt` — callable factory for signing HS256 JWTs with the local
  `SUPABASE_JWT_SECRET`, used by auth middleware unit tests.
- `seeded_users` — session-scoped fixture that creates canonical test users A
  and B via the Supabase Admin API (with `email_confirm: true`). Only tests
  that depend on this fixture trigger the seed, so pure-unit tests do not
  require a running Supabase stack.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Callable

import httpx
import jwt
import pytest

DEFAULT_JWT_SECRET = "super-secret-jwt-token-with-at-least-32-characters-long"

USER_A_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_A_EMAIL = "test@dailyriff.local"
USER_B_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
USER_B_EMAIL = "test-b@dailyriff.local"
SEED_PASSWORD = "test-password-do-not-use-in-prod"


def _jwt_secret() -> str:
    return os.environ.get("SUPABASE_JWT_SECRET", DEFAULT_JWT_SECRET)


@pytest.fixture(autouse=True)
def _ensure_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee tests always have a JWT secret and ENVIRONMENT set."""
    if not os.environ.get("SUPABASE_JWT_SECRET"):
        monkeypatch.setenv("SUPABASE_JWT_SECRET", DEFAULT_JWT_SECRET)
    if not os.environ.get("ENVIRONMENT"):
        monkeypatch.setenv("ENVIRONMENT", "test")


@pytest.fixture
def make_test_jwt() -> Callable[..., str]:
    """Return a factory that signs a Supabase-shaped HS256 JWT."""

    def _factory(
        user_id: str | uuid.UUID = USER_A_ID,
        role: str = "user",
        email: str | None = USER_A_EMAIL,
        expires_in: int = 3600,
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "email": email,
            "aud": "authenticated",
            "role": "authenticated",
            "app_metadata": {"role": role},
            "iat": now,
            "exp": now + expires_in,
        }
        return jwt.encode(payload, _jwt_secret(), algorithm="HS256")

    return _factory


@pytest.fixture(scope="session")
def seeded_users() -> dict[str, dict]:
    """Create canonical test users A and B via the Supabase Admin API.

    Refuses to run if SUPABASE_URL is not localhost — seed passwords are only
    safe inside ephemeral local/CI Supabase instances.
    """
    supabase_url = os.environ.get("SUPABASE_URL", "http://localhost:54321")
    service_role = os.environ.get("SUPABASE_SERVICE_ROLE")

    if "localhost" not in supabase_url and "127.0.0.1" not in supabase_url:
        pytest.skip("Refusing to seed users against non-local Supabase URL")
    if not service_role:
        pytest.skip("SUPABASE_SERVICE_ROLE not set; cannot seed test users")

    users = {
        "a": {"id": str(USER_A_ID), "email": USER_A_EMAIL},
        "b": {"id": str(USER_B_ID), "email": USER_B_EMAIL},
    }

    headers = {
        "apikey": service_role,
        "Authorization": f"Bearer {service_role}",
        "Content-Type": "application/json",
    }
    admin_endpoint = f"{supabase_url}/auth/v1/admin/users"

    with httpx.Client(timeout=10.0) as client:
        for user in users.values():
            body = {
                "id": user["id"],
                "email": user["email"],
                "password": SEED_PASSWORD,
                "email_confirm": True,
            }
            resp = client.post(admin_endpoint, json=body, headers=headers)
            if resp.status_code not in (200, 201, 422):
                resp.raise_for_status()

    return users
