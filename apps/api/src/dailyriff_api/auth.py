"""JWT auth middleware and CurrentUser dependency.

Stage 0 uses HS256 with `SUPABASE_JWT_SECRET` — matching Supabase local CLI.
Stage 0b will widen the algorithm list to `["HS256", "ES256"]` when moving to
cloud Supabase (asymmetric keys).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ALGORITHMS = ["HS256"]

# Shared openapi `responses` entry for every protected route. Declaring these
# status codes in the spec lets Schemathesis accept 400/401/422 bodies as
# conformant — without it, any non-2xx response is flagged as a schema
# conformance failure on random-input fuzzing.
PROTECTED_RESPONSES: dict[int | str, dict] = {
    400: {"description": "Bad request — invalid input"},
    401: {"description": "Not authenticated"},
    405: {"description": "Method not allowed"},
    422: {"description": "Validation error"},
}

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str | None
    role: str | None


def _jwt_secret() -> str:
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not set")
    return secret


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = jwt.decode(
            credentials.credentials,
            _jwt_secret(),
            algorithms=ALGORITHMS,
            audience="authenticated",
        )
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
