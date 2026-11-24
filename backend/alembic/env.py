"""
Alembic async migration environment.

Alembic runs migrations independently of FastAPI startup.
This file uses asyncio.run() to drive async SQLAlchemy operations so a
single async engine is used throughout — no dual-engine complexity.

The DATABASE_URL is read from the environment (or .env file) via Pydantic
Settings, so migrations pick up the same configuration as the application.

Usage (run from backend/):
    uv run alembic upgrade head
    uv run alembic revision --autogenerate -m "describe change"
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini.
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override sqlalchemy.url with the value from Pydantic Settings so the
# application and Alembic always use the same database.
# ---------------------------------------------------------------------------
from bolkhata.config.settings import Settings  # noqa: E402

_settings = Settings()
config.set_main_option("sqlalchemy.url", _settings.database_url)

# ---------------------------------------------------------------------------
# Metadata for autogenerate support.
# Import your SQLAlchemy Base here when models are added.
# ---------------------------------------------------------------------------
import bolkhata.domains  # noqa: E402, F401
from bolkhata.common.base import Base  # noqa: E402

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within a connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using asyncio."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
