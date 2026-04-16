"""Auth middleware behaviors — verified through HTTP calls against the app."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import DEFAULT_JWT_SECRET


@asynccontextmanager
async def _fake_rls_transaction(user_id):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    yield conn


@pytest.fixture(autouse=True)
def _mock_db(monkeypatch):
    """Patch rls_transaction so unit tests don't require a live database."""
    import dailyriff_api.routers.devices as dev_mod
    import dailyriff_api.routers.preferences as pref_mod

    monkeypatch.setattr(dev_mod, "rls_transaction", _fake_rls_transaction)
    monkeypatch.setattr(pref_mod, "rls_transaction", _fake_rls_transaction)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_is_public(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "git_sha" in body


def test_401_on_missing_token(client: TestClient) -> None:
    resp = client.get("/devices")
    assert resp.status_code == 401


def test_401_on_expired_token(client: TestClient) -> None:
    now = int(time.time())
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "expired@dailyriff.local",
            "aud": "authenticated",
            "app_metadata": {"role": "user"},
            "iat": now - 7200,
            "exp": now - 3600,
        },
        DEFAULT_JWT_SECRET,
        algorithm="HS256",
    )
    resp = client.get("/devices", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_401_on_malformed_token(client: TestClient) -> None:
    resp = client.get("/devices", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


def test_200_on_valid_token(
    client: TestClient, make_test_jwt: Callable[..., str]
) -> None:
    token = make_test_jwt()
    resp = client.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_current_user_has_studio_id_and_impersonation_session_id(
    make_test_jwt: Callable[..., str],
) -> None:
    """CurrentUser exposes studio_id and impersonation_session_id (both Optional)."""
    from dailyriff_api.auth import CurrentUser

    user = CurrentUser(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="test@dailyriff.local",
        role="user",
        studio_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        impersonation_session_id=uuid.UUID("00000000-0000-0000-0000-0000000000aa"),
    )
    assert user.studio_id == uuid.UUID("00000000-0000-0000-0000-000000000099")
    assert user.impersonation_session_id == uuid.UUID("00000000-0000-0000-0000-0000000000aa")


@pytest.mark.asyncio
async def test_current_user_new_fields_default_to_none(
    make_test_jwt: Callable[..., str],
) -> None:
    """CurrentUser studio_id and impersonation_session_id default to None."""
    from dailyriff_api.auth import get_current_user

    token = make_test_jwt()
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)
    user = await get_current_user(creds)
    assert user.studio_id is None
    assert user.impersonation_session_id is None


# --- ES256 / JWKS tests ---


def _make_ec_keypair():
    """Generate an EC P-256 key pair for ES256 tests."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key


def _ec_key_to_jwk(private_key, kid: str = "test-key-1") -> dict:
    """Convert an EC public key to a JWK dict."""
    from jwt.algorithms import ECAlgorithm

    algo = ECAlgorithm(ECAlgorithm.SHA256)
    jwk = json.loads(algo.to_jwk(private_key.public_key()))
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "ES256"
    return jwk


def _make_es256_jwt(
    private_key,
    kid: str = "test-key-1",
    user_id: str | None = None,
    email: str = "es256@dailyriff.local",
    role: str = "user",
    expires_in: int = 3600,
) -> str:
    """Sign a Supabase-shaped JWT with ES256."""
    now = int(time.time())
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "app_metadata": {"role": role},
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": kid},
    )


def test_200_on_valid_es256_token(client: TestClient, monkeypatch) -> None:
    """ES256 token verified against mocked JWKS is accepted."""
    import dailyriff_api.auth as auth_mod

    private_key = _make_ec_keypair()
    kid = "test-key-1"
    jwk = _ec_key_to_jwk(private_key, kid)
    jwks_response = {"keys": [jwk]}

    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")

    async def fake_fetch_jwks():
        return jwks_response

    monkeypatch.setattr(auth_mod, "_fetch_jwks_raw", fake_fetch_jwks)

    token = _make_es256_jwt(private_key, kid=kid)
    resp = client.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_jwks_cached_within_ttl(client: TestClient, monkeypatch) -> None:
    """Second ES256 request within TTL reuses cached JWKS (no re-fetch)."""
    import dailyriff_api.auth as auth_mod

    auth_mod._jwks_cache = None
    auth_mod._jwks_cache_time = 0.0

    private_key = _make_ec_keypair()
    kid = "test-key-1"
    jwk = _ec_key_to_jwk(private_key, kid)
    jwks_response = {"keys": [jwk]}

    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")

    call_count = 0

    async def counting_fetch_jwks():
        nonlocal call_count
        call_count += 1
        return jwks_response

    monkeypatch.setattr(auth_mod, "_fetch_jwks_raw", counting_fetch_jwks)

    token1 = _make_es256_jwt(private_key, kid=kid)
    resp1 = client.get("/devices", headers={"Authorization": f"Bearer {token1}"})
    assert resp1.status_code == 200

    token2 = _make_es256_jwt(private_key, kid=kid)
    resp2 = client.get("/devices", headers={"Authorization": f"Bearer {token2}"})
    assert resp2.status_code == 200

    assert call_count == 1, f"JWKS fetched {call_count} times, expected 1 (cached)"


def test_jwks_refetched_after_ttl_expires(client: TestClient, monkeypatch) -> None:
    """After TTL expires, JWKS is re-fetched."""
    import dailyriff_api.auth as auth_mod

    auth_mod._jwks_cache = None
    auth_mod._jwks_cache_time = 0.0

    private_key = _make_ec_keypair()
    kid = "test-key-1"
    jwk = _ec_key_to_jwk(private_key, kid)
    jwks_response = {"keys": [jwk]}

    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")

    call_count = 0

    async def counting_fetch_jwks():
        nonlocal call_count
        call_count += 1
        return jwks_response

    monkeypatch.setattr(auth_mod, "_fetch_jwks_raw", counting_fetch_jwks)

    token1 = _make_es256_jwt(private_key, kid=kid)
    resp1 = client.get("/devices", headers={"Authorization": f"Bearer {token1}"})
    assert resp1.status_code == 200
    assert call_count == 1

    auth_mod._jwks_cache_time = time.monotonic() - auth_mod._JWKS_TTL_SECONDS - 1

    token2 = _make_es256_jwt(private_key, kid=kid)
    resp2 = client.get("/devices", headers={"Authorization": f"Bearer {token2}"})
    assert resp2.status_code == 200
    assert call_count == 2, f"JWKS fetched {call_count} times, expected 2 (TTL expired)"


def test_401_on_es256_token_with_unknown_kid(client: TestClient, monkeypatch) -> None:
    """ES256 token with kid not in JWKS is rejected."""
    import dailyriff_api.auth as auth_mod

    auth_mod._jwks_cache = None
    auth_mod._jwks_cache_time = 0.0

    private_key = _make_ec_keypair()
    jwks_response = {"keys": []}

    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")

    async def fake_fetch_jwks():
        return jwks_response

    monkeypatch.setattr(auth_mod, "_fetch_jwks_raw", fake_fetch_jwks)

    token = _make_es256_jwt(private_key, kid="unknown-kid")
    resp = client.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_401_on_es256_token_signed_with_wrong_key(
    client: TestClient, monkeypatch
) -> None:
    """ES256 token signed with a different key than what JWKS advertises is rejected."""
    import dailyriff_api.auth as auth_mod

    auth_mod._jwks_cache = None
    auth_mod._jwks_cache_time = 0.0

    signing_key = _make_ec_keypair()
    wrong_key = _make_ec_keypair()
    kid = "test-key-1"
    jwk = _ec_key_to_jwk(wrong_key, kid)
    jwks_response = {"keys": [jwk]}

    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")

    async def fake_fetch_jwks():
        return jwks_response

    monkeypatch.setattr(auth_mod, "_fetch_jwks_raw", fake_fetch_jwks)

    token = _make_es256_jwt(signing_key, kid=kid)
    resp = client.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
