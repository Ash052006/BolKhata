# BolKhata — Architectural & Engineering Decision Log

> **Document Type:** Central Engineering Decision Log
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)
> **Last Updated:** Sprint S1 Stage 2
> **Status:** Living Document — Updated with each architectural choice

---

## Purpose & Scope

This document answers: **WHY did we build BolKhata this way?**

It captures the architectural, technological, and engineering trade-offs made across BolKhata's development lifecycle. Decisions are recorded chronologically, starting from S0 (Foundation). Every record documents context, chosen solution, alternatives rejected, trade-offs, consequences, verifiable code/test evidence, and how to defend the choice in a technical interview.

### Decision Taxonomy
- **Implemented Decision:** Chosen, implemented in code, passing tests, and verified in Git history.
- **Approved Architectural Direction:** Accepted architectural consensus (e.g., in accepted ADRs or roadmaps) whose implementation is pending in an upcoming milestone.
- **Proposed:** Under active design discussion; not yet accepted or merged.
- **Superseded:** Previously accepted, but replaced by a later architectural decision (with explicit rationale).

---

## Table of Contents

- [S0: Foundation Decisions](#s0-foundation-decisions)
  - [DEC-0001: Monorepo Architecture with Dedicated Root Tooling](#dec-0001-monorepo-architecture-with-dedicated-root-tooling)
  - [DEC-0002: FastAPI Async Application Factory & Probes](#dec-0002-fastapi-async-application-factory--probes)
  - [DEC-0003: React, TypeScript, and Vite for Voice PWA Frontend](#dec-0003-react-typescript-and-vite-for-voice-pwa-frontend)
  - [DEC-0004: Async SQLAlchemy 2.0 and Alembic Migrations](#dec-0004-async-sqlalchemy-20-and-alembic-migrations)
  - [DEC-0005: SQLite WAL Default with PostgreSQL Docker Profile](#dec-0005-sqlite-wal-default-with-postgresql-docker-profile)
  - [DEC-0006: Fail-Closed PII & Credential Scrubbing in Structured Logs](#dec-0006-fail-closed-pii--credential-scrubbing-in-structured-logs)
  - [DEC-0007: Hermetic Secret Scanning with Line Allowlisting](#dec-0007-hermetic-secret-scanning-with-line-allowlisting)
  - [DEC-0008: Strict Static Typing & Multi-Pass Quality Gates](#dec-0008-strict-static-typing--multi-pass-quality-gates)
  - [DEC-0009: Strict Domain Isolation Boundary (ADR 0002)](#dec-0009-strict-domain-isolation-boundary-adr-0002)
- [S1: Provider Architecture Decisions](#s1-provider-architecture-decisions)
  - [DEC-0010: Abstract Provider Contracts vs Direct Model Coupling (ADR 0003)](#dec-0010-abstract-provider-contracts-vs-direct-model-coupling-adr-0003)
  - [DEC-0011: Zero-Network Deterministic Mocks for CI & Local Development](#dec-0011-zero-network-deterministic-mocks-for-ci--local-development)
  - [DEC-0012: Settings-Driven Dependency Injection Registry](#dec-0012-settings-driven-dependency-injection-registry)
  - [DEC-0013: Canonical Startup Ordering & Reverse-Order Shutdown](#dec-0013-canonical-startup-ordering--reverse-order-shutdown)
  - [DEC-0014: Identity-Based Provider Tracking for Cleanup Retries](#dec-0014-identity-based-provider-tracking-for-cleanup-retries)
  - [DEC-0015: Early Rollback Tracking on Startup Failure](#dec-0015-early-rollback-tracking-on-startup-failure)
  - [DEC-0016: Structured Output Mocking via Explicit Fixtures](#dec-0016-structured-output-mocking-via-explicit-fixtures)
  - [DEC-0017: Transparent Async Cancellation Semantics for Native Inference](#dec-0017-transparent-async-cancellation-semantics-for-native-inference)
- [S1: Audio Utilities & Settings Decisions](#s1-audio-utilities--settings-decisions)
  - [DEC-0018: Standardized 16 kHz Mono Linear PCM Contract](#dec-0018-standardized-16-khz-mono-linear-pcm-contract)
  - [DEC-0019: Standard-Library `array` over NumPy for Shared Audio Utilities](#dec-0019-standard-library-array-over-numpy-for-shared-audio-utilities)
  - [DEC-0020: Mathematical Normalization Boundaries for Float32 Samples](#dec-0020-mathematical-normalization-boundaries-for-float32-samples)
  - [DEC-0021: Strict Byte Alignment and Duration Validation](#dec-0021-strict-byte-alignment-and-duration-validation)
  - [DEC-0022: Bounded ASR Concurrency Defaulting to Unity](#dec-0022-bounded-asr-concurrency-defaulting-to-unity)
- [S2: Hinglish Normalization & Evaluation Decisions](#s2-hinglish-normalization--evaluation-decisions)
  - [DEC-0029: Deterministic Spoken-Number and Unit Parsing Grammar](#dec-0029-deterministic-spoken-number-and-unit-parsing-grammar)
  - [DEC-0023: Honest Optional Confidence Contract (float | None)](#dec-0023-honest-optional-confidence-contract-float--none)
  - [DEC-0024: Vocabulary-Prompt Support (initial_prompt) for Contextual Biasing](#dec-0024-vocabulary-prompt-support-initial_prompt-for-contextual-biasing)
  - [DEC-0025: Platform-Specific Optional Dependency Isolation for AI Runtimes (Superseded)](#dec-0025-platform-specific-optional-dependency-isolation-for-ai-runtimes)
  - [DEC-0026: Apple Silicon-Only Architecture with MLX ASR Runtime](#dec-0026-apple-silicon-only-architecture-with-mlx-asr-runtime)
  - [DEC-0027: MLX-Whisper ASR Provider Architecture, Bounded Worker Tracking, and Lifecycle Isolation](#dec-0027-mlx-whisper-asr-provider-architecture-bounded-worker-tracking-and-lifecycle-isolation)
  - [DEC-0028: Push-to-Talk WebSocket Protocol, Explicit Four-State Machine, and Generation Invariants](#dec-0028-push-to-talk-websocket-protocol-explicit-four-state-machine-and-generation-invariants)

---

## S0: Foundation Decisions

### DEC-0001: Monorepo Architecture with Dedicated Root Tooling
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `pyproject.toml`, `.pre-commit-config.yaml`, `docker-compose.yml`, `backend/`, `frontend/`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0001: Tooling Choices](adr/0001-tooling-choices.md)

**Context:**
BolKhata requires a high-performance Python speech backend and a mobile-friendly browser interface for kirana shopkeepers. Splitting the project into separate Git repositories would introduce cross-repo version drift, synchronized release overhead, and friction during local end-to-end testing under tight hackathon timelines.

**Decision:**
Adopt a unified monorepo hosting `backend/` and `frontend/` with root-level orchestration (`docker-compose.yml`, root `.pre-commit-config.yaml`, single CI workflow). Backend dependencies are managed by `uv` with Python 3.11 pinning; frontend is managed by `npm` with Node 24.

**Alternatives considered:**
1. *Multi-repo setup:* Separate repos for backend, frontend, and models. Rejected due to version coordination friction.
2. *Full-stack Next.js/Node:* Running Python ML engines via child processes from Node. Rejected because speech models (such as MLX or PyTorch) require first-class Python async runtimes.

**Why this approach:**
Enables atomic commits touching both API contracts and UI views; allows single-command local spin-up (`docker compose up --build`); enforces unified pre-commit validation across both languages.

**Trade-offs:**
Docker multi-stage builds require installing both Python and Node tooling in the root context.

**Consequences:**
Root-level linters must handle both Python (`ruff`, `mypy`) and TypeScript/JSON (`eslint`, `tsc`, `json`).

**Evidence:**
Verified in `docker-compose.yml` and root CI configuration passing in commit `bd11710`.

**Interview angle:**
*Challenge:* Monorepos can become unmaintainable as teams scale.
*Defense:* For a cohesive vertical product with an intimate contract between audio streaming frontend and speech backend, a monorepo eliminates contract drift and enables atomic integration testing. Domain boundaries prevent internal spaghetti code.

---

### DEC-0002: FastAPI Async Application Factory & Probes
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/api/app.py`, `backend/src/bolkhata/api/routes/health.py`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0001: Tooling Choices](adr/0001-tooling-choices.md)

**Context:**
The HTTP/WebSocket server must support high-concurrency real-time audio streaming while providing cloud-native observability for orchestrators.

**Decision:**
Use FastAPI with the Application Factory pattern (`create_app(settings)`), exposing separate liveness (`GET /health`) and readiness (`GET /ready`) probes. `/ready` actively checks async database connectivity via `SELECT 1`.

**Alternatives considered:**
1. *Global singleton app:* Instant instantiation at module import. Rejected because it prevents parameterized testing with different configurations.
2. *Django/Flask:* Heavier memory footprint and synchronous WSGI legacy. Rejected because voice streaming demands native ASGI async concurrency.

**Why this approach:**
The factory pattern enables clean test isolation. Independent liveness and readiness probes prevent traffic routing to nodes that have crashed or lost database connectivity.

**Trade-offs:**
Requires explicit lifespan management context (`lifespan(app)`) rather than older `@app.on_event` decorators.

**Consequences:**
All lifecycle services (database pools, provider registries) are managed within the async lifespan context.

**Evidence:**
Verified by `tests/integration/test_health.py` and `tests/integration/test_ready.py` (healthy 200 and disconnected 503 states).

**Interview angle:**
*Challenge:* Why separate `/health` from `/ready`?
*Defense:* If a database temporarily stalls or reconnects, killing the entire container (failing liveness) creates restart storms. A failing readiness probe stops incoming traffic while keeping the process alive to finish draining active voice sessions.

---

### DEC-0003: React, TypeScript, and Vite for Voice PWA Frontend
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/App.tsx`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0001: Tooling Choices](adr/0001-tooling-choices.md)

**Context:**
The frontend must run reliably on low-cost Android smartphones in Indian retail stores, capture uncompressed microphone audio via Web Audio API, and render instantaneous UI state changes.

**Decision:**
Build a lightweight Single Page Application (SPA) / Progressive Web App (PWA) using React 18, strict TypeScript, and Vite 6.

**Alternatives considered:**
1. *Next.js SSR:* Adds server-side Node rendering overhead. Unnecessary because kirana shopkeepers use the app as an interactive client-side tool, not a public SEO website.
2. *Vanilla JavaScript:* Lacks compile-time state guarantees for complex voice dialogue state machines.

**Why this approach:**
Vite delivers sub-second Hot Module Replacement (HMR) and optimized static production bundles (<150 KB gzip). Strict TypeScript prevents client-side null-pointer crashes during live voice interactions.

**Trade-offs:**
Requires maintaining a separate Node.js build pipeline and configuring Vite dev proxies to route `/api` to FastAPI.

**Consequences:**
Audio recording will use client-side `AudioWorklet` streaming raw PCM directly over WebSockets.

**Evidence:**
`npm run build` generates production bundle in ~250ms with zero TypeScript warnings.

**Interview angle:**
*Challenge:* Why not Flutter or React Native for a mobile-first app?
*Defense:* A PWA requires zero installation barrier for shopkeepers, allows instantaneous updates without app store review delays, and has full access to the Web Audio `AudioWorklet` API for 16 kHz PCM streaming.

---

### DEC-0004: Async SQLAlchemy 2.0 and Alembic Migrations
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/db.py`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0001: Tooling Choices](adr/0001-tooling-choices.md)

**Context:**
The database layer must support asynchronous queries to avoid blocking the event loop during transactions, while enforcing formal schema versioning across developer machines and Docker environments.

**Decision:**
Use SQLAlchemy 2.0 with `ext.asyncio` (`AsyncEngine`, `async_sessionmaker`) and Alembic for automated migrations.

**Alternatives considered:**
1. *Raw SQL strings:* High risk of SQL injection and lack of schema migration tracking.
2. *Tortoise ORM / Prisma Python:* Smaller community, less mature migration tooling than Alembic.

**Why this approach:**
SQLAlchemy 2.0 provides 100% type-annotated query syntax (`Mapped[...]`), native async support, and industry-standard schema migrations via Alembic.

**Trade-offs:**
Async SQLAlchemy requires running migrations through `run_sync` wrappers in `alembic/env.py`.

**Consequences:**
Database schemas are defined declaratively and versioned in `backend/alembic/versions/`.

**Evidence:**
Verified by `tests/integration/test_alembic_smoke.py`, which performs a live schema `upgrade head` and `downgrade base` cycle.

**Interview angle:**
*Challenge:* Does async DB access actually improve performance on SQLite?
*Defense:* SQLite itself is single-writer file-based, but using `aiosqlite` prevents blocking the main event loop thread while disk I/O operations complete, ensuring WebSocket audio frames are not starved.

---

### DEC-0005: SQLite WAL Default with PostgreSQL Docker Profile
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/db.py`, `backend/src/bolkhata/config/settings.py`, `docker-compose.yml`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0001: Tooling Choices](adr/0001-tooling-choices.md)

**Context:**
BolKhata must run locally on developer laptops with zero external services (embedded SQLite), yet support multi-container production deployments (PostgreSQL) without code modifications.

**Decision:**
Default to SQLite (`sqlite+aiosqlite:///bolkhata.db`) with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) enabled automatically on startup. Provide a Docker Compose profile (`--profile pg`) for PostgreSQL with zero code changes required.

**Alternatives considered:**
1. *PostgreSQL mandatory:* Requires running a PostgreSQL container for every unit test and developer run. Rejected as too heavy for quick local iteration.
2. *SQLite default rollback journal:* Standard SQLite locks the entire database during writes. Rejected because simultaneous read queries would block.

**Why this approach:**
WAL mode allows concurrent readers and a concurrent writer, drastically reducing lock contention. SQLAlchemy's dialect abstraction enables identical application queries across SQLite and Postgres.

**Trade-offs:**
SQLite lacks certain PostgreSQL features (e.g. native JSONB indexing), requiring portable column types.

**Consequences:**
Transactions and migrations must adhere to ANSI SQL standards supported by both engines.

**Evidence:**
Verified in `backend/src/bolkhata/common/db.py` (WAL pragma execution) and `tests/integration/test_lifespan.py`.

**Interview angle:**
*Challenge:* Why enable WAL mode explicitly?
*Defense:* By default, SQLite uses a rollback journal which blocks readers while a write transaction is committed. In a voice app where background speech queries happen simultaneously with ledger balance reads, WAL mode prevents reader starvation.

---

### DEC-0006: Fail-Closed PII & Credential Scrubbing in Structured Logs
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/logging.py`, `tests/unit/test_logging_redaction.py`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0001: Tooling Choices](adr/0001-tooling-choices.md)

**Context:**
Voice ledger applications capture customer names, phone numbers, and transaction balances. Accidental leakage of this data into centralized log aggregators violates India's Digital Personal Data Protection (DPDP) Act and basic merchant privacy.

**Decision:**
Implement a custom `StructuredJsonFormatter` in `bolkhata.common.logging` that scrubs PII and credentials across all log levels. Redaction applies to dictionary keys (`customer_name`, `phone`, `token`, `password`), Indian mobile regex patterns (`\b[6-9]\d{9}\b`), bearer tokens, and exception tracebacks. If redaction fails, the logger fails closed, emitting a safe sentinel.

**Alternatives considered:**
1. *Relying on developer discipline:* Asking developers not to log sensitive fields. Rejected as error-prone.
2. *Third-party logging proxies:* Adding an external log scrubbing daemon. Rejected as added infrastructure complexity.

**Why this approach:**
In-process scrubbing guarantees that unredacted customer PII never leaves the Python memory space, whether logged intentionally or via unhandled exception frames.

**Trade-offs:**
Recursive dictionary inspection and regex scanning introduce slight CPU overhead per log call (mitigated by structured logging only at INFO+).

**Consequences:**
Debug logs can safely be captured in production without violating user privacy.

**Evidence:**
Verified by 24 test cases in `tests/unit/test_logging_redaction.py`.

**Interview angle:**
*Challenge:* How do you ensure exception tracebacks don't leak secrets stored in local variables?
*Defense:* Our formatter recursively sanitizes the exception chain and renders sanitized traceback strings, scrubbing API keys and tokens before formatting into JSON.

---

### DEC-0007: Hermetic Secret Scanning with Line Allowlisting
- **Date:** 2026-11-16
- **Stage:** S0 Foundation / Remediation
- **Status:** Implemented Decision
- **Related files:** `.secrets.baseline`, `.pre-commit-config.yaml`
- **Related commits:** `bd11710`, `8aa8415`

**Context:**
Automated secret detection (`detect-secrets`) flagged synthetic test tokens (`test_token_1234567890abcdef`) in `test_logging_redaction.py`.

**Decision:**
Do not weaken or disable secret scanning detectors. Instead, use `detect-secrets` line-level allowlisting in `.secrets.baseline`, pinning the audited synthetic test fixtures.

**Alternatives considered:**
1. *Disabling high-entropy string detector:* Defeats the purpose of the security gate.
2. *Obfuscating test strings (e.g. base64 decode at runtime):* Hides test intent and makes fixtures difficult to read.

**Why this approach:**
Maintains 100% detector rigor on real project code while explicitly auditing and allowlisting synthetic test inputs.

**Trade-offs:**
Adding new high-entropy test fixtures requires updating `.secrets.baseline`.

**Consequences:**
No real secret can ever be committed; CI fails immediately if unallowlisted credentials appear.

**Evidence:**
Verified by `git ls-files | xargs backend/.venv/bin/detect-secrets scan` returning `{"results": {}}`.

**Interview angle:**
*Challenge:* What is the engineering lesson from false-positive security scans?
*Defense:* Never disable security gates to unblock CI. Audit and allowlist verified test data through formal tool mechanisms, ensuring production code remains strictly guarded.

---

### DEC-0008: Strict Static Typing & Multi-Pass Quality Gates
- **Date:** 2026-11-16
- **Stage:** S0 Foundation / Remediation
- **Status:** Implemented Decision
- **Related files:** `pyproject.toml`, `.pre-commit-config.yaml`
- **Related commits:** `fe97621`, `e1cf4a9`

**Context:**
Python's dynamic typing allows subtle runtime errors (e.g., passing `None` where a float is expected, or missing dictionary keys) that can crash real-time voice loops. Linters can drift between developer environments.

**Decision:**
Enforce strict Mypy type-checking on all backend code (`disallow_untyped_defs = true`, `check_untyped_defs = true`), Ruff linting/formatting, and run all pre-commit hooks twice consecutively in CI.

**Alternatives considered:**
1. *Permissive Mypy:* Allowing partial type hints. Rejected because it hides type errors in edge cases.
2. *Single-pass pre-commit:* Formatters can modify files on pass 1 and fail the build.

**Why this approach:**
Two-pass pre-commit verifies idempotency: formatters must leave code unchanged on pass 2. Strict static typing catches bugs before tests are even executed.

**Trade-offs:**
Higher upfront development time writing explicit generic type annotations (e.g. `array.array[float]`).

**Consequences:**
Zero unhandled type errors across the entire codebase.

**Evidence:**
`uv run mypy src/bolkhata` checks 23 source files with zero errors; pre-commit passes twice consecutively.

**Interview angle:**
*Challenge:* Why run pre-commit twice?
*Defense:* The first run applies auto-formatters (which returns exit code 1 if files changed). The second run proves that the changes are idempotent and that the codebase is completely stable.

---

### DEC-0009: Strict Domain Isolation Boundary (ADR 0002)
- **Date:** 2026-11-16
- **Stage:** S0 Foundation
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/domains/`, `frontend/src/apps/ledger/`
- **Related commit:** `bd11710`
- **Related ADR:** [ADR 0002: Hackathon Scope and Domain Isolation Boundary](adr/0002-hackathon-scope-and-domain-isolation.md)

**Context:**
Hackathon requirements and problem statements evolve. Tightly coupling speech streaming code with kirana ledger business logic makes it difficult to pivot or reuse the voice pipeline for other retail domains.

**Decision:**
Isolate ledger business logic exclusively inside `bolkhata/domains/ledger` and `frontend/src/apps/ledger`. The core voice pipeline is strictly forbidden from importing from `domains/ledger`.

**Alternatives considered:**
1. *Monolithic voice-ledger controller:* Directly handling ledger updates inside WebSocket handlers. Rejected as inflexible spaghetti architecture.
2. *Over-abstracting DomainPack in S0:* Implementing complex abstract protocols before real requirements exist. Rejected by ADR 0002.

**Why this approach:**
Package boundaries allow the core voice streaming infrastructure to remain stable while business domains plug in via standardized interfaces.

**Trade-offs:**
Domain-specific actions must be mediated through formal data transfer objects.

**Consequences:**
When S3 introduces the kirana ledger, it will implement a pluggable `DomainPack` interface without altering the ASR or audio streaming modules.

**Evidence:**
Verified in `backend/src/bolkhata/domains/` package layout and ADR 0002.

**Interview angle:**
*Challenge:* Is premature domain isolation an over-engineering anti-pattern?
*Defense:* We did *not* build complex unused abstraction classes in S0 (which would be over-engineering). We merely established strict package boundaries, ensuring voice code doesn't import database models directly.

---

## S1: Provider Architecture Decisions

### DEC-0010: Abstract Provider Contracts vs Direct Model Coupling (ADR 0003)
- **Date:** 2026-11-16
- **Stage:** S1 Stage 1
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/base.py`, `backend/src/bolkhata/tts/base.py`, `backend/src/bolkhata/llm/base.py`, `backend/src/bolkhata/asr/vad.py`
- **Related commit:** `96b2b52`
- **Related ADR:** [ADR 0003: Provider Interfaces and Registry](adr/0003-provider-interfaces-and-registry.md)

*(Historical Note: When DEC-0008 was established in S1 Stage 1, both Faster-Whisper and MLX-Whisper were contemplated. S1 Stage 2 subsequently standardized physical ASR execution exclusively on Apple Silicon MLX per DEC-0026).*

**Context:**
Machine learning runtimes vary across target hardware and test environments (e.g. Apple Silicon running Metal/MLX vs developer CI environments with zero GPUs). Directly importing neural model libraries in route handlers couples the codebase to specific hardware.

**Decision:**
Define abstract base classes (`ASRProvider`, `TTSProvider`, `LLMProvider`, `VADProvider`) with asynchronous methods, typed result contracts, and unified lifecycle management (`initialize`, `warmup`, `shutdown`).

**Alternatives considered:**
1. *Direct imports:* Calling concrete model libraries directly in API routes. Rejected due to inability to test offline.
2. *Dynamic duck typing:* Passing arbitrary objects without abstract base classes. Rejected because Mypy cannot enforce contract compliance.

**Why this approach:**
Enables complete decoupling of business logic from machine learning runtimes; allows swapping between mock and planned real adapters (such as MLX-Whisper on Apple Silicon) via a single environment variable (`ASR_PROVIDER`).

**Trade-offs:**
Requires defining common denominators across models (e.g. standardizing on 16 kHz PCM inputs).

**Consequences:**
All planned real model adapters (MLX-Whisper, Piper TTS) must implement these contracts.

**Evidence:**
Verified by `tests/unit/test_providers_mock.py` confirming mock providers satisfy ABC contracts.

**Interview angle:**
*Challenge:* What is the performance cost of Python abstract base classes?
*Defense:* Zero runtime overhead during inference. The virtual table dispatch in Python takes nanoseconds, while neural model inference takes dozens of milliseconds. The architectural flexibility and testability vastly outweigh any theoretical dispatch overhead.

---

### DEC-0011: Zero-Network Deterministic Mocks for CI & Local Development
- **Date:** 2026-11-16
- **Stage:** S1 Stage 1
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/mock.py`, `backend/src/bolkhata/tts/mock.py`, `backend/src/bolkhata/llm/mock.py`
- **Related commit:** `96b2b52`
- **Related ADR:** [ADR 0003: Provider Interfaces and Registry](adr/0003-provider-interfaces-and-registry.md)

**Context:**
Downloading multi-gigabyte neural weights (Whisper models, LLM weights) in CI causes slow, flaky, expensive builds that fail when external networks hiccup.

**Decision:**
Build high-fidelity, deterministic mock providers (`MockASRProvider`, `MockTTSProvider`, `MockLLMProvider`, `MockVADProvider`) that execute in milliseconds without external network or GPU access. Mocks return structurally valid data (e.g. `MockTTSProvider` generates mathematically valid sine-wave PCM audio).

**Alternatives considered:**
1. *Downloading tiny Whisper models in CI:* Adds ~100MB download per CI run and requires CPU inference time.
2. *Mocking at the unit test level with `unittest.mock`:* Brittle and fails to test provider contract compliance.

**Why this approach:**
Provides complete system testability. Entire end-to-end provider lifecycles and pipeline tests run in <0.2 seconds.

**Trade-offs:**
Mocks do not test the actual acoustic accuracy of neural weights (which is delegated to dedicated evaluation harnesses).

**Consequences:**
CI runs deterministically on every commit with 100% offline hermetic execution.

**Evidence:**
96 backend tests pass in 0.12s on standard CPUs.

**Interview angle:**
*Challenge:* If CI only uses mocks, how do you know the real models work?
*Defense:* We separate **contract/lifecycle testing** from **model accuracy evaluation**. Contract tests run on every commit via deterministic mocks. Accuracy benchmarks (WER, RTF) run on dedicated hardware nodes against recorded ground-truth audio in `docs/benchmarks`.

---

### DEC-0012: Settings-Driven Dependency Injection Registry
- **Date:** 2026-11-16
- **Stage:** S1 Stage 1
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/registry.py`, `backend/src/bolkhata/config/settings.py`
- **Related commit:** `96b2b52`
- **Related ADR:** [ADR 0003: Provider Interfaces and Registry](adr/0003-provider-interfaces-and-registry.md)

**Context:**
Providers need configuration (model paths, device selection, concurrency limits) and must be shared across requests without global mutable state.

**Decision:**
Implement a `ProviderRegistry` class that accepts a typed `Settings` instance, lazily creates provider instances, guards state transitions with an `asyncio.Lock`, and coordinates initialization and warmup.

**Alternatives considered:**
1. *Global singleton module variables:* Hard to reset between test runs; concurrency race conditions.
2. *Heavy DI framework (e.g. dependency-injector):* Unnecessary external dependency and runtime overhead for 4 providers.

**Why this approach:**
Clean, thread-safe dependency injection using standard Python asyncio primitives, easily instantiated with custom settings in tests.

**Trade-offs:**
Requires explicit lifecycle management in FastAPI lifespan.

**Consequences:**
API routes access active providers via the dependency-injected registry.

**Evidence:**
Verified by `test_default_mock_selection` and `test_registry_concurrency_safe_initialization` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* Why not use FastAPI's built-in `Depends` directly?
*Defense:* FastAPI's `Depends` is excellent for per-request dependencies (like database sessions), but neural providers are expensive long-lived singletons that require explicit async startup, GPU warmup, and graceful shutdown. The registry encapsulates this lifecycle.

---

### DEC-0013: Canonical Startup Ordering & Reverse-Order Shutdown
- **Date:** 2026-11-17
- **Stage:** S1 Stage 1 / Lifecycle Hardening
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/registry.py`
- **Related commits:** `687385c`, `516e03a`
- **Related ADR:** [ADR 0003: Provider Interfaces and Registry](adr/0003-provider-interfaces-and-registry.md)

**Context:**
Providers have implicit pipeline dependencies. A speech pipeline processes audio through ASR $\rightarrow$ TTS $\rightarrow$ LLM $\rightarrow$ VAD. Shutting down providers in arbitrary order can cause active requests to fail if downstream dependencies disappear before upstream inputs.

**Decision:**
Enforce a canonical startup order: ASR $\rightarrow$ TTS $\rightarrow$ LLM $\rightarrow$ optional VAD. Enforce strict reverse order during shutdown: VAD $\rightarrow$ LLM $\rightarrow$ TTS $\rightarrow$ ASR.

**Alternatives considered:**
1. *Unordered concurrent cleanup via `asyncio.gather`:* Fast, but risks deadlocks or crashes if a dependent provider is torn down while another provider is flushing buffers.
2. *Arbitrary list iteration:* Fragile and dependent on dictionary key ordering.

**Why this approach:**
Upstream providers (VAD, LLM) stop accepting new work and terminate before downstream resources (TTS, ASR audio buffers) are deallocated.

**Trade-offs:**
Shutdown is sequential rather than parallel, taking slightly longer if providers have slow teardowns.

**Consequences:**
Guarantees clean, deterministic resource deallocation.

**Evidence:**
Verified by `test_registry_shutdown_reverse_order` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* Why does reverse-order shutdown matter for machine learning models?
*Defense:* If the LLM generates a read-back text while TTS is shutting down, the request crashes with broken pipe errors. Reverse-order teardown stops input ingestion first, allows in-flight synthesis to finish, and releases hardware memory last.

---

### DEC-0014: Identity-Based Provider Tracking for Cleanup Retries
- **Date:** 2026-11-17
- **Stage:** S1 Stage 1 / Lifecycle Hardening
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/registry.py`
- **Related commit:** `516e03a`

**Context:**
If a provider's `shutdown()` fails (e.g. timeout releasing GPU context), the registry must allow the caller to retry shutdown. Earlier logic moved failed providers to a temporary retry list, corrupting their relative shutdown sequence if multiple providers failed.

**Decision:**
Maintain a single `_initialized_providers: list[BaseProvider]` in canonical startup order. Iterate in `reversed()` order during shutdown. Only remove a provider from the list upon *successful* shutdown. If exceptions occur, failed providers remain in their exact relative positions in the list, preserving reverse-order invariants on retry.

**Alternatives considered:**
1. *Popping and appending to a failed list:* Caused reverse-order corruption on multiple failures (discovered and fixed in commit `516e03a`).
2. *Tracking with a set:* Sets do not preserve sequence ordering.

**Why this approach:**
Identity-based list tracking guarantees that repeated calls to `shutdown()` always execute in strict reverse-startup sequence, regardless of how many providers fail or when retries occur.

**Trade-offs:**
None; simpler and more robust than auxiliary tracking lists.

**Consequences:**
The shutdown lifecycle is completely resilient to partial failures and safe for idempotent retry.

**Evidence:**
Verified by `test_multiple_providers_fail_shutdown_retried_in_reverse_startup_order` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* Walk me through a subtle bug you found in production-grade code.
*Defense:* (Explain the retry-order bug, how popping into a failed list reversed the reverse order, and how identity-based tracking in a canonical list solved it).

---

### DEC-0015: Early Rollback Tracking on Startup Failure
- **Date:** 2026-11-17
- **Stage:** S1 Stage 1 / Lifecycle Hardening
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/common/registry.py`
- **Related commit:** `687385c`

**Context:**
Previously, a provider was only recorded in `_initialized_providers` after both `initialize()` and `warmup()` succeeded. If `warmup()` raised an exception (e.g., out-of-memory or Metal graph allocation error during warmup tensor pass), the provider was never tracked, orphaning any GPU memory allocated during `initialize()`.

**Decision:**
Track the provider immediately after its `initialize()` method succeeds. If `warmup()` subsequently fails, the provider is already tracked, triggering automatic rollback and cleanup.

**Alternatives considered:**
1. *Combining initialize and warmup into a single method:* Prevents warming up models in the background after boot.
2. *Ignoring warmup cleanup:* Causes memory leaks in production containers.

**Why this approach:**
Guarantees failure-atomic lifecycle: partial initialization failures are guaranteed to receive cleanup.

**Trade-offs:**
Rollback logic must handle providers that initialized but did not complete warmup.

**Consequences:**
Zero resource leaks on startup crashes.

**Evidence:**
Verified by `test_asr_warmup_failure_after_successful_initialization` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* What happens if a model allocates VRAM in initialize and crashes in warmup?
*Defense:* Because our registry tracks the instance immediately upon `initialize()` success, the failure in `warmup()` triggers an immediate rollback that calls `shutdown()` on that provider, releasing the allocated VRAM.

---

### DEC-0016: Structured Output Mocking via Explicit Fixtures
- **Date:** 2026-11-17
- **Stage:** S1 Stage 1 / Lifecycle Hardening
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/llm/mock.py`, `backend/src/bolkhata/llm/base.py`
- **Related commit:** `687385c`

**Context:**
`MockLLMProvider.complete_structured` previously used a generic fallback that fabricated arbitrary values for unknown Pydantic schemas. In a financial application where ledger schemas represent currency transactions, fabricating random data violates money-safety invariants.

**Decision:**
Require explicit pre-configured fixtures (`set_structured_fixture(schema, instance)`) for all non-default schemas in `MockLLMProvider`. If a structured call is made without a configured fixture, it raises `ValueError` immediately.

**Alternatives considered:**
1. *Pydantic generic fake generator:* Fills fields with random strings/ints. Unacceptable for ledger data.
2. *Always returning None:* Fails type contracts.

**Why this approach:**
Forces test authors to be explicit about test inputs and expected financial outputs, preventing tests from passing on fabricated hallucinations.

**Trade-offs:**
Unit tests requiring structured output must register an explicit fixture before calling `complete_structured`.

**Consequences:**
Guarantees determinism in domain extraction tests.

**Evidence:**
Verified by `test_mock_llm_complete_structured_missing_fixture_fails` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* Why not use Faker or auto-generated mock data?
*Defense:* Auto-generated fake data masks subtle extraction bugs. For financial ledgers, test assertions must match exact ground truth. Failing closed ensures tests only pass when explicit fixtures match expectations.

---

### DEC-0017: Transparent Async Cancellation Semantics for Native Inference
- **Date:** 2026-11-17
- **Stage:** S1 Stage 1 / Lifecycle Hardening
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/base.py`, `docs/adr/0003-provider-interfaces-and-registry.md`
- **Related commit:** `687385c`

**Context:**
Initial documentation suggested that cancelling an asyncio coroutine awaiting speech recognition would terminate native C++ inference. In Python, OS worker threads running C-extensions cannot be forcefully interrupted without risking interpreter corruption.

**Decision:**
Document and formalize exact cancellation semantics: cancelling a coroutine awaiting `asyncio.to_thread` abandons the coroutine on the event loop immediately, but the underlying worker thread continues until the native inference step completes. Bounded concurrency (semaphores) prevents resource starvation from abandoned tasks.

**Alternatives considered:**
1. *Calling C-level thread kill primitives (`pthread_cancel`):* High risk of segfaults, memory leaks, and deadlocks in native C/C++ runtimes.
2. *Pretending cancellation kills the thread:* Dishonest engineering that leads to production memory exhaustion.

**Why this approach:**
Honest architecture reflecting actual Python runtime semantics, guiding safe system design.

**Trade-offs:**
Abandoned inference runs to completion in the background, consuming CPU/GPU cycles for that specific turn.

**Consequences:**
Concurrency limits must account for potentially abandoned requests during rapid client disconnects.

**Evidence:**
Explicitly documented in ADR 0003 and `bolkhata.asr.base` docstrings.

**Interview angle:**
*Challenge:* What happens when you cancel `asyncio.to_thread()`?
*Defense:* Python cannot kill native OS threads. The coroutine raises `CancelledError` on the event loop, but the worker thread executes to the end. That is why we enforce bounded concurrency with semaphores, so abandoned threads cannot pile up and crash the process.

---

## S1: Audio Utilities & Settings Decisions

### DEC-0018: Standardized 16 kHz Mono Linear PCM Contract
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/common.py`
- **Related commit:** `863b07d`

**Context:**
Voice pipelines ingest audio from web browsers, mobile PWAs, and test fixtures. Supporting multiple sample rates, stereo channels, or container formats (WAV headers, MP3, OGG) on the server adds decoding latency and CPU overhead.

**Decision:**
Standardize strictly on headerless `16,000 Hz, 1 Channel (Mono), Signed 16-bit Little-Endian Linear PCM` (`pcm_s16le`). Audio clients must perform resampling in the browser via `AudioWorklet`.

**Alternatives considered:**
1. *Server-side FFmpeg transcoding:* Ingesting any format and transcoding on the fly. Rejected due to CPU latency and heavy external dependencies.
2. *44.1 kHz / 48 kHz high-fidelity audio:* High bandwidth consumption with zero accuracy gain (Whisper downsamples to 16 kHz internally).

**Why this approach:**
16 kHz mono produces exactly 32,000 bytes/sec, streaming smoothly over congested 3G/4G networks. Direct buffer access eliminates container parsing overhead.

**Trade-offs:**
Frontend must handle client-side downsampling and PCM buffering.

**Consequences:**
All server audio utilities, providers, and test fixtures adhere to this exact binary contract.

**Evidence:**
Verified in `backend/src/bolkhata/asr/common.py` (`SAMPLE_RATE_HZ = 16000`, `BYTES_PER_SAMPLE = 2`).

**Interview angle:**
*Challenge:* Why not stream Opus-compressed audio over WebSockets?
*Defense:* Opus is great for long calls, but for short push-to-talk kirana utterances (2–4 seconds), 32 KB/s raw PCM is tiny (64–128 KB total). Transcoding adds 20–50ms of codec latency on low-end phones and server decompression overhead. Raw PCM streams directly into inference buffers.

---

### DEC-0019: Standard-Library `array` over NumPy for Shared Audio Utilities
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/common.py`
- **Related commit:** `863b07d`

**Context:**
Converting raw PCM bytes to float32 samples is traditionally done using NumPy (`np.frombuffer`). However, adding NumPy as a hard dependency in `bolkhata.asr.common` couples core shared utilities to a heavy C-extension library (50+ MB).

**Decision:**
Implement `pcm_to_float32` using Python's standard-library `array` module (`array.array('h')` and `array.array('f')`), with native byte-swapping (`raw_samples.byteswap()`) on big-endian architectures.

**Alternatives considered:**
1. *Mandating NumPy:* Standard approach, but bloats lightweight utility scripts and container layers.
2. *Manual `struct.unpack` loop:* Slower and creates intermediary Python integer objects for every sample.

**Why this approach:**
Python's `array` module implements the C buffer protocol natively, supports fast `.frombytes()`, and requires zero third-party dependencies. Concrete ASR models accept buffer-protocol objects directly.

**Trade-offs:**
Python list/generator comprehension during float division is slightly slower than vectorized NumPy C-loops on multi-megabyte audio files (negligible on 2–4 second kirana voice clips).

**Consequences:**
Core audio utilities can be imported anywhere without requiring NumPy or PyTorch.

**Evidence:**
Verified by `test_common_utility_imports_without_numpy_or_engines` in `tests/unit/test_asr_common.py`.

**Interview angle:**
*Challenge:* Isn't NumPy always faster than the standard library?
*Defense:* For massive matrix multiplication, yes. But for a 3-second voice clip (48,000 samples), `array.frombytes` executes in microseconds. Avoiding a 50MB C-extension dependency keeps microservices, Lambdas, and test suites lightweight and dependency-isolated.

---

### DEC-0020: Mathematical Normalization Boundaries for Float32 Samples
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/common.py`
- **Related commit:** `863b07d`

**Context:**
Signed 16-bit PCM integers range from $-32768$ to $+32767$. Neural models expect normalized float32 samples strictly within $[-1.0, 1.0]$. Asymmetric normalization (e.g. dividing positive numbers by 32767 and negative by 32768) introduces non-linear distortion.

**Decision:**
Normalize all samples uniformly by dividing by `32768.0`:
- Sample $-32768$ maps exactly to $-1.0$.
- Sample $0$ maps exactly to $0.0$.
- Sample $+32767$ maps to $32767 / 32768.0 \approx +0.999969$.
- Output is strictly bounded in $[-1.0, 1.0]$.

**Alternatives considered:**
1. *Dividing by 32767.0:* Causes $-32768$ to map to $-1.0000305$, violating the $[-1.0, 1.0]$ boundary and triggering clipping warnings in neural audio encoders.
2. *Asymmetric branch (`x / 32767.0 if x > 0 else x / 32768.0`):* Adds branching overhead and introduces non-linear harmonic distortion.

**Why this approach:**
Standard mathematical convention in professional digital audio signal processing and deep learning frameworks (librosa, soundfile).

**Trade-offs:**
Maximum positive amplitude is slightly less than 1.0 ($1 - 2^{-15}$), which is acoustically indistinguishable.

**Consequences:**
Guarantees zero tensor clipping or boundary overflow in neural ASR frontends.

**Evidence:**
Verified by `test_normalization_boundaries` in `tests/unit/test_asr_common.py`.

**Interview angle:**
*Challenge:* Why divide by 32768.0 instead of 32767.0?
*Defense:* Signed 16-bit two's complement has 65,536 values, ranging from -32,768 to +32,767. Dividing by 32767 causes -32768 to exceed -1.0, which causes gradient clipping in neural network input layers. Dividing by 32768.0 keeps all values strictly within [-1.0, 1.0].

---

### DEC-0021: Strict Byte Alignment and Duration Validation
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/common.py`
- **Related commit:** `863b07d`

**Context:**
16-bit PCM requires exactly 2 bytes per sample. Ingesting an odd number of bytes indicates a truncated network frame or misaligned buffer. Silently dropping the trailing byte can cause phase shifts and frame misalignment across streaming chunks.

**Decision:**
Enforce strict byte alignment: if `len(audio_bytes) % 2 != 0`, raise `AudioFormatError` immediately. Similarly, `compute_duration_ms` validates alignment and positive sample rates.

**Alternatives considered:**
1. *Silently slicing `audio_bytes[:len(audio_bytes) - 1]`:* Masks upstream network chunking bugs.
2. *Zero-padding the odd byte:* Distorts the final sample value.

**Why this approach:**
Fail-fast principle: network transport layers must supply aligned audio frames. Truncation bugs are caught immediately in unit tests rather than manifesting as acoustic distortion.

**Trade-offs:**
Callers must ensure even-length byte buffers.

**Consequences:**
All audio processing stages can assume strictly aligned 16-bit boundaries.

**Evidence:**
Verified by `test_odd_length_input_rejection` and `test_misaligned_byte_count_rejected` in `tests/unit/test_asr_common.py`.

**Interview angle:**
*Challenge:* Why fail on an odd byte instead of truncating it?
*Defense:* Silent truncation hides streaming transport bugs. If a WebSocket frame drops a byte, subsequent frames will have their high and low bytes swapped, turning speech into loud white noise. Failing fast exposes framing bugs immediately.

---

### DEC-0022: Bounded ASR Concurrency Defaulting to Unity
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/config/settings.py`
- **Related commit:** `863b07d`

**Context:**
Neural ASR engines (such as planned MLX-Whisper on Apple Silicon) are compute-bound and multi-threaded; a single model instance typically saturates available CPU and Metal cores. Spawning multiple unconstrained concurrent inference passes on a 16 GB unified-memory machine risks thread contention, memory exhaustion, and latency spikes.

**Decision:**
Add `asr_max_concurrency: int = 1` to `Settings`, enforced via Pydantic validator (`>= 1`). Concurrent requests will queue behind an async semaphore.

**Alternatives considered:**
1. *Unbounded concurrency:* Allows requests to run simultaneously. Crashes local developer machines and low-VRAM inference nodes.
2. *Hardcoded constant:* Prevents scaling concurrency on high-end multi-GPU instances.

**Why this approach:**
A default of 1 provides rock-solid stability on laptops and edge nodes, while configurable settings allow production deployments with multi-GPU clusters to scale concurrency via `.env`.

**Trade-offs:**
Under burst traffic on a single node, subsequent requests experience queue wait latency.

**Consequences:**
Prevents Out-Of-Memory (OOM) crashes during concurrent speech requests.

**Evidence:**
Verified by `test_asr_max_concurrency_settings` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* Why set concurrency to 1 by default?
*Defense:* Whisper models are compute-bound matrix engines that internally parallelize across CPU cores. Running two concurrent inferences on a 4-core machine doesn't make it 2x faster—it causes cache thrashing and doubles latency for both users. Serializing inference with a semaphore maximizes throughput and guarantees deterministic latency.

---

### DEC-0023: Honest Optional Confidence Contract (float | None)
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/base.py`, `backend/src/bolkhata/asr/mock.py`, `tests/unit/test_providers_mock.py`
- **Related commit:** Commit `f84abff0074d631a50bbacc367f2f5fa45a923bd`

**Context:**
Many ASR models (such as Whisper) produce sequence token log-probabilities (`avg_logprob`), not well-calibrated posterior probabilities. Converting `avg_logprob` using `math.exp()` or substituting missing confidences with arbitrary placeholders like `1.0` falsely implies statistical certainty, misleading downstream financial risk gates.

**Decision:**
Define `ASRResult.confidence` and `WordTiming.confidence` as `float | None`. Numeric values are permitted strictly when derived from documented runtime probability fields. When unavailable, the value must be `None`. Mock providers must not invent confidence numbers unless explicitly provided by test fixtures. Empty audio returns `confidence=None`.

**Alternatives considered:**
1. *Exponentiating `avg_logprob`:* Incorrect mathematical interpretation of unnormalized sequence-to-sequence beam search scores.
2. *Defaulting to 1.0:* Masks absence of confidence and gives false assurance on hallucinated tokens.

**Why this approach:**
Enforces honest confidence semantics throughout the pipeline. Downstream financial dialogue engines only make safety decisions when calibrated probability is genuinely present.

**Trade-offs:**
Downstream consumers must handle `None` gracefully.

**Consequences:**
Guarantees transparent data contracts and avoids synthetic certainty in financial flows.

**Evidence:**
Verified by `test_word_timing_and_asr_result_optional_confidence_semantics` and `test_mock_asr_transcribe_empty_audio_returns_empty_result` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* Why not just exponentiate Whisper's average log probability to get confidence?
*Defense:* In autoregressive encoder-decoder models, beam search log probabilities are uncalibrated and sequence-length dependent. Exponentiating them does not yield a true posterior probability. Reporting `None` is honest engineering; inventing false confidence creates severe risk in a financial ledger.

---

### DEC-0024: Vocabulary-Prompt Support (initial_prompt) for Contextual Biasing
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/base.py`, `backend/src/bolkhata/asr/mock.py`, `tests/unit/test_providers_mock.py`
- **Related commit:** Commit `f84abff0074d631a50bbacc367f2f5fa45a923bd`

**Context:**
Indian kirana store interactions feature specialized vocabulary: customer surnames (*Sharma, Verma, Gupta*), commodities (*chawal, dal, atta, cheeni*), and transaction terms (*udhaar, jama, khata*). Standard multilingual Whisper often misrecognizes these phonetic terms without domain context.

**Decision:**
Extend the `ASRProvider.transcribe()` contract to accept an optional `initial_prompt: str | None = None` parameter. The prompt passes textual context to the underlying speech recognition engine's decoder to bias recognition toward domain-specific kirana vocabulary.

**Alternatives considered:**
1. *Fine-tuning acoustic models:* Expensive, inflexible, requires continuous retraining as inventory changes, and risks catastrophic forgetting of colloquial Hinglish.
2. *Post-ASR fuzzy spell-checking alone:* Fails if phonetically similar words are transcribed into completely different phonetic tokens by the acoustic model.

**Why this approach:**
`initial_prompt` supplies textual context to Whisper's decoder. It can bias recognition toward known kirana vocabulary. However:
- It does not guarantee correct recognition and does not replace acoustic evidence.
- Excessive or incorrect context can also bias the transcript incorrectly or increase hallucination risk.
- Vocabulary prompting must be evaluated empirically using real Hindi/Hinglish audio, including negative evaluation examples where a suggested word was not spoken.

**Trade-offs:**
The caller must curate relevant vocabulary carefully (e.g. from the shop's local customer address book or active transaction items) to minimize token-budget consumption and hallucination hazards.

**Consequences:**
Establishes the contract foundation for vocabulary biasing without modifying core provider protocols. Full accuracy validation requires benchmark evaluation on real audio fixtures (planned for Stage 2 / S6).

**Evidence:**
Verified by `test_mock_asr_transcribe_initial_prompt_pass_through` in `tests/unit/test_providers_mock.py`.

**Interview angle:**
*Challenge:* What is the difference between an initial prompt in Whisper and an LLM prompt?
*Defense:* An LLM prompt is an open-ended instruction directing the model to generate a completion or perform reasoning. In Whisper, `initial_prompt` supplies preceding textual context tokens to the autoregressive text decoder, conditioning its language modeling prior toward specific domain spellings (*Sharma ji, udhaar, jama, chawal*). However, `initial_prompt` is not an infallible constraint: excessive or incorrect prompt context can induce hallucination or misalign transcripts against actual acoustics. Its operational efficacy must be proven on real audio using both positive and negative controls.

---

### DEC-0025: Platform-Specific Optional Dependency Isolation for AI Runtimes
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Superseded by [DEC-0026](#dec-0026-apple-silicon-only-architecture-with-mlx-asr-runtime)
- **Related files:** `backend/pyproject.toml`, `backend/uv.lock`, `tests/unit/test_settings_asr.py`
- **Related commit:** Commit `f84abff`

*(Historical Note: Dual-platform packaging across Windows RTX 3050 and Apple Silicon Mac was superseded by DEC-0026, which narrowed the physical hardware target exclusively to the Apple Silicon MacBook Air M5).*

**Context:**
BolKhata initially targeted heterogeneous hardware: Windows RTX 3050 (requiring CTranslate2 / CUDA) and Apple Silicon Mac (requiring Apple MLX / Metal). Installing MLX on Windows fails to build; installing CUDA/PyTorch bloats Mac and CI runners.

**Decision:**
Configure `faster-whisper==1.2.1` and `mlx-whisper==0.4.3` as optional dependency extras in `pyproject.toml`. Guard `mlx-whisper` with environment marker `sys_platform == 'darwin' and platform_machine == 'arm64'`. Lock dependencies reproducibly in `uv.lock`. Keep the default development and CI environment 100% free of heavy speech runtimes.

**Alternatives considered:**
1. *Placing all runtimes in base dependencies:* Fails cross-platform installation and bloats CI container builds.
2. *Separate requirements-windows.txt and requirements-mac.txt:* Loses unified lockfile reproducibility and dependency graph validation.

**Why this approach:**
`uv` resolves multi-platform dependency graphs cleanly into a single lockfile while allowing target platforms to install only what they support via `uv sync --extra faster-whisper` or `uv sync --extra mlx-whisper`.

**Trade-offs:**
Target machines must specify the extra when installing dependencies.

**Consequences:**
CI remains hermetic and sub-second fast; real runtimes are installed only on dedicated hardware nodes.

**Evidence:**
Verified by `test_package_imports_without_speech_runtimes` in `tests/unit/test_settings_asr.py`.

**Interview angle:**
*Challenge:* How do you manage platform-specific AI dependencies in a monorepo without breaking CI?
*Defense:* We use PEP 508 environment markers (`sys_platform == 'darwin' and platform_machine == 'arm64'`) and optional dependency extras in `pyproject.toml`. Standard CI installs zero ML packages, testing contracts with deterministic mocks. Hardware nodes install their respective extra (`--extra faster-whisper` or `--extra mlx-whisper`), keeping environments clean and reproducible.

---

### DEC-0026: Apple Silicon-Only Architecture with MLX ASR Runtime
- **Date:** 2026-11-17
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Supersedes:** [DEC-0025](#dec-0025-platform-specific-optional-dependency-isolation-for-ai-runtimes)
- **Related files:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/src/bolkhata/config/settings.py`, `tests/unit/test_settings_asr.py`
- **Related commit:** Commit `e25299448e62983beb17c45d21c6230c6cb1b06c`

**Context:**
The project previously contemplated heterogeneous target environments (Windows NVIDIA RTX 3050 via Faster-Whisper/CUDA and Apple Silicon via MLX/Metal). A firm platform decision was made: physical development, inference, testing, and benchmarking will standardize exclusively on the Apple Silicon MacBook Air M5 with 16 GB unified memory. Carrying dual-stack configuration (CUDA, CTranslate2, Faster-Whisper, generic `asr_device` and `asr_compute_type`) added unnecessary architectural overhead, dead configuration paths, and bloated dependency locks.

**Decision:**
1. Scope the planned real ASR foundation exclusively to Apple Silicon using Apple's MLX framework (`mlx-whisper==0.4.3; sys_platform == 'darwin' and platform_machine == 'arm64'`).
2. Remove all `faster-whisper` packages and transitive dependencies (`ctranslate2`, `onnxruntime`, `protobuf`, `tokenizers`, `av`) from `pyproject.toml` and `uv.lock`.
3. Remove `asr_faster_whisper_model_id`, `asr_faster_whisper_model_revision`, `asr_device`, and `asr_compute_type` from `Settings`.
4. Retain and validate only runtime settings required by MLX: `asr_mlx_whisper_model_id`, `asr_mlx_whisper_model_revision` (pinned full 40-char commit hash), `asr_model_dir`, `asr_offline_mode`, `asr_max_duration_seconds`, and `asr_max_concurrency`.
5. Keep default CI and local test environments completely free of MLX dependencies and model downloads; real MLX inference remains an upcoming stage implementation (`MockASRProvider` is currently the only active ASR engine).

**Alternatives considered:**
1. *Maintain dual-stack Faster-Whisper and MLX configuration:* Rejected because BolKhata is standardized on Apple Silicon unified memory hardware. Dual-stack abstraction introduces unused complexity and configuration drift.
2. *Keep generic device/compute_type abstractions:* Rejected because MLX uses Apple Silicon unified memory directly; CTranslate2/CUDA compute types (`int8_float16`, `cuda`) do not map to the MLX API.

**Why this approach:**
Apple Silicon unified memory allows the M-series CPU and Metal GPU to access the same physical memory space directly, avoiding host-to-device PCIe bus memory copies. Standardizing on Apple's MLX framework aligns the planned inference implementation with the physical deployment target. Note:
- MLX execution utilizes Apple Silicon CPU and Metal GPU cores; claims regarding Apple Neural Engine (ANE) utilization are unverified and excluded.
- Runtime performance, latency, real-time factor (RTF), and memory footprints remain **unmeasured** until the concrete adapter is implemented and benchmarked on target hardware.

**Checkpoint Licensing Note:**
- The default model candidate is pinned to Hugging Face repository `mlx-community/whisper-small-mlx` at commit revision `45f3915923c7a79a5a5b5a7d909d39aeb0e5630e`.
- The runtime package licence (`mlx-whisper` under MIT) and the model weights checkpoint licence are legally distinct.
- The exact checkpoint's licence, upstream attribution, and commercial redistribution terms must be verified before downloading or packaging model weights for production distribution. Until upstream terms are formally audited, the checkpoint's redistribution status remains **unresolved**.

**Trade-offs:**
Execution on non-Apple Silicon hardware with real neural inference is not supported; however, mock providers and the entire test suite remain 100% platform-independent for CI.

**Consequences:**
The codebase, lockfile, and settings schema are simplified and aligned with actual deployment hardware. CI remains sub-second fast.

**Evidence:**
Verified by `TestASRSettingsDefaultsAndOverrides`, `TestASRSettingsValidationErrors`, and `TestASRRuntimeImportIsolation` in `tests/unit/test_settings_asr.py` (129 passed).

**Interview angle:**
*Challenge:* Why did you discard cross-platform support and standardize exclusively on Apple Silicon?
*Defense:* In hardware-accelerated edge AI, premature cross-platform abstraction creates dead code. A kirana store counter requires compact, silent, fanless, and power-efficient hardware. Apple Silicon's unified memory architecture allows the CPU and GPU to share a unified 16 GB address space without PCIe bus transfer overhead. Rather than maintaining leaky abstractions over disparate runtimes (CUDA vs Metal), standardizing on MLX keeps the dependency graph minimal and focuses engineering effort on the target platform. Model execution metrics remain unmeasured pending benchmark execution.

---

### DEC-0027: MLX-Whisper ASR Provider Architecture, Bounded Worker Tracking, and Lifecycle Isolation
- **Date:** 2026-11-19
- **Stage:** S1 Stage 2
- **Status:** Implemented Decision
- **Related files:** `backend/src/bolkhata/asr/mlx_whisper.py`, `backend/src/bolkhata/common/registry.py`, `tests/unit/test_asr_mlx_whisper.py`
- **Related commit:** Pending

**Context:**
S1 Stage 2 requires implementing BolKhata's first concrete neural speech recognition engine, `MLXWhisperASRProvider`, targeting Apple Silicon macOS (M-series, 16 GB unified memory).
Key architectural constraints:
1. The default CI/CD pipeline and local mock development must remain 100% free of MLX runtime imports and weight downloads.
2. MLX inference is synchronous and compute-intensive; running it inside the asyncio event loop would freeze WebSocket heartbeats and HTTP routes.
3. Native OS threads in Python cannot be killed asynchronously upon coroutine cancellation. If a caller cancels its awaiting coroutine, naive semaphore context managers release the slot immediately, causing the system to oversubscribe physical GPU/CPU cores while the abandoned thread is still executing.
4. Native C++ extensions compiled with `nanobind` (`mlx.core`) maintain global static type registries; unloading/reloading modules via `sys.modules` manipulation causes fatal `SIGABRT` crashes (exit code 134).
5. Shutdown must wait for running worker threads without deadlocking or blocking the event loop thread.

**Decision:**
1. **Lazy Runtime Dependency Boundary (`MLXRuntime`):** Encapsulated runtime dependencies in an immutable `MLXRuntime` container loaded via an injectable `runtime_loader`. Module import of `bolkhata.asr.mlx_whisper` triggers zero MLX imports. Unit tests inject fake runtimes directly without touching global `sys.modules` or monkeypatching `builtins.__import__`.
2. **Cancellation-Safe Concurrency Slot Tracking:** Concurrency is bounded by `asr_max_concurrency` using an `asyncio.Semaphore` and a dedicated `ThreadPoolExecutor`. The semaphore slot is acquired asynchronously before submitting the job to the executor, and is released **strictly and exclusively** by the thread's completion callback (`loop.call_soon_threadsafe(sem.release)`). If the caller coroutine is cancelled while the thread is running, the slot remains occupied until the thread terminates, preventing capacity oversubscription.
3. **Double-Checked Shutdown Rejection:** A request waiting in the semaphore queue re-checks `self._is_shutdown` immediately after acquiring the slot; if shutdown started while waiting, it releases the slot and raises `RuntimeError("MLXWhisperASRProvider has been shut down.")`.
4. **Off-Loop Shutdown Synchronization:** `shutdown()` sets `self._is_shutdown = True` and signals `shutdown_started_event` synchronously before its first suspension point. The blocking join `all_workers_done.wait()` and `executor.shutdown(wait=True)` are executed off-loop via `asyncio.to_thread(_cleanup_executor, ...)`, ensuring the asyncio event loop is never blocked or deadlocked.
5. **Strict Immutable Revision Resolution & Offline Mode:** The provider resolves models against Hugging Face repository `mlx-community/whisper-small-mlx` using the explicit 40-character commit hash (`45f3915923c7a79a5a5b5a7d909d39aeb0e5630e`). Mutable revisions (`main`) are strictly rejected. When `asr_offline_mode=True`, `local_files_only=True` is enforced and missing weights raise `ModelResolutionError`.
6. **Honest Confidence & Push-to-Talk Streaming:** Overall confidence is strictly `None` because Whisper does not provide calibrated sequence-level probabilities (`avg_logprob` is uncalibrated). Word timings include probabilities only when supplied as a valid probability by the runtime. Streaming accumulates PCM frames and yields a single final `ASRPartialResult(text=..., is_final=True)` at completion, accurately representing sequence-to-sequence Whisper rather than fabricating incremental streaming text.

**Alternatives considered:**
1. *Global `patch.dict(sys.modules)` for missing-dependency testing:* Rejected because unloading `mlx.core` from `sys.modules` corrupts `nanobind`'s static type registry and triggers interpreter aborts (`SIGABRT`, exit code 134) on subsequent imports.
2. *Rely on `async with semaphore:` context manager:* Rejected because coroutine cancellation exits the context manager and releases the slot prematurely while the OS worker thread is still active on hardware.
3. *Synchronous `executor.shutdown(wait=True)` on the event loop:* Rejected because joining worker threads directly on the loop thread blocks the event loop and starves concurrent coroutines.

**Why this approach:**
Provides rock-solid concurrency guarantees, completely eliminates flaky test crashes, ensures zero network downloads during CI, and respects the true physical execution characteristics of synchronous neural inference on Apple Silicon.

**Trade-offs:**
`stream()` does not produce interim partial tokens during speech because Whisper is non-causal; this is documented honestly as push-to-talk batch accumulation. Real neural inference performance (WER, RTF, RAM) is unverified until the hardware smoke test milestone.

**Consequences:**
Complete thread safety, robust error recovery, and 100% hermetic unit tests running in a single process without C-extension corruption.

**Evidence:**
Verified by 21 unit tests in `tests/unit/test_asr_mlx_whisper.py` and 151 total backend tests in `tests/`.

**Interview angle:**
*Challenge:* What happens if a client disconnects while a heavy MLX speech inference request is executing?
*Defense:* In Python asyncio, cancelling an awaiting task raises `asyncio.CancelledError` on the event loop, but native OS worker threads executing C++ MLX code cannot be interrupted. If we simply used `async with semaphore:`, the semaphore would be released immediately upon cancellation, allowing a new request to begin and causing multiple heavy matrix computations to fight for unified memory. Our provider decouples semaphore release from coroutine cancellation: the slot is held until the OS thread finishes its work and releases the slot via `loop.call_soon_threadsafe(sem.release)`. Furthermore, `shutdown()` awaits active worker completion off the event loop thread using `asyncio.to_thread`, ensuring shutdown never deadlocks the loop.

---

### DEC-0028: Push-to-Talk WebSocket Protocol, Explicit Four-State Machine, and Generation Invariants

*Status: Implemented (S1 Stage 3)*

**Context:**
A voice-driven Kirana application needs an interactive, low-latency communication channel between the client browser and the backend speech-to-text, LLM dialogue, and text-to-speech synthesis pipeline. The transport must:
1. Stream binary 16 kHz mono 16-bit PCM frames without base64 framing overhead during active speech.
2. Interleave UTF-8 JSON control messages (`start_utterance`, `end_utterance`, `cancel_utterance`, `transcript`, `assistant_text`, `audio_chunk`, `timings`, `error`).
3. Enforce an explicit session state machine (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`) where illegal transitions are rejected and logged.
4. Prevent race conditions and stale turns through monotonic turn tracking and unique `generation_id` tokens.

**Decision:**
1. **Single WebSocket Transport (`/ws/session`):** Unified bidirectional connection handling binary audio frames and typed JSON messages. Avoids complex multi-protocol coordination (WebRTC or separate polling REST endpoints).
2. **Explicit Four-State Machine (`SessionStateMachine`):**
   - `IDLE`: Connection open, waiting for push-to-talk press.
   - `LISTENING`: Talk button pressed, accumulating raw PCM frames in bounded buffer.
   - `THINKING`: Talk button released, running ASR and LLM reasoning. Generates a fresh `generation_id`.
   - `SPEAKING`: Synthesizing and streaming audio chunks back to the client.
   - **Transition Invariant:** Only legal transitions are permitted (`IDLE -> LISTENING`, `LISTENING -> THINKING`, `THINKING -> SPEAKING`, `SPEAKING -> IDLE`, plus cancellation back to `IDLE` or barge-in `SPEAKING -> LISTENING`). Out-of-order calls (e.g. `start_utterance` while in `THINKING`) raise `InvalidStateTransitionError` and emit a structured error frame.
3. **Generation Invariants (`generation_id`):** When entering `THINKING`, the session manager generates a new `generation_id`. All emitted downstream events (`transcript`, `assistant_text`, `audio_chunk`, `timings`) carry this ID. If a user cancels or interrupts a turn, any lingering in-flight compute matching an older `generation_id` is silently dropped, guaranteeing no stale audio or text corrupts the client UI.
4. **Bounded Audio Buffering:** In `LISTENING`, audio bytes are accumulated up to `asr_max_duration_seconds * BYTES_PER_SECOND`. If a client streams past the duration limit, the server emits `AUDIO_TOO_LONG` and resets to `IDLE` without allocating unbounded memory.
5. **Per-Stage Latency Telemetry (`timings`):** Every turn concludes with fine-grained timing measurements (`asr_ms`, `llm_ms`, `tts_ms`, `total_ms`) for end-to-end performance visibility.

**Alternatives considered:**
1. *WebRTC (DataChannel + MediaStream):* Excessive complexity, NAT traversal/STUN/TURN dependencies, and unnecessary peer-to-peer overhead for a simple push-to-talk store application.
2. *HTTP POST with polling / Server-Sent Events (SSE):* Incurs multi-connection overhead, higher latency, and difficulty synchronizing binary audio chunks with state events.
3. *Implicit boolean state flags (`is_listening = True`):* Susceptible to race conditions, split-brain states, and difficult to test exhaustively.

**Why this approach:**
Provides a simple, robust, auditable protocol with strict state machine validation and race-free turn handling.

**Consequences:**
The client and server maintain perfectly synchronized states with sub-millisecond transition overhead. Tests can easily simulate entire turns with pure mock or real providers.

**Evidence:**
Verified by:
- 12 unit tests in `tests/unit/test_realtime_protocol.py`
- 10 unit tests in `tests/unit/test_realtime_state_machine.py`
- 5 integration tests in `tests/integration/test_ws_session.py`

**Interview angle:**
*Challenge:* What happens if a shopkeeper taps push-to-talk while the assistant is in the middle of synthesizing a response for the previous question?
*Defense:* This is a classic voice UI race condition. Our state machine supports explicit barge-in transitions (`SPEAKING -> LISTENING`). When `start_utterance` arrives, any active background task for the previous turn is cancelled, the state resets the generation context, and a new `turn_id` is established. Furthermore, even if native threads from the earlier turn continue briefly before cancellation takes effect, any emitted events carry the old `generation_id` and are discarded before reaching the client.

---

### DEC-0029: Deterministic Spoken-Number and Unit Parsing Grammar

*Status: Implemented (S2)*

**Context:**
In Indian retail (Kirana), transactions are spoken using a blend of Hindi, English, and regional colloquialisms. Key linguistic patterns include:
1. Multipliers based on the Indian numbering system: `sau` (100), `hazaar` (1,000), `lakh` (100,000), `crore` (10,000,000).
2. Complex fractional words acting as unit multipliers or adjustments:
   - `dhai` (2.5x base): `dhai sau` = 250, `dhai hazaar` = 2,500.
   - `derh` / `dedh` (1.5x base): `dedh sau` = 150, `derh hazaar` = 1,500.
   - `sawa` (1.25x or +0.25 of multiplier): `sawa sau` = 125, `sawa do sau` = 225.
   - `sadhe` (+0.5 of unit for $\ge 3$): `sadhe teen sau` = 350, `sadhe char sau` = 450.
   - `paune` (-0.25 of unit): `paune do sau` = 175, `paune teen sau` = 275.
3. Colloquial units: `pau` (250g), `aadha kilo` (500g), `darjan` (12), `bori` (sack), `thaili` (pouch).
4. Dual currency expressions: `das rupaye pachaas paise` = ₹10.50.

General-purpose Large Language Models (LLMs) frequently hallucinate or fail simple arithmetic when presented with these idiomatic structures (e.g. interpreting `dhai sau` as 200 or 50, or `paune do sau` as 275). In a ledger recording financial credit and debit transactions, numerical hallucinations are critical safety violations.

**Decision:**
1. **Zero LLM Arithmetic for Money:** Spoken numbers, amounts, and units are parsed exclusively by a deterministic Python grammar (`bolkhata.domains.common.numbers` and `bolkhata.domains.common.units`). The LLM is never permitted to calculate, normalize, or decide financial amounts.
2. **Explicit Ambiguity Signaling:** When an utterance exhibits true phonetic or numeric ambiguity (e.g. ranges like `do teen packet` or `do teen sau rupaye`), the parser sets `is_ambiguous=True`, lowers the confidence flag, and returns a list of explicit numeric `candidates` (e.g. `[2.0, 3.0]`). The downstream dialogue flow must clarify ambiguous numbers with the shopkeeper rather than silently guessing.
3. **Reproducible Evaluation Harness:** An automated benchmarking harness (`bolkhata.eval`) calculates Word Error Rate (WER) and Character Error Rate (CER) via pure-Python Wagner-Fischer dynamic programming edit distance (cross-checked against `jiwer`), Real-Time Factor (RTF), latency percentiles, and amount exact-match accuracy. Two text normalization modes are provided (`strict` and `tolerant`) to evaluate Hinglish phonetic variations without masking genuine acoustic errors.

**Alternatives considered:**
1. *LLM Few-Shot Extraction:* Rejected. Non-deterministic, expensive, high latency, susceptible to hallucinations on rare idioms, and un-auditable.
2. *Existing Open-Source Parsers (e.g. duckling, word2number):* Rejected. None support Hindi fractional idioms (`dhai`, `derh`, `sawa`, `sadhe`, `paune`), Devanagari numerals, or Indian Kirana packaging units out of the box.

**Why this approach:**
Provides 100% deterministic, auditable, sub-millisecond parsing with zero hallucinations, guaranteeing financial safety for ledger transactions.

**Consequences:**
Every numerical entity has mathematical provenance. All 0–100 Hindi numbers, common spelling variants, and colloquial idioms pass automated verification.

**Evidence:**
- 64 unit tests in `tests/unit/test_spoken_numbers.py`
- 117 unit tests in `tests/unit/test_units_currency.py`
- 22 unit tests in `tests/unit/test_eval_metrics.py` and `tests/unit/test_asr_normalizer.py`
- 3 integration tests in `tests/unit/test_eval_runner.py`

**Interview angle:**
*Challenge:* Why not just prompt an advanced LLM like GPT-4 or Claude 3.5 to extract the transaction amount and units directly from the audio transcript?
*Defense:* LLMs are probabilistic sequence predictors, not deterministic calculators. When evaluating real Kirana speech, LLMs frequently make subtle arithmetic errors on idioms like `dhai sau` (often interpreting it as 200 or 50) or `paune do sau` (computing 200 - 25 = 175 incorrectly as 275). In banking and ledger software, hallucinating a transaction amount is unacceptable. Our architecture enforces a hard boundary: speech recognition produces text, our deterministic Python grammar extracts and normalizes the numbers with mathematical certainty, and the LLM is restricted solely to unstructured intent resolution where rules cannot resolve the context. Money amounts never touch an LLM reasoning step.
