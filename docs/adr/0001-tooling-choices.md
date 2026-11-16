# 1. Tooling Choices for Bolkhata Monorepo

Date: 2026-11-16
Status: Accepted

## Context

Bolkhata is a voice-first ledger application designed for Indian kirana shopkeepers, supporting Hindi, English, and Hinglish. It is built under tight hackathon timelines (Scaler x Wispr Flow "India Runs on Voice") with rigorous engineering constraints:
- Monorepo hosting both backend and frontend.
- Single command startup (`docker compose up`).
- Strict typing, linting, and deterministic testing.
- Hardware constraints: primary dev/demo machine is an Apple Silicon MacBook (16 GB unified memory); optional inference node is a Windows RTX 3050 (6 GB VRAM).

We needed to select a developer tooling suite that maximizes developer velocity, guarantees type safety, enforces code quality, and avoids infrastructure bloat.

## Decision

We made the following architectural and tooling choices:

1. **Package Management**:
   - Backend: `uv` (Astral). Extremely fast dependency resolution, lockfile management, and virtual environment provisioning with strict Python 3.11 pinning.
   - Frontend: `npm` with Node 24 and Vite 6.

2. **Backend Framework & Database**:
   - `FastAPI`: High-performance asynchronous API framework with native OpenAPI and Pydantic v2 support.
   - `SQLAlchemy 2 (Asyncio)` with `aiosqlite`: Single asynchronous database engine pattern across the application. SQLite is the default zero-config storage engine; PostgreSQL (`psycopg` / `asyncpg`) is supported via an optional Docker Compose profile (`pg`).
   - `Alembic`: Database schema migrations executed asynchronously (`asyncio.run`) in `env.py`, decoupleable from the web application lifecycle.

3. **Code Quality & Typing**:
   - Backend: `Ruff` for linting and formatting (replaces flake8, black, isort). `mypy` with `strict = true` on all application source code.
   - Frontend: `ESLint 9` (flat config) and TypeScript 5.7 in strict mode.

4. **Structured Logging & Fail-Closed Redaction**:
   - `structlog`: Emits JSON structured logs. Request context variables (`session_id`, `turn_id`, `generation_id`) are injected automatically via `contextvars`.
   - Redaction processor runs unconditionally across all log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`). It sanitizes customer names, phone numbers, transcripts, and credentials with a fail-closed error fallback.

5. **Secrets & Hygiene**:
   - `detect-secrets` and `pre-commit` configuration for early vulnerability and credential leak detection.

## Consequences

- Zero runtime overhead for heavy sync engines or unneeded ORM complexity.
- Local setup time is minimal (< 5 minutes with `uv` and `npm`).
- Codebase strictly adheres to static analysis with no permissive type escapes.
- No Redis or message queues introduced prematurely.
