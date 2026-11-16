"""
Integration tests for GET /ready.

Happy path: SQLite database at a valid path → 200 {"status": "ready"}.
Broken path: SQLite path with non-existent parent directory → 503.

The broken-path test does NOT use mocks.  It wires the app to a genuinely
unreachable database URL so that the full async driver error path fires.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ready_returns_200_with_valid_db(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ready_body_with_valid_db(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_ready_returns_503_when_db_unreachable(broken_client: AsyncClient) -> None:
    """
    Uses a genuinely unreachable SQLite path (parent directory does not exist).
    aiosqlite raises OperationalError → /ready must return 503.
    """
    response = await broken_client.get("/ready")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_ready_503_body(broken_client: AsyncClient) -> None:
    response = await broken_client.get("/ready")
    body = response.json()
    assert body["status"] == "unavailable"
    assert "database" in body["detail"].lower()
