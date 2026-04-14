"""Alembic environment.

Important invariant (PRD §5): Alembic declares FKs into `auth.users` but
never owns the `auth` schema. `include_schemas=False` plus an
`include_object` filter that rejects anything in schema `auth` prevents
autogenerate from drifting into Supabase-owned tables.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres",
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = None


def _include_object(object_, name, type_, reflected, compare_to):
    """Reject anything in the Supabase-owned `auth` schema."""
    schema = getattr(object_, "schema", None)
    if schema == "auth":
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=False,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=False,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
