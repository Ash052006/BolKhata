"""
Application settings loaded from environment variables.

All secrets and infrastructure addresses must be provided via environment
variables or a .env file — never hard-coded.  Pydantic validates types and
required fields at import time so mis-configuration fails fast.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ app
    app_env: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # ------------------------------------------------------------------ database
    # Default: SQLite for local development.
    # Override DATABASE_URL to use PostgreSQL (requires the `pg` optional dep).
    database_url: str = "sqlite+aiosqlite:///./bolkhata.db"

    @field_validator("database_url")
    @classmethod
    def _validate_db_url(cls, v: str) -> str:
        allowed_schemes = (
            "sqlite+aiosqlite",
            "postgresql+asyncpg",
            "postgresql+psycopg",
        )
        if not any(v.startswith(s) for s in allowed_schemes):
            raise ValueError(f"DATABASE_URL must use one of {allowed_schemes}. Got: {v!r}")
        return v

    # ------------------------------------------------------------------ server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


# Module-level singleton — imported everywhere as `from bolkhata.config.settings import settings`
settings = Settings()
