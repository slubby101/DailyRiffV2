"""Database pool and connection helpers.

Provides an asyncpg pool with two connection modes:
- `rls_transaction(user_id)`: sets role=authenticated + JWT claims so RLS applies.
- `service_transaction()`: uses the default postgres superuser (bypasses RLS).
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

import asyncpg


_pool: asyncpg.Pool | None = None


def _dsn() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:54322/postgres",
    )


async def _register_jsonb_codec(conn: asyncpg.Connection) -> None:
    """Teach asyncpg to serialize Python dicts/lists <-> jsonb.

    Without this, passing a dict to a jsonb parameter raises
    `DataError: expected str, got dict` because asyncpg's default jsonb
    codec expects the caller to pre-serialize to JSON.
    """
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        _dsn(),
        min_size=2,
        max_size=10,
        init=_register_jsonb_codec,
    )


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "Database pool not initialised — call init_pool() first"
    return _pool


@asynccontextmanager
async def rls_transaction(user_id: UUID) -> AsyncIterator[asyncpg.Connection]:
    """Connection scoped to *authenticated* role with JWT claims set."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            claims = json.dumps({"sub": str(user_id)})
            await conn.execute(
                "SELECT set_config('role', 'authenticated', true)"
            )
            await conn.execute(
                "SELECT set_config('request.jwt.claims', $1, true)",
                claims,
            )
            yield conn


@asynccontextmanager
async def service_transaction() -> AsyncIterator[asyncpg.Connection]:
    """Connection using the default (superuser) role — bypasses RLS."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
