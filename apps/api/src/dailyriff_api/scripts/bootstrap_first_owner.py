"""Bootstrap the first DailyRiff employee (owner).

One-shot script that creates the initial owner row in dailyriff_employees.
Sanity checks:
  1. No employees exist yet (employees count must be 0)
  2. The target auth.users row exists
  3. In production, the target user has TOTP enrolled via GoTrue

Usage:
  uv run python -m dailyriff_api.scripts.bootstrap_first_owner <user_id>
  uv run python -m dailyriff_api.scripts.bootstrap_first_owner <user_id> --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from uuid import UUID

import asyncpg


def _dsn() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:54322/postgres",
    )


async def _run(user_id: UUID, *, dry_run: bool = False) -> None:
    conn = await asyncpg.connect(_dsn())
    try:
        async with conn.transaction():
            # Advisory lock prevents concurrent bootstrap runs
            await conn.execute("SELECT pg_advisory_xact_lock(42)")
            # Check 1: no employees exist
            count = await conn.fetchval("SELECT COUNT(*) FROM dailyriff_employees")
        if count > 0:
            print(f"ABORT: {count} employee(s) already exist. This script is one-shot only.")
            sys.exit(1)

        # Check 2: auth.users row exists
        user_row = await conn.fetchrow(
            "SELECT id, email FROM auth.users WHERE id = $1",
            user_id,
        )
        if user_row is None:
            print(f"ABORT: No auth.users row found for {user_id}")
            sys.exit(1)

        email = user_row["email"]
        print(f"Found user: {email} ({user_id})")

        # Check 3: in production, verify TOTP enrollment
        env = os.environ.get("ENVIRONMENT", "development").lower()
        if env == "production":
            factor_count = await conn.fetchval(
                "SELECT COUNT(*) FROM auth.mfa_factors "
                "WHERE user_id = $1 AND factor_type = 'totp' AND status = 'verified'",
                user_id,
            )
            if factor_count == 0:
                print(
                    "ABORT: User does not have TOTP enrolled. "
                    "Enroll via GoTrue native flow before bootstrapping."
                )
                sys.exit(1)
            print(f"TOTP verified: {factor_count} factor(s) enrolled")
        else:
            print(f"Skipping TOTP check (environment={env})")

        if dry_run:
            print("DRY RUN — would insert owner row. No changes made.")
            return

        await conn.execute(
            "INSERT INTO dailyriff_employees (user_id, role, notes) "
            "VALUES ($1, 'owner', 'Bootstrap owner — first employee')",
            user_id,
        )
        print(f"SUCCESS: {email} is now a DailyRiff owner.")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first DailyRiff employee (owner)."
    )
    parser.add_argument("user_id", type=str, help="UUID of the auth.users row")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate checks without inserting",
    )
    args = parser.parse_args()

    try:
        uid = UUID(args.user_id)
    except ValueError:
        print(f"ERROR: '{args.user_id}' is not a valid UUID")
        sys.exit(1)

    asyncio.run(_run(uid, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
