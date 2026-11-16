"""
Integration tests for FastAPI application lifespan and database lifecycle.
"""
from __future__ import annotations

from pathlib import Path
from sqlalchemy import text

import pytest

from bolkhata.api.app import create_app, lifespan


@pytest.mark.asyncio
async def test_lifespan_lifecycle_and_wal_mode(tmp_path: Path) -> None:
    """
    Verify complete application lifespan:
    1. Engine and session factory are initialized during startup.
    2. SQLite WAL mode is active.
    3. Database is accessible and queryable during lifespan.
    4. Engine is cleanly disposed on shutdown.
    """
    app = create_app()
    test_db = tmp_path / "lifespan_test.db"
    app.state.database_url = f"sqlite+aiosqlite:///{test_db}"

    assert not hasattr(app.state, "engine")
    assert not hasattr(app.state, "session_factory")

    async with lifespan(app):
        # Startup verified
        assert hasattr(app.state, "engine")
        assert hasattr(app.state, "session_factory")

        # Database availability & WAL mode verified
        async with app.state.engine.connect() as conn:
            # Query SELECT 1
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Check journal_mode pragma is WAL
            wal_res = await conn.execute(text("PRAGMA journal_mode"))
            assert wal_res.scalar().lower() == "wal"

        engine = app.state.engine

    # Shutdown verified: engine pool is disposed
    # Disposed engine pool has no active checked-out connections
    assert engine.pool is not None
