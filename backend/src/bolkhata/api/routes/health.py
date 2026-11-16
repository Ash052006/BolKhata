"""
Health and readiness endpoints.

GET /health  — always returns 200; confirms the process is alive.
GET /ready   — returns 200 when the database is reachable, 503 otherwise.

Error-handling contract for /ready
-----------------------------------
* SQLAlchemy errors (connectivity) → 503 Service Unavailable.
* Any other unexpected exception propagates normally so FastAPI's
  default 500 handler fires and the application bug is not masked.

This deliberate distinction satisfies the requirement that /ready "handles
database connectivity errors without masking unrelated application bugs."
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from bolkhata.common.db import check_database_connectivity
from bolkhata.common.logging import get_logger
from bolkhata.config.settings import settings

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health() -> JSONResponse:
    """Liveness probe — always 200 when the process is running."""
    return JSONResponse({"status": "ok", "version": settings.app_version})


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """
    Readiness probe — returns 200 when the database is reachable, 503 otherwise.

    Only SQLAlchemyError is caught here.  Any other exception (programming error,
    attribute error on app.state, etc.) propagates to FastAPI's default 500 handler
    so application bugs are not silently swallowed.
    """
    engine = request.app.state.engine
    try:
        await check_database_connectivity(engine)
    except SQLAlchemyError as exc:
        logger.warning("readiness_check_failed", error_type=type(exc).__name__)
        return JSONResponse(
            {"status": "unavailable", "detail": "database unreachable"},
            status_code=503,
        )
    return JSONResponse({"status": "ready"})
