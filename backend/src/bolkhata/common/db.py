"""
Database engine and session factory.

Design
------
* A single AsyncEngine is created from DATABASE_URL.
* async_sessionmaker provides type-safe async sessions throughout the app.
* The engine is attached to app.state at startup and disposed at shutdown
  via FastAPI's lifespan context manager (not deprecated on_event hooks).
* SQLite databases are automatically configured with Write-Ahead Logging (WAL)
  mode and synchronous=NORMAL via connect event listeners for safe concurrent reads.
* Alembic runs migrations independently via alembic/env.py using asyncio.run()
  — it does NOT go through this module at migration time.

Connectivity test
-----------------
check_database_connectivity() opens a raw async connection and executes
SELECT 1. It is used by GET /ready. It raises the underlying SQLAlchemy
exception on failure — the caller decides how to respond (HTTP 503).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bolkhata.common.logging import get_logger
from bolkhata.config.settings import settings

logger = get_logger(__name__)


def build_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create and return an AsyncEngine for *database_url*.

    Defaults to settings.database_url when no URL is supplied.
    When SQLite is used, WAL mode is activated via a connect listener.
    """
    url = database_url or settings.database_url
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_async_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,  # detect stale connections before checkout
        echo=settings.app_env == "development",
    )

    if url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    logger.info("database_engine_created", url_scheme=url.split(":")[0])
    return engine


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to *engine*."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_database_connectivity(engine: AsyncEngine) -> None:
    """
    Verify that the database is reachable by executing SELECT 1.

    Raises
    ------
    sqlalchemy.exc.SQLAlchemyError
        Any connectivity or driver error propagated as-is so callers can
        distinguish DB errors from application bugs.
    """
    conn: AsyncConnection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
