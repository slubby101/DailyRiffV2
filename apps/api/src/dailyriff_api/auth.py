"""JWT auth middleware and CurrentUser dependency.

Stage 0 shipped HS256 with `SUPABASE_JWT_SECRET` for local Supabase CLI.
Stage 1 widens to HS256 + ES256: tokens with a `kid` header are verified
against the Supabase JWKS endpoint; tokens without `kid` fall back to the
shared secret.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import ECAlgorithm

logger = logging.getLogger(__name__)

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
_jwks_lock = asyncio.Lock()


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str | None
    role: str | None
    studio_id: UUID | None = None
    impersonation_session_id: UUID | None = None
    has_totp: bool = False


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
    async with _jwks_lock:
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    request: Request = None,  # type: ignore[assignment]
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = await _decode_token(credentials.credentials)
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

    # Check AMR (Authentication Methods Reference) for TOTP
    amr = payload.get("amr") or []
    has_totp = any(
        entry.get("method") == "totp" for entry in amr if isinstance(entry, dict)
    )

    role = app_metadata.get("role")

    # --- Impersonation header ---
    # When a superadmin sends X-Impersonation-Session, we validate the
    # session and return a CurrentUser representing the *target* user,
    # with impersonation_session_id set for audit purposes.
    imp_header = (
        request.headers.get("x-impersonation-session") if request else None
    )
    if imp_header:
        if role != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmins can use impersonation sessions",
            )
        try:
            session_id = UUID(imp_header)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid impersonation session ID",
            ) from exc
        # Validate session is active — import here to avoid circular deps
        from dailyriff_api.db import service_transaction
        from dailyriff_api.services import impersonation_service

        async with service_transaction() as conn:
            session = await impersonation_service.validate_session(
                conn, session_id=session_id
            )
        if session is None or session["impersonator_user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired impersonation session",
            )
        return CurrentUser(
            id=session["target_user_id"],
            email=None,  # target email not available from session
            role=role,
            impersonation_session_id=session_id,
            has_totp=has_totp,
        )

    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        role=role,
        has_totp=has_totp,
    )




# ---------------------------------------------------------------------------
# Superadmin + TOTP enforcement dependency
# ---------------------------------------------------------------------------

SUPERADMIN_RESPONSES: dict[int | str, dict] = {
    **PROTECTED_RESPONSES,
    403: {"description": "Superadmin role required"},
}


def _is_dev_or_staging() -> bool:
    env = os.environ.get("ENVIRONMENT", "").lower()
    return env in ("development", "staging", "test")


def require_superadmin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require superadmin role + TOTP when factor is enrolled.

    In dev/staging without TOTP enrolled, logs a warning but does not block.
    In production, TOTP is enforced if the user has it enrolled (checked
    via the ``amr`` JWT claim).
    """
    if user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin role required",
        )

    if not user.has_totp:
        if _is_dev_or_staging():
            logger.warning(
                "Superadmin %s accessing protected route without TOTP "
                "(allowed in dev/staging)",
                user.id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TOTP verification required for superadmin access",
            )

    return user


def require_not_impersonating(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Block scope-restricted operations during impersonation sessions.

    Use as a dependency on endpoints that must never be called while
    impersonating: password changes, account deletion, email changes,
    2FA changes, OAuth authorization, data deletion.
    """
    if user.impersonation_session_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is not permitted during an impersonation session",
        )
    return user
