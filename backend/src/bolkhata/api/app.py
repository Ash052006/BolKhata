"""
FastAPI application factory.

Startup / shutdown resource management is handled by a lifespan context manager
(the modern FastAPI pattern — on_event hooks are deprecated).

Lifespan sequence
-----------------
  startup:
    1. Configure structured JSON logging.
    2. Build the async database engine.
    3. Attach engine and session factory to app.state.
  shutdown:
    1. Dispose the engine (closes all pooled connections cleanly).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bolkhata.api.routes.health import router as health_router
from bolkhata.common.db import build_engine, build_session_factory
from bolkhata.common.logging import configure_logging, get_logger
from bolkhata.config.settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application-level resources across the full process lifetime."""
    # --- startup ---
    configure_logging(settings.log_level)
    logger.info("bolkhata_starting", env=settings.app_env, version=settings.app_version)

    db_url: str | None = getattr(app.state, "database_url", None)
    engine = build_engine(db_url)
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    logger.info("bolkhata_ready")

    yield

    # --- shutdown ---
    logger.info("bolkhata_shutting_down")
    await engine.dispose()
    logger.info("bolkhata_stopped")


def create_app() -> FastAPI:
    """Create and return the configured FastAPI application."""
    app = FastAPI(
        title="Bolkhata",
        description="Voice-first ledger for Indian kirana shopkeepers",
        version=settings.app_version,
        lifespan=lifespan,
        # Disable docs in production to reduce attack surface.
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    app.include_router(health_router)

    return app


# WSGI/ASGI entry point for Uvicorn: `uvicorn bolkhata.api.app:app`
app = create_app()
