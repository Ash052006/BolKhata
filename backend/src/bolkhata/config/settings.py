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

    # ------------------------------------------------------------------ providers
    asr_provider: str = "mock"
    asr_max_concurrency: int = 1
    tts_provider: str = "mock"
    llm_provider: str = "mock"
    vad_provider: str | None = None

    @field_validator("asr_provider")
    @classmethod
    def _validate_asr_provider(cls, v: str) -> str:
        allowed = ("mock", "faster_whisper", "mlx_whisper")
        norm = v.strip().lower()
        if norm not in allowed:
            raise ValueError(f"ASR_PROVIDER must be one of {allowed}. Got: {v!r}")
        return norm

    @field_validator("asr_max_concurrency")
    @classmethod
    def _validate_asr_max_concurrency(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"ASR_MAX_CONCURRENCY must be at least 1. Got: {v}")
        return v

    @field_validator("tts_provider")
    @classmethod
    def _validate_tts_provider(cls, v: str) -> str:
        allowed = ("mock", "piper", "edge")
        norm = v.strip().lower()
        if norm not in allowed:
            raise ValueError(f"TTS_PROVIDER must be one of {allowed}. Got: {v!r}")
        return norm

    @field_validator("llm_provider")
    @classmethod
    def _validate_llm_provider(cls, v: str) -> str:
        allowed = ("mock", "groq", "ollama")
        norm = v.strip().lower()
        if norm not in allowed:
            raise ValueError(f"LLM_PROVIDER must be one of {allowed}. Got: {v!r}")
        return norm

    @field_validator("vad_provider")
    @classmethod
    def _validate_vad_provider(cls, v: str | None) -> str | None:
        if v is None:
            return None
        norm = v.strip().lower()
        if not norm or norm == "none":
            return None
        allowed = ("mock", "silero")
        if norm not in allowed:
            raise ValueError(f"VAD_PROVIDER must be one of {allowed} or None. Got: {v!r}")
        return norm

    # ------------------------------------------------------------------ server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


# Module-level singleton — imported everywhere as `from bolkhata.config.settings import settings`
settings = Settings()
