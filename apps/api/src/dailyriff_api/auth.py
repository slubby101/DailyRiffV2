"""JWT auth middleware and CurrentUser dependency.

Stage 0 shipped HS256 with `SUPABASE_JWT_SECRET` for local Supabase CLI.
Stage 1 widens to HS256 + ES256: tokens with a `kid` header are verified
against the Supabase JWKS endpoint; tokens without `kid` fall back to the
shared secret.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import ECAlgorithm

ALGORITHMS = ["HS256", "ES256"]

PROTECTED_RESPONSES: dict[int | str, dict] = {
    400: {"description": "Bad request — invalid input"},
    401: {"description": "Not authenticated"},
    405: {"description": "Method not allowed"},
    422: {"description": "Validation error"},
}

_bearer = HTTPBearer(auto_error=False)

_JWKS_TTL_SECONDS = 300
_jwks_cache: dict | None = None
_jwks_cache_time: float = 0.0


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str | None
    role: str | None
    studio_id: UUID | None = None
    impersonation_session_id: UUID | None = None


def _jwt_secret() -> str:
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not set")
    return secret


def _supabase_url() -> str | None:
    return os.environ.get("SUPABASE_URL")


async def _fetch_jwks_raw() -> dict:
    """Fetch JWKS from Supabase's well-known endpoint."""
    base = _supabase_url()
    if not base:
        raise RuntimeError("SUPABASE_URL is not set")
    url = f"{base}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def _get_jwks() -> dict:
    """Return JWKS, using a TTL cache to avoid per-request fetches."""
    global _jwks_cache, _jwks_cache_time
    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_cache_time) < _JWKS_TTL_SECONDS:
        return _jwks_cache
    _jwks_cache = await _fetch_jwks_raw()
    _jwks_cache_time = now
    return _jwks_cache


def _find_jwk_by_kid(jwks: dict, kid: str) -> dict | None:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _decode_token(token: str) -> dict:
    """Decode a JWT using kid-based key selection: JWKS for ES256, shared secret for HS256."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    if kid:
        jwks = await _get_jwks()
        jwk = _find_jwk_by_kid(jwks, kid)
        if jwk is None:
            raise jwt.InvalidTokenError(f"No JWKS key found for kid={kid}")
        algo = ECAlgorithm(ECAlgorithm.SHA256)
        public_key = algo.from_jwk(jwk)
        return jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    else:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            audience="authenticated",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = _decode_token_sync(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid token") from exc

    sub = payload.get("sub")
    if not sub:
        raise _unauthorized("Token missing subject")

    try:
        user_id = UUID(sub)
    except (TypeError, ValueError) as exc:
        raise _unauthorized("Token subject is not a UUID") from exc

    app_metadata = payload.get("app_metadata") or {}
    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        role=app_metadata.get("role"),
    )


def _decode_token_sync(token: str) -> dict:
    """Synchronous token decode — HS256 tokens don't need async.

    For ES256 tokens (with kid), we run the async JWKS fetch in a new event loop
    since FastAPI's sync dependencies don't run in an async context.
    """
    import asyncio

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    if kid:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _decode_token(token))
                return future.result()
        else:
            return asyncio.run(_decode_token(token))
    else:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            audience="authenticated",
        )
