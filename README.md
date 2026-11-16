# Bolkhata (बोलखाता)

> A voice-first digital ledger for Indian kirana shopkeepers (Hindi, English, Hinglish), built for the Scaler x Wispr Flow "India Runs on Voice" hackathon.

Reliable, measured, money-safe, and honest about its limits.

---

## Quickstart (Under 5 Minutes)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2+ installed and running.
- Alternatively, for local dev without Docker: Python 3.11 (`uv`), Node.js 24 (`npm`).

### Run with Docker Compose

1. **Clone the repository and enter the directory**:
   ```bash
   cd BolKhata
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Start services**:
   ```bash
   docker compose up --build
   ```

4. **Verify services**:
   - Frontend UI: [http://localhost:3000](http://localhost:3000)
   - Backend Liveness probe: [http://localhost:8000/health](http://localhost:8000/health)
   - Backend Database Readiness probe: [http://localhost:8000/ready](http://localhost:8000/ready)

To run with optional PostgreSQL instead of SQLite:
```bash
docker compose --profile pg up --build
```

---

## Local Development (Without Docker)

### Backend

```bash
cd backend

# Install dependencies using uv and Python 3.11
uv sync --python 3.11

# Run database migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn bolkhata.api.app:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server with proxy to backend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000). Vite proxies `/api/*` directly to `http://localhost:8000/*`.

---

## Quality & Testing Commands

### Backend Verification
From the `backend/` directory:
```bash
# Run test suite (30+ unit & integration tests)
uv run pytest ../tests/ -v

# Code linting
uv run ruff check src/

# Strict type checking
uv run mypy src/bolkhata
```

### Frontend Verification
From the `frontend/` directory:
```bash
# Linting
npm run lint

# TypeScript verification and production build
npm run build
```

---

## Architecture & Monorepo Layout

```
BolKhata/
├── backend/
│   ├── alembic/                # Database migrations (async runner)
│   ├── src/bolkhata/
│   │   ├── api/                # FastAPI factory and routes (/health, /ready)
│   │   ├── common/             # Async database engine and fail-closed logging
│   │   ├── config/             # Pydantic Settings loaded from .env
│   │   └── domains/            # Strict domain boundary (ledger logic isolated here)
│   └── pyproject.toml          # Pinned Python dependencies, Ruff, mypy
├── frontend/
│   ├── src/                    # React 18 + TypeScript + Vite app
│   │   └── apps/ledger/        # Frontend ledger domain boundary
│   ├── nginx.conf              # Production reverse proxy (/api -> backend:8000)
│   └── package.json
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   └── slo.md                  # Latency budget and evaluation metrics
├── tests/
│   ├── unit/                   # Unit tests (fail-closed redaction filter across all levels)
│   └── integration/            # Integration tests (health and genuine DB-failure 503)
├── docker-compose.yml          # Backend + Frontend + optional PostgreSQL profile
└── .env.example                # Canonical environment template
```

---

## Key Design Principles

1. **Money Safety**: Deterministic calculations, append-only ledgers, idempotent mutations, and explicit voice read-back confirmations.
2. **Fail-Closed Logging**: Sensitive customer data (names, transcripts, phone numbers, credentials) is redacted across *all* log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
3. **Domain Isolation**: Core voice pipelines remain decoupled from the kirana ledger domain. Ledger-specific logic is confined to `domains/ledger`.
4. **Push-to-Talk**: Direct push-to-talk voice capture without complex barge-in or WebRTC overhead.
5. **Single Command Run**: Complete local stack starts with `docker compose up`.
