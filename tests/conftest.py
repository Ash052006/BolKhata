"""
Shared pytest fixtures.

Fixtures use the actual FastAPI lifespan context manager so that engine creation,
session factory initialization, and engine disposal on shutdown are exercised
natively during tests without mocks or test-only workarounds.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from bolkhata.api.app import create_app, lifespan


@pytest_asyncio.fixture()
async def client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client operating within the real FastAPI application lifespan.
    Uses an isolated temporary SQLite database path that is cleanly deleted after test.
    """
    application = create_app()
    test_db = tmp_path / "test_bolkhata.db"
    application.state.database_url = f"sqlite+aiosqlite:///{test_db}"

    async with lifespan(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as ac:
            yield ac


@pytest_asyncio.fixture()
async def broken_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client operating within the real FastAPI application lifespan,
    configured with a genuinely unreachable SQLite database path (parent directory
    does not exist). No mocks involved — exercises genuine async DB connectivity error.
    """
    application = create_app()
    application.state.database_url = "sqlite+aiosqlite:////nonexistent/bolkhata_broken/db.sqlite"

    async with lifespan(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as ac:
            yield ac
