"""Retention cleanup for unboundedly-growing log tables.

Wraps the SQL functions created in migration 0015_log_retention_cleanup
so they can be invoked from Python (e.g., a scheduled FastAPI task or
manual admin action) and tested without pg_cron.
"""
from __future__ import annotations

from dailyriff_api.db import service_transaction


async def cleanup_mfa_failure_log() -> int:
    """Delete mfa_failure_log rows older than 30 days. Returns count deleted."""
    async with service_transaction() as conn:
        result = await conn.fetchval("SELECT public.cleanup_mfa_failure_log()")
        return result or 0


async def cleanup_idempotency_log() -> int:
    """Delete idempotency_log rows older than 90 days. Returns count deleted."""
    async with service_transaction() as conn:
        result = await conn.fetchval("SELECT public.cleanup_idempotency_log()")
        return result or 0
