"""Shared pagination parameters for list endpoints."""

from __future__ import annotations

from fastapi import Query

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def pagination_params(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> tuple[int, int]:
    return limit, offset
