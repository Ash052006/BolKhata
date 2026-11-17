# BolKhata (बोलखाता) — Living Engineering Progress & Interview Guide

> **Document Type:** Living Architecture, Engineering Journal & Technical Interview Preparation Guide
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)
> **Last Updated:** Sprint S1 Stage 2 (Prompt 1)
> **Active Branch:** `feat/s1-provider-foundation`
> **Latest Commit:** `863b07d22635c1cc8b2942798b66e4366cea7298`

---

## Maintenance Invariant (Read Before Editing)

This is a **living engineering document** for BolKhata. It captures the project's evolution, technical rationale, architecture decisions, and interview preparation.

Whenever an implementation prompt or sprint is completed:
1. **Update the Status Table:** Update Section B and Section G with the newly completed tasks.
2. **Append Chronological Log:** Add a subsection to Section C explaining what was built, why, how it works, bugs found, and how they were solved.
3. **Add New Interview Questions:** Add new relevant questions and deep dives to Section F reflecting the newly written code and challenges encountered.
4. **Update Metrics & Evidence:** Update Section H with exact test counts, gate results, and verified Git commit SHAs.
5. **Differentiate Statuses:** Never mark planned components as completed. Keep planned, partial, and implemented components strictly distinct.

---

## Table of Contents

- [Section A — Project Overview](#section-a--project-overview)
  - [Problem Statement & Kirana Context](#problem-statement--kirana-context)
  - [Why Voice-First Interaction?](#why-voice-first-interaction)
  - [Target Users & Multilingual Reality](#target-users--multilingual-reality)
  - [Intended User Journey](#intended-user-journey)
  - [End-to-End System Architecture](#end-to-end-system-architecture)
- [Section B — Overall Roadmap & Progress](#section-b--overall-roadmap--progress)
  - [Milestones (S0 to S6)](#milestones-s0-to-s6)
  - [Feature Tiers & Priority Cut Line](#feature-tiers--priority-cut-line)
- [Section C — Detailed Implementation History](#section-c--detailed-implementation-history)
  - [Sprint S0: Production-Ready Foundation](#sprint-s0-production-ready-foundation)
  - [S0 Tooling & Secret-Scanning Remediation](#s0-tooling--secret-scanning-remediation)
  - [S1 Stage 1: Provider Interfaces & Registry](#s1-stage-1-provider-interfaces--registry)
  - [S1 Stage 1: Lifecycle Hardening & Ordering Fixes](#s1-stage-1-lifecycle-hardening--ordering-fixes)
  - [S1 Stage 2 (Prompt 1): Audio Utilities & Shared ASR Settings](#s1-stage-2-prompt-1-audio-utilities--shared-asr-settings)
- [Section D — Important Architecture Decisions (ADRs)](#section-d--important-architecture-decisions-adrs)
- [Section E — Current Architecture & Code Map](#section-e--current-architecture--code-map)
- [Section F — Technical Interview Preparation](#section-f--technical-interview-preparation)
  - [1. Architecture & System Design](#1-architecture--system-design)
  - [2. Python & Asynchronous Programming](#2-python--asynchronous-programming)
  - [3. AI & Speech Processing](#3-ai--speech-processing)
  - [4. Backend, Databases & Money Safety](#4-backend-databases--money-safety)
  - [5. Reliability, Security & Data Protection](#5-reliability-security--data-protection)
  - [6. Testing, CI/CD & Engineering Workflow](#6-testing-cicd--engineering-workflow)
  - [7. Project-Specific Deep Dives](#7-project-specific-deep-dives)
- [Section G — Current Status & Next Steps](#section-g--current-status--next-steps)
- [Section H — Metrics & Verified Evidence](#section-h--metrics--verified-evidence)
  - [Verified Gate Results](#verified-gate-results)
  - [Verified Git Commit History](#verified-git-commit-history)

---

## Section A — Project Overview

### Problem Statement & Kirana Context
In India, millions of micro-merchants (kirana stores, tea stalls, local grocers) manage daily credit (*udhaar*) using paper notebooks called *Bahi-Khata*. While digital ledger apps (Khatabook, OkCredit) exist, manual typing on a smartphone screen remains a major friction point during busy store hours. A shopkeeper with dusted hands weighing lentils or attending multiple customers cannot afford to unlock a phone, search for a customer name, open a numeric keyboard, type ₹250, and tap save.

As a result, transactions are either scribbled down hours later (leading to forgotten debts) or recorded on loose scraps of paper that get misplaced.

### Why Voice-First Interaction?
Voice is the most natural, zero-touch interface for a shopkeeper. However, traditional voice assistants (Siri, Alexa, Google Assistant) fail kirana stores for three critical reasons:
1. **Language & Dialect Mix:** Shopkeepers speak code-switched Hindi-English (*Hinglish*) and regional colloquialisms (e.g., *"Sharma ji ko dhai sau udhaar"*).
2. **Acoustic Noise & High Stakes:** Kirana stores are loud (traffic, ceiling fans, chatter). A misrecognized monetary amount is not an annoyance; it is a financial loss.
3. **Unreliable Connectivity:** Local mobile data drops frequently in congested markets. An app that hangs when the internet cuts out cannot be trusted with a merchant's cash flow.

**BolKhata** solves this by offering a **push-to-talk, speech-driven, money-safe ledger**. The merchant speaks naturally, the system deterministically parses numbers and entities, reads back the parsed entry for explicit verbal confirmation, and commits an append-only ledger transaction.

### Target Users & Multilingual Reality
- **Primary Users:** Kirana store owners, vegetable vendors, and local retail merchants.
- **Language Requirements:**
  - **Hindi (Devanagari / Romanized):** Traditional Indian number forms (*dhai sau*, *dedh hazaar*, *pachaas*).
  - **Indian English:** Colloquial terms (*two-fifty*, *hundred bucks*, *credit*).
  - **Hinglish (Code-Switched):** Blended sentence structures (*"Verma ji 500 rupees udhaar on rice"*).

### Intended User Journey
1. **Push-to-Talk (PTT):** The merchant holds a single screen button or hardware key and speaks:
   > *"Sharma ji ko dhai sau udhaar, aur do kilo chawal."*
2. **Audio Capture:** Raw 16 kHz mono signed 16-bit PCM is buffered via browser `AudioWorklet`.
3. **Fast Speech Recognition (ASR):** Speech is converted to raw text tokens.
4. **Domain & Deterministic Extraction:**
   - **Deterministic Number Parser:** Evaluates *"dhai sau"* to exactly `250.00`. Never delegated to probabilistic LLMs.
   - **Entity Extraction:** Matches *"Sharma ji"* against local customer records; categorizes *"chawal"* as item detail.
5. **Spoken Read-Back & Confirmation:**
   > System speaks: *"Sharma ji, do sau pachaas rupaye udhaar, do kilo chawal. Sahi hai?"*
6. **Verbal Confirmation:**
   - Merchant says: *"Haan"* (or taps confirm) $\rightarrow$ Transaction committed.
   - Merchant says: *"Nahi, teen sau"* $\rightarrow$ Voice correction applied.
7. **Append-Only Persistence:** SQLite / PostgreSQL ledger updated with immutable transaction and idempotency keys.

### End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client (Frontend PWA)"]
        MIC["Microphone Capture<br/>(AudioWorklet)"]
        UI["Push-to-Talk UI<br/>(React + Vite)"]
        SPEAKER["Audio Output<br/>(PCM Playback)"]
    end

    subgraph Transport ["Realtime Transport"]
        WS["WebSocket Stream<br/>(Binary PCM + JSON Events)<br/><i>[Planned - S1/S4]</i>"]
    end

    subgraph BackendGateway ["FastAPI Application"]
        ROUTER["API Router & Lifespan<br/>(app.py / health.py)<br/><b>[Implemented - S0]</b>"]
        REGISTRY["Provider Registry<br/>(registry.py)<br/><b>[Implemented - S1]</b>"]
    end

    subgraph SpeechPipeline ["Speech & Audio Layer"]
        COMMON["Audio Utils & Settings<br/>(16kHz s16le PCM to float32)<br/><b>[Implemented - S1]</b>"]
        ASR["ASR Provider<br/>(Mock <b>[Done]</b> / Faster-Whisper, MLX <i>[Planned]</i>)"]
        VAD["VAD Provider<br/>(Mock <b>[Done]</b> / Silero <i>[Planned]</i>)"]
        TTS["TTS Provider<br/>(Mock <b>[Done]</b> / Piper, Edge <i>[Planned]</i>)"]
    end

    subgraph CoreEngine ["Domain & Intelligence Layer"]
        NUM_PARSER["Deterministic Spoken-Number Parser<br/>(Hindi / Hinglish / English)<br/><i>[Planned - S2]</i>"]
        LLM["LLM Provider<br/>(Mock <b>[Done]</b> / Local or API <i>[Planned]</i>)"]
        DOMAIN["DomainPack & Ledger Extractor<br/>(Customer & Item Resolution)<br/><i>[Planned - S3]</i>"]
    end

    subgraph Storage ["Persistence Layer"]
        DB[("Database Engine<br/>Async SQLite / PostgreSQL<br/><b>[Implemented - S0]</b>")]
        LEDGER["Append-Only Ledger Tables<br/>(Compensating Entries & Idempotency)<br/><i>[Planned - S3]</i>"]
    end

    MIC -->|Raw Audio (16kHz s16le)| WS
    WS --> ROUTER
    ROUTER --> REGISTRY
    REGISTRY --> COMMON
    COMMON --> ASR
    ASR --> NUM_PARSER
    ASR --> LLM
    NUM_PARSER --> DOMAIN
    LLM --> DOMAIN
    DOMAIN --> LEDGER
    LEDGER --> DB
    DOMAIN -->|Read-back Text| TTS
    TTS -->|Synthesized PCM| WS
    WS --> SPEAKER
```

---

## Section B — Overall Roadmap & Progress

The project schedule follows the master roadmap outlined in `bolkhata-agent-prompts.md`.

### Milestones (S0 to S6)

| Stage | Objective | What We Do | Why It Matters | Status |
|---|---|---|---|---|
| **S0** | **Production Foundation** | Monorepo layout, FastAPI factory, async DB (SQLite/Postgres), health/readiness probes, structured logging with PII redaction, Docker Compose, CI, strict Ruff/mypy gates. | Eliminates technical debt early; establishes verifiable engineering baselines before introducing non-deterministic ML models. | **Completed** |
| **S1** | **Provider Foundation & ASR Adapter** | Abstract provider interfaces (`ASR`, `TTS`, `LLM`, `VAD`), deterministic offline mocks, thread-safe DI registry with lifecycle rollbacks, 16kHz PCM utilities, Faster-Whisper and MLX-Whisper adapters, push-to-talk WebSocket slice. | Allows rapid model swapping across Mac (Metal) and PC (CUDA); enables 100% offline, deterministic CI testing without downloading heavy weights. | **In Progress**<br/>*(Interfaces, Registry, Mocks & Audio Utils Completed)* |
| **S2** | **Spoken-Number Parser & Evaluation Harness** | Deterministic number parser for Hindi/Hinglish numeric idioms (*dhai sau*, *dedh hazaar*), ground-truth audio test corpus, Word Error Rate (WER) and number extraction accuracy evaluation harness. | **Money safety:** Large language models hallucinate and fail at Indian colloquial arithmetic. Deterministic parsing guarantees mathematical correctness. | **Planned** |
| **S3** | **DomainPack & Ledger Extraction** | Pluggable DomainPack protocol, kirana transaction extraction schema, customer name entity resolution, append-only ledger schema, idempotency tokens. | Decouples speech pipeline from business logic; guarantees immutable financial audit trails and prevents double-posting. | **Planned** |
| **S4** | **Read-Back, Correction & Failure Handling** | Verbal confirmation loop, state machine (IDLE, LISTENING, THINKING, SPEAKING), voice-driven transaction corrections, network failure and audio recovery flows. | Kirana shops cannot afford silent transcription mistakes; explicit verbal read-back ensures merchant trust and operational resilience. | **Planned** |
| **S5** | **Frontend PWA, Offline Fallback & Benchmarks** | React PWA with AudioWorklet capture, offline local-LLM fallback, hardware latency/memory profiling (Apple Silicon Mac vs Windows RTX 3050). | Delivers snappy zero-latency push-to-talk UX and empirically validates performance against latency budgets on target hardware. | **Planned** |
| **S6** | **Evidence, Documentation & Release Freeze** | Complete benchmarking documentation, reproducible demo script, final test freeze, project release tag. | Provides verifiable proof of system performance, accuracy, and operational claims for hackathon evaluation and production readiness. | **Planned** |

### Feature Tiers & Priority Cut Line

To balance ambitious capabilities with strict delivery timelines, features are tiered into strict priority bands:

- **Must-Have (Core Invariants — Non-negotiable):**
  - **F1 (Vocabulary Biasing):** Bias ASR toward kirana customer names, commodity terms (*chawal*, *dal*, *atta*), and transaction words (*udhaar*, *jama*).
  - **F2 (Spoken Balance Queries):** Support instant verbal balance inquiries (*"Sharma ji ka kitna baaki hai?"*).
  - **F6 (Data Ownership & Export):** Zero vendor lock-in; one-click local SQLite backup and CSV/PDF export.
  - **F7 (Pilot Instrumentation):** Granular structured metrics (PTT-to-transcript latency, extraction accuracy, user confirmation rate) without logging PII.
- **Should-Have (High Value — Implement After Musts Pass):**
  - **F3 (Debt Ageing & Daily Digest):** Automated calculation of overdue credit (*"30 din purana udhaar"*) and evening settlement summaries (*"Aaj ka hisaab"*).
  - **F4 (WhatsApp Reminder Drafts):** Generate pre-filled, polite payment reminder messages in Hindi/English ready for shopkeeper dispatch.
  - **F5 (Explainability Panel):** Visual diagnostic panel displaying raw transcript, confidence scores, and entity resolution breakdown.
- **Could-Have (Bonus Features — Subject to Cut Order):**
  - **F8 (Second Language):** Add support for Tamil, Telugu, or Marathi.
  - **F9 (Local-First Synchronization):** Multi-device peer sync across local Wi-Fi.
  - **F10 (Open Spoken-Amount Benchmark):** Public open-source dataset and benchmark runner for Indian spoken currency phrases.

> **Cut Order if Constrained:** (1) Remote RTX inference node $\rightarrow$ (2) Offline local-LLM fallback $\rightarrow$ (3) Frontend visual polish $\rightarrow$ (4) Spoken TTS audio (retaining visual on-screen read-back) $\rightarrow$ Could-Haves $\rightarrow$ Should-Haves.
> **Never Cut:** Number parser tests, benchmark numbers, explicit read-back confirmation, failure handling, and append-only ledger safety.

---

## Section C — Detailed Implementation History

### Sprint S0: Production-Ready Foundation
*Commits: `bd11710` (initial baseline), `8aa8415` (secret scanner safe fixtures)*

Before integrating machine learning frameworks, we established an enterprise-grade backend and frontend baseline. Building foundational infrastructure first prevents compounding architectural debt.
- **Monorepo Layout:** Clean split between `backend/` (FastAPI, Python 3.11, `uv`) and `frontend/` (React 18, TypeScript, Vite 6, Tailwind CSS).
- **Application Factory Pattern:** `bolkhata.api.app:create_app()` dynamically instantiates FastAPI, binding routes, lifespan events, and configuration.
- **Liveness & Readiness Probes:**
  - `GET /health`: Instantaneous liveness check returning status and service metadata.
  - `GET /ready`: Async database connectivity check via `SELECT 1`. If the database is unreachable, returns HTTP 503 Service Unavailable with JSON error payloads.
- **Settings & Environment Management:** Strictly typed Pydantic v2 `BaseSettings` (`bolkhata.config.settings:Settings`) reading from `.env`. Validates database URLs, logging levels, and provider configurations at boot.
- **Async Database Architecture:** SQLAlchemy 2.0 with async engine (`sqlite+aiosqlite://` for local zero-dependency development; `postgresql+asyncpg://` via Docker Compose profile). WAL mode (`PRAGMA journal_mode=WAL`) is automatically enabled for SQLite during lifespan startup to maximize concurrent read/write throughput.
- **Alembic Migrations:** Async migration runner (`backend/alembic/env.py`) verified by an automated smoke test (`tests/integration/test_alembic_smoke.py`) that executes a complete `upgrade head` and `downgrade base` cycle.
- **PII Redaction in Structured Logging:** Custom JSON log formatter (`bolkhata.common.logging:StructuredJsonFormatter`) that recursively scrubs customer names, phone numbers, API keys, passwords, and tokens across log dictionaries and nested exception tracebacks. Tested thoroughly in `tests/unit/test_logging_redaction.py`.
- **Quality Gates:** Complete automated CI pipeline with Ruff linting, Ruff formatting, strict Mypy type-checking, pre-commit hooks, and Docker Compose single-command orchestration (`docker compose up --build`).

### S0 Tooling & Secret-Scanning Remediation
*Commits: `8aa8415` (scanner-safe fixtures), `fe97621` (reproducible pre-commit), `e1cf4a9` (baseline lint cleanup)*

During early development, automated pre-commit hooks triggered false positives and environment discrepancies:
1. **Synthetic Secret Detection:** `detect-secrets` flagged synthetic test tokens used to verify PII redaction (`test_token_1234567890abcdef`). Disabling secret detectors was rejected as an unacceptable security risk. Instead, exact line-level exclusions were added to `.secrets.baseline` using the tool's sanctioned audit mechanism.
2. **Pre-commit Reproducibility:** Pre-commit hooks initially invoked system-level tools with drifting versions. Configuration was pinned explicitly to `backend/.venv` using `repo: local` hooks, guaranteeing identical execution across macOS, Linux, and CI runners.
3. **Strict JSON Parsing in Tooling:** `frontend/tsconfig.json` contained JavaScript-style comments (`//`), causing standard JSON linters to fail. Comments were removed to adhere to strict RFC 8259 JSON specifications.
4. **Historical Ruff Test Linting:** Legacy test files had minor Ruff rule violations (PT018 for composite assertions, PT006 for tuple parameterization). These were resolved in an isolated commit (`e1cf4a9`) to maintain clean, auditable Git history without mingling with feature code.

> **Engineering Takeaway:** Quality gates should be reproducible and never bypassed or disabled to achieve a passing build. If a gate produces false positives, solve it using documented, audited allowlists or code restructuring.

### S1 Stage 1: Provider Interfaces & Registry
*Commits: `96b2b52` (contracts and mock registry), `687385c` (lifecycle hardening)*

To guarantee that BolKhata can run on developer laptops, resource-constrained cloud VMs, or edge devices without modifying business logic, all AI subsystems are hidden behind abstract contracts:
- **`ASRProvider` (`bolkhata.asr.base`):** Asynchronous speech-to-text contract supporting both one-shot `transcribe(audio_bytes)` and chunked streaming `transcribe_stream(audio_chunks)`. Returns an immutable `ASRResult` containing text, language, confidence, and tuple of `WordTiming`.
- **`TTSProvider` (`bolkhata.tts.base`):** Synthesizes text into raw PCM audio chunks (`synthesize` and `stream_synthesize`).
- **`LLMProvider` (`bolkhata.llm.base`):** Asynchronous chat completion supporting conversational streaming (`stream_chat`) and deterministic structured JSON output (`complete_structured`).
- **`VADProvider` (`bolkhata.asr.vad`):** Voice activity detection segmenting raw audio into speech/silence boundaries.
- **Deterministic Mock Implementations:** CI and local testing must never download multi-gigabyte neural weights or make external cloud calls. Mocks (`MockASRProvider`, `MockTTSProvider`, `MockLLMProvider`, `MockVADProvider`) return deterministic, valid data (e.g., generating valid sine-wave PCM audio rather than dummy empty bytes).
- **Dependency Injection Provider Registry (`bolkhata.common.registry:ProviderRegistry`):** Reads settings, instantiates configured providers, manages concurrency locks, and provides a unified async lifecycle (`initialize()`, `warmup()`, `shutdown()`).

#### Illustrative Provider Abstraction Example
The following snippet illustrates how application services depend only on abstract interfaces, allowing seamless provider substitution:

```python
# Illustrative example of dependency injection via ProviderRegistry
from bolkhata.asr.base import ASRProvider, ASRResult
from bolkhata.common.registry import ProviderRegistry
from bolkhata.config.settings import Settings

async def transcribe_audio(registry: ProviderRegistry, audio_pcm: bytes) -> str:
    # Service requests the active ASR provider without knowing whether it is
    # MockASRProvider, FasterWhisperASRProvider, or MLXWhisperASRProvider
    asr: ASRProvider = registry.get_asr()
    result: ASRResult = await asr.transcribe(audio_pcm)
    return result.text
```

### S1 Stage 1: Lifecycle Hardening & Ordering Fixes
*Commits: `687385c` (lifecycle hardening), `516e03a` (retry-order fix)*

During thorough edge-case testing of the `ProviderRegistry`, five subtle lifecycle bugs were identified and eliminated:
1. **Late Tracking on Startup Rollback:** Previously, a provider was only appended to `_initialized_providers` after both `initialize()` and `warmup()` succeeded. If `warmup()` raised an exception, previously initialized state was orphaned without cleanup. **Fix:** Track providers immediately upon successful `initialize()`, guaranteeing rollback on warmup failure.
2. **Inference Cancellation Clarification:** Documentation previously implied that cancelling an asyncio task would immediately terminate running native C++ inference. **Correction:** Documented that cancelling an `asyncio.to_thread()` coroutine abandons the awaiting task on the event loop, but the underlying OS thread runs to completion.
3. **Structured Mock Hallucination:** `MockLLMProvider.complete_structured` previously fabricated arbitrary values for unknown Pydantic schemas. For financial ledger schemas, this violated money-safety invariants. **Fix:** Require explicit pre-configured test fixtures for structured output; missing fixtures fail closed with a clear error.
4. **Cleanup Retry Ordering Bug:** In `ProviderRegistry.shutdown()`, providers that failed cleanup were removed from tracking and appended to a retry list. If multiple providers failed, their retry order became unpredictable.
5. **Canonical Startup Invariant Solution:**
   - **Canonical Startup Order:** ASR $\rightarrow$ TTS $\rightarrow$ LLM $\rightarrow$ optional VAD.
   - **Canonical Shutdown Order:** VAD $\rightarrow$ LLM $\rightarrow$ TTS $\rightarrow$ ASR (exact reverse order).
   - Identity-based tracking (`list[BaseProvider]`) now retains original startup order across failed cleanup retries. Tests in `tests/unit/test_providers_mock.py` prove that even under partial cleanup exceptions, subsequent shutdown calls execute in strict reverse-startup sequence.

### S1 Stage 2 (Prompt 1): Audio Utilities & Shared ASR Settings
*Commit: `863b07d` (PCM utilities and ASR settings)*

Before implementing concrete speech recognition engines (Faster-Whisper and MLX-Whisper), we established a shared, high-performance audio standard:
- **Audio Format Specification:**
  - Sample Rate: `16,000 Hz` (`SAMPLE_RATE_HZ`)
  - Channels: `1` Mono (`CHANNELS`)
  - Sample Format: Signed 16-bit little-endian raw PCM (`BYTES_PER_SAMPLE = 2`)
- **Memory-Efficient PCM-to-Float32 Conversion:**
  Neural ASR models expect floating-point inputs normalized to the range $[-1.0, 1.0]$. We implemented `pcm_to_float32(audio_bytes: bytes) -> array.array[float]` in `backend/src/bolkhata/asr/common.py`.
  - **Zero-Dependency Standard Library Implementation:** Built using Python's standard-library `array` module (`array.array("h")` and `array.array("f")`). Avoids forcing NumPy as a hard dependency in minimal environments.
  - **Normalization Boundaries:** Maps $-32768$ exactly to $-1.0$ and $+32767$ to $32767 / 32768.0 \approx +0.99997$.
  - **Endianness Safety:** Detects system byte order (`sys.byteorder`) and automatically performs `raw_samples.byteswap()` on big-endian hosts, guaranteeing uniform little-endian interpretation.
  - **Input Validation:** Empty byte strings return empty float arrays; misaligned odd-length byte buffers raise a structured `AudioFormatError`.
- **Duration Calculation:** `compute_duration_ms(byte_count, sample_rate)` computes exact audio duration in milliseconds, enforcing alignment and positive sample rates.
- **ASR Concurrency Bounds:** Added `asr_max_concurrency: int = 1` in `Settings`. Local ASR models (CTranslate2 / MLX) saturate CPU/GPU cores during inference; allowing unbounded concurrent calls causes severe thread contention and out-of-memory crashes. The safe default of 1 ensures serialized execution unless explicitly scaled.

#### Illustrative PCM Conversion Example
```python
# Illustrative snippet of bolkhata.asr.common.pcm_to_float32
import array
import sys

def pcm_to_float32(audio_bytes: bytes) -> array.array[float]:
    raw_samples = array.array("h")
    raw_samples.frombytes(audio_bytes)
    if sys.byteorder != "little":
        raw_samples.byteswap()
    # Normalize signed 16-bit integer to float32 in [-1.0, 1.0]
    return array.array("f", (s / 32768.0 for s in raw_samples))
```

### Documentation Milestone: Permanent Engineering Knowledge Base & Deep-Dive Manuals
*Commits: `b065ab8`, `b6b7461`, `b261680`*

To preserve engineering rationale, accelerate onboarding, and provide comprehensive interview defense materials, we created a four-pillar documentation knowledge base under `docs/`:
1. [docs/README.md](README.md): Documentation index, navigation guide, and source-of-truth precedence hierarchy.
2. [docs/decision.md](decision.md): Central architectural decision log detailing context, choices, alternatives rejected, trade-offs, consequences, and interview defense angles.
3. [docs/architecture-deep-dive.md](architecture-deep-dive.md): Exhaustive technical reference detailing internal component mechanics, sequence flows, state machines, provider registry rollbacks, float32 audio normalization math, and failure recovery matrices.
4. [docs/interview-guide.md](interview-guide.md): In-depth interview defense manual featuring 30s/1m/3m/5m pitches, grounded answers for technical questions, walkthroughs of critical interviewer challenges, and preparation checklists.

Additionally, `agent.md` was updated with a mandatory **Documentation Maintenance Contract** binding future coding agents to update these records after every implementation task, and all document links were made repository-relative for portable navigation across clones and GitHub.

### S1 Stage 2 (Prompt 1 Extension): ASR Runtime Configuration, Vocabulary Biasing Contract & Honest Confidence
*Commit: Pending Prompt 1 commit*

To prepare the codebase for concrete Faster-Whisper and MLX-Whisper adapters without premature model downloads, we hardened the speech contracts, configuration, and packaging:
- **Honest Confidence Contract:** Changed `ASRResult.confidence` and `WordTiming.confidence` to `float | None`. Numeric values are permitted strictly when originating from documented runtime probabilities. Uncalibrated beam-search log probabilities (`avg_logprob`) are not converted to probabilities via `exp()`, and missing confidences are never masked with `1.0`. `None` explicitly signals unavailable confidence. Empty audio returns an empty result with `confidence=None`.
- **Vocabulary-Prompt Support:** Extended `ASRProvider.transcribe()` to accept optional `initial_prompt: str | None = None`. This allows passing contextual domain tokens (*Sharma ji, udhaar, jama, chawal*) to the Whisper decoder's cross-attention layers, conditioning acoustic transcription without altering audio semantics.
- **Provider-Specific ASR Settings:** Added strongly-typed Pydantic settings in `bolkhata.config.settings:Settings`:
  - `asr_faster_whisper_model_id: str = "Systran/faster-whisper-small"`
  - `asr_faster_whisper_model_revision: str | None = "536b0662742c02347bc0e980a01041f333bce120"` (full 40-character hex commit verified upstream) <!-- pragma: allowlist secret -->
  - `asr_mlx_whisper_model_id: str = "mlx-community/whisper-small-mlx"`
  - `asr_mlx_whisper_model_revision: str | None = "45f3915923c7a79a5a5b5a7d909d39aeb0e5630e"` (full 40-character hex commit verified upstream) <!-- pragma: allowlist secret -->
  - `asr_device: str = "auto"` (validated against `auto`, `cpu`, `cuda`)
  - `asr_compute_type: str = "auto"` (validated against `auto`, `int8`, `float16`, `int8_float16`)
  - `asr_model_dir: str | None = None`
  - `asr_offline_mode: bool = False`
  - `asr_max_duration_seconds: float = 30.0` (validated positive finite number)
  - Preserved `asr_max_concurrency: int = 1` ($\ge 1$).
- **Isolated Multi-Platform Optional Dependencies:** Added optional extras `faster-whisper = ["faster-whisper==1.2.1"]` and `mlx-whisper = ["mlx-whisper==0.4.3; sys_platform == 'darwin' and platform_machine == 'arm64'"]` in `pyproject.toml`. Resolved reproducibly in `uv.lock`. Base virtual environment and CI install zero heavy speech libraries.
- **Unit Test Coverage:** Added `tests/unit/test_settings_asr.py` and updated `tests/unit/test_providers_mock.py`, expanding the passing test suite from 96 to 134 hermetic tests.

> **Note on Scope:** Neither Faster-Whisper nor MLX-Whisper adapters were implemented in this prompt, and zero model weights were downloaded. All tests execute completely offline in milliseconds.



---

## Section D — Important Architecture Decisions (ADRs)

| Decision | Chosen Approach | Alternative Considered | Architectural Rationale | Trade-Off / Consequence |
|---|---|---|---|---|
| **ADR 0001: Developer Tooling & Monorepo** *(Accepted)* | `uv` package manager, Python 3.11, FastAPI, Vite 6, Docker Compose. | Poetry/Pipenv; Next.js fullstack; separate backend/frontend repos. | Sub-second dependency resolution with `uv`; strict type safety; single-command local boot (`docker compose up`). | Docker images must build both Python and Node environments; unified tooling requires cross-stack discipline. |
| **ADR 0002: Domain Isolation Boundary** *(Accepted)* | Strict package boundary (`bolkhata/domains/ledger`). Outside code cannot import from ledger. | Monolithic application code where voice routes directly call ledger DB models. | Allows adapting to new hackathon problem statements or retail domains without modifying the core speech pipeline. | Requires standardized abstraction protocols (`DomainPack`) before domain features can be written. |
| **ADR 0003: Provider Interfaces & Registry** *(Accepted)* | Abstract base classes (`ASR`, `TTS`, `LLM`, `VAD`) + dependency-injected `ProviderRegistry`. | Direct imports of Faster-Whisper, Piper, and OpenAI SDKs in API route handlers. | Decouples runtime from hardware; allows offline CI testing with deterministic mocks; supports Apple Silicon (Metal) and PC (CUDA). | Slightly higher initial boilerplate; requires implementing mock fixtures for every new contract. |
| **Zero-Dependency Shared Audio Utils** *(Approved)* | Python stdlib `array` module for 16kHz PCM-to-float32 normalization. | Heavy reliance on `numpy` or `scipy` in core packages. | Keeps lightweight microservices and utility scripts free of heavy C-extensions until real inference engines are imported. | Pure Python generator comprehension during conversion is slightly slower than vectorized NumPy C-loops on massive audio buffers. |
| **Bounded ASR Concurrency** *(Approved)* | Bounded execution via `asr_max_concurrency: int = 1` in Settings. | Unbounded parallel `asyncio.to_thread` execution. | CTranslate2 and MLX inference are compute-bound and multi-threaded; unconstrained parallel calls exhaust RAM/VRAM. | Simultaneous requests must queue behind an async semaphore, increasing queue latency under load. |
| **Append-Only Ledger Safety** *(Approved - Planned S3)* | Immutable transaction entries; corrections and reversals are new compensating rows. | In-place SQL `UPDATE` / `DELETE` on transaction balances. | Financial auditability; guarantees zero data loss and simple offline synchronization conflict resolution. | Queries for current balance require aggregating transaction logs (mitigated by read-optimized balance snapshots). |
| **Deterministic Number Parsing** *(Approved - Planned S2)* | Rule-based grammar and regex parser for Indian currency numbers. | Delegating number extraction to LLM prompts. | **Money safety:** LLMs hallucinate, suffer prompt injection, and struggle with Hindi compound numbers (*dhai sau* = 250). | Requires writing and maintaining exhaustive grammatical rule sets for Hindi, Hinglish, and English numeric terms. |

---

## Section E — Current Architecture & Code Map

The following table documents the active repository layout, identifying the purpose and status of each key file:

| Path | Purpose & Architectural Role | Depends On / Used By | Implementation Status |
|---|---|---|---|
| `backend/src/bolkhata/api/app.py` | FastAPI application factory; binds routes and lifespan context. | Used by `uvicorn` and test suites. | **Implemented (S0)** |
| `backend/src/bolkhata/api/routes/health.py` | Liveness (`/health`) and readiness (`/ready`) endpoints. | Depends on `db.py` session factory. | **Implemented (S0)** |
| `backend/src/bolkhata/config/settings.py` | Pydantic v2 `BaseSettings`; environment variables and provider validation. | Used by `app.py`, `registry.py`, `db.py`. | **Implemented (S0/S1)** |
| `backend/src/bolkhata/common/db.py` | Async SQLAlchemy engine and session factory; SQLite WAL configuration. | Used by `health.py` and future repositories. | **Implemented (S0)** |
| `backend/src/bolkhata/common/logging.py` | Structured JSON log formatter with recursive PII/credential redaction. | Used throughout backend application. | **Implemented (S0)** |
| `backend/src/bolkhata/common/registry.py` | Thread-safe dependency injection registry managing AI provider lifecycles. | Used by application lifespan and routes. | **Implemented (S1)** |
| `backend/src/bolkhata/asr/base.py` | Abstract `ASRProvider` contract and immutable `ASRResult` dataclass. | Implemented by `mock.py`, future adapters. | **Implemented (S1)** |
| `backend/src/bolkhata/asr/mock.py` | Deterministic offline mock ASR provider for tests and CI. | Used by `registry.py` under `asr_provider="mock"`. | **Implemented (S1)** |
| `backend/src/bolkhata/asr/common.py` | 16kHz s16le PCM audio constants, float32 conversion, duration math. | Used by ASR providers and audio ingest. | **Implemented (S1)** |
| `backend/src/bolkhata/asr/vad.py` | Abstract `VADProvider` contract and `MockVADProvider`. | Used by realtime audio stream processors. | **Implemented (S1)** |
| `backend/src/bolkhata/tts/base.py` | Abstract `TTSProvider` contract for speech synthesis. | Implemented by `mock.py`, future TTS adapters. | **Implemented (S1)** |
| `backend/src/bolkhata/tts/mock.py` | Deterministic mock TTS generating valid sine-wave PCM audio. | Used by `registry.py` under `tts_provider="mock"`. | **Implemented (S1)** |
| `backend/src/bolkhata/llm/base.py` | Abstract `LLMProvider` contract (`stream_chat`, `complete_structured`). | Implemented by `mock.py`, future LLM adapters. | **Implemented (S1)** |
| `backend/src/bolkhata/llm/mock.py` | Deterministic mock LLM with fixture-driven structured output. | Used by `registry.py` under `llm_provider="mock"`. | **Implemented (S1)** |
| `backend/src/bolkhata/domains/` | Package boundary for business domains (e.g. kirana ledger). | Isolated from core speech pipeline. | **Package Boundary (S0)** |
| `backend/src/bolkhata/asr/faster_whisper.py` | Concrete Faster-Whisper ASR engine adapter. | Depends on `ASRProvider`, CTranslate2. | *Planned (S1 Stage 2)* |
| `backend/src/bolkhata/asr/mlx_whisper.py` | Concrete Apple Silicon Metal/MLX Whisper ASR adapter. | Depends on `ASRProvider`, mlx-whisper. | *Planned (S1 Stage 2)* |
| `backend/src/bolkhata/domains/ledger/` | Kirana ledger DomainPack, schema, normalizers, and entities. | Implements DomainPack protocol. | *Planned (S3)* |
| `frontend/src/App.tsx` | Root React component with health check polling. | Frontend entry point. | **Implemented (S0)** |
| `frontend/src/apps/ledger/` | Frontend domain view boundary for kirana ledger UI. | Frontend application layer. | *Planned (S5)* |
| `tests/unit/test_logging_redaction.py` | Unit tests for structured logging and PII redaction rules. | Verifies `logging.py`. | **Implemented (S0)** |
| `tests/unit/test_providers_mock.py` | Unit tests for provider contracts, mock behaviors, and registry lifecycle. | Verifies `registry.py` and mock providers. | **Implemented (S1)** |
| `tests/unit/test_asr_common.py` | Unit tests for PCM-to-float32 conversion and audio duration calculations. | Verifies `asr/common.py`. | **Implemented (S1)** |
| `tests/integration/test_health.py` | Integration tests for `/health` endpoint. | Verifies API routing and JSON response. | **Implemented (S0)** |
| `tests/integration/test_ready.py` | Integration tests for `/ready` endpoint under healthy and failed DB states. | Verifies DB connectivity and 503 handling. | **Implemented (S0)** |
| `tests/integration/test_alembic_smoke.py` | Integration tests verifying clean Alembic migration cycles. | Verifies DB migration scripts. | **Implemented (S0)** |

---

## Section F — Technical Interview Preparation

This section prepares candidates and contributors for technical interview questions grounded in BolKhata's actual codebase and architectural trade-offs.

```
Interview Topics:
1. Architecture & System Design
2. Python & Asynchronous Programming
3. AI & Speech Processing
4. Backend, Databases & Money Safety
5. Reliability, Security & Data Protection
6. Testing, CI/CD & Engineering Workflow
7. Project-Specific Deep Dives
```

---

### 1. Architecture & System Design

#### Q1.1: Why did you choose a provider-based architecture instead of calling Faster-Whisper or Piper directly?
- **What the interviewer is testing:** Understanding of separation of concerns, dependency inversion, testability, and multi-hardware support.
- **Suggested Answer:**
  > "In an AI speech system, coupling route handlers directly to specific machine learning libraries creates three major issues: testing becomes slow and non-deterministic because CI must download gigabytes of model weights; switching hardware (e.g. from an Apple Silicon Mac using Metal to an NVIDIA GPU using CUDA) requires rewriting application code; and benchmarking alternative models becomes invasive.
  > By introducing abstract contracts (`ASRProvider`, `TTSProvider`, `LLMProvider`) and a centralized `ProviderRegistry`, the application code only depends on high-level interfaces. In CI, we inject deterministic mock providers that run in milliseconds without network or GPU access. In production, we swap providers via environment configuration (`ASR_PROVIDER=faster_whisper` or `mlx_whisper`) without altering a single line of business logic."
- **Deeper Follow-Up:** How do you handle capability differences between providers (e.g., if one ASR engine supports word-level timestamps but another does not)?
- **What to show in code:** [backend/src/bolkhata/asr/base.py](../backend/src/bolkhata/asr/base.py) (contract definition) and [backend/src/bolkhata/common/registry.py](../backend/src/bolkhata/common/registry.py) (factory instantiation).

#### Q1.2: How would you scale this system from a single kirana store to thousands of concurrent merchants?
- **What the interviewer is testing:** Knowledge of distributed system bottlenecks, CPU/GPU saturation, stateful vs stateless services, and horizontal scaling.
- **Suggested Answer:**
  > "ASR and LLM inference are compute-bound and memory-heavy, whereas API routing and database operations are I/O-bound. Running both in the same process limits horizontal scalability.
  > In a scaled production architecture:
  > 1. The FastAPI web nodes remain stateless, terminating WebSocket connections and buffering audio.
  > 2. Audio chunks are dispatched to an inference worker pool (managed via Celery, Redis Streams, or gRPC microservices) backed by GPU autoscaling groups.
  > 3. Database operations use PostgreSQL with read-replicas, and session state is stored in distributed caches (Redis).
  > 4. For local kirana resilience, we maintain an edge-computing mode where a local workstation or mobile PWA performs offline inference, syncing transactions asynchronously when connectivity resumes."
- **Deeper Follow-Up:** How do you handle sticky sessions if a merchant's push-to-talk stream is split across multiple network packets?
- **What to show in code:** Point to the planned WebSocket architecture and bounded concurrency settings in [backend/src/bolkhata/config/settings.py](../backend/src/bolkhata/config/settings.py).

#### Q1.3: Why separate domain logic from infrastructure, and how is it enforced?
- **What the interviewer is testing:** Architectural boundaries, domain-driven design, and preventing domain leak into core pipelines.
- **Suggested Answer:**
  > "Under ADR 0002, BolKhata enforces a strict boundary between speech pipeline infrastructure and business domains (`bolkhata/domains/ledger`). If we ever pivot the product from kirana ledgers to healthcare prescription logging or civic grievance intake, the real-time voice pipeline (VAD $\rightarrow$ ASR $\rightarrow$ Dialogue State Machine $\rightarrow$ TTS) remains 100% untouched.
  > Each domain implements a standardized `DomainPack` (schema, normalizers, entity resolvers, read-back templates). Code outside `domains/` is strictly forbidden from importing anything from `domains/ledger`."
- **Deeper Follow-Up:** How would you enforce this import boundary automatically in CI?
- **What to show in code:** [docs/adr/0002-hackathon-scope-and-domain-isolation.md](adr/0002-hackathon-scope-and-domain-isolation.md).

---

### 2. Python & Asynchronous Programming

#### Q2.1: What is the difference between concurrency and parallelism, and how do they apply to BolKhata?
- **What the interviewer is testing:** Core Python concurrency concepts, the GIL, asyncio event loop, and multi-threading/multi-processing.
- **Suggested Answer:**
  > "Concurrency is about *dealing with* lots of things at once (structuring tasks to make progress independently), whereas parallelism is about *doing* lots of things at once (executing simultaneously on multiple CPU cores).
  > In BolKhata:
  > - **Concurrency (I/O-bound):** Managed by Python's single-threaded `asyncio` event loop. It handles hundreds of incoming WebSocket frames, HTTP requests, and async database queries concurrently without blocking.
  > - **Parallelism (Compute-bound):** CTranslate2 (Faster-Whisper) executes native C++ matrix multiplications across multiple CPU/GPU threads, releasing Python's GIL. If we ran synchronous inference directly on the asyncio loop, it would freeze the loop, dropping WebSocket frames and failing health checks. Therefore, inference must be offloaded using `asyncio.to_thread()`."
- **Deeper Follow-Up:** What are the hidden risks of using `asyncio.to_thread()` with compute-bound neural models?
- **What to show in code:** [backend/src/bolkhata/asr/mock.py](../backend/src/bolkhata/asr/mock.py) (async contract definitions).

#### Q2.2: What happens when an awaiting coroutine is cancelled while native inference is running in `asyncio.to_thread()`?
- **What the interviewer is testing:** Advanced understanding of Python thread execution and cancellation semantics.
- **Suggested Answer:**
  > "When a coroutine awaiting `asyncio.to_thread(func)` is cancelled (for example, if a client disconnects), the `asyncio.CancelledError` is raised immediately inside the coroutine on the event loop.
  > However, **Python cannot forcefully kill an operating system thread**. The underlying worker thread in the thread pool continues executing the native C++ inference to completion; its return value is simply discarded when finished.
  > In BolKhata, we explicitly documented this invariant in ADR 0003: cancellation releases the event loop immediately, but does not abort in-flight native CTranslate2 compute. To prevent resource exhaustion from abandoned requests, we bound concurrency via semaphores rather than spawning unconstrained threads."
- **Deeper Follow-Up:** How could you achieve true immediate hardware abort if required?
- **What to show in code:** [docs/adr/0003-provider-interfaces-and-registry.md](adr/0003-provider-interfaces-and-registry.md) (Contract Invariants: Streaming and Cancellation).

#### Q2.3: How does startup rollback work in the provider registry?
- **What the interviewer is testing:** Distributed lifecycle management, exception safety, and resource leak prevention.
- **Suggested Answer:**
  > "If a service crashes halfway through initialization, any previously acquired resources (open network sockets, GPU memory allocations, database pools) must be cleanly released.
  > In `ProviderRegistry.initialize()`, providers are initialized sequentially: ASR $\rightarrow$ TTS $\rightarrow$ LLM $\rightarrow$ VAD. As soon as a provider successfully completes `initialize()`, it is tracked in `_initialized_providers`.
  > If a subsequent provider raises an exception during `initialize()` or `warmup()`, the registry catches the error, initiates an immediate reverse-order cleanup of all already-initialized providers, resets its internal state, and re-raises the original exception. This guarantees failure-atomic lifecycle management."
- **Deeper Follow-Up:** What happens if a cleanup operation itself throws an exception during a rollback?
- **What to show in code:** [backend/src/bolkhata/common/registry.py](../backend/src/bolkhata/common/registry.py) (lines 140–180).

---

### 3. AI & Speech Processing

#### Q3.1: What is PCM audio, and why did BolKhata standardize on 16 kHz mono signed 16-bit little-endian?
- **What the interviewer is testing:** Fundamentals of digital signal processing (DSP), audio codecs, and model input expectations.
- **Suggested Answer:**
  > "Pulse Code Modulation (PCM) is uncompressed digital audio representing acoustic waves by sampling amplitudes at uniform intervals.
  > We chose `16,000 Hz, Mono, 16-bit Signed Little-Endian PCM` because:
  > 1. **Model Expectation:** State-of-the-art speech models (OpenAI Whisper, Silero VAD) are trained on 16 kHz mono audio. Passing 44.1 kHz or 48 kHz audio requires real-time resampling, adding CPU overhead.
  > 2. **Bandwidth & Latency:** 16 kHz mono 16-bit audio produces exactly $16,000 \times 2 = 32,000$ bytes/sec (32 KB/s). This is small enough to stream over low-bandwidth 3G/4G connections without compression artifacts.
  > 3. **Zero Decode Overhead:** Compressed formats (MP3, AAC) require codec decompression on the server before feeding tensors. Raw PCM can be converted directly into float32 tensors with basic integer division."
- **Deeper Follow-Up:** Why does endianness matter when processing audio across network boundaries?
- **What to show in code:** [backend/src/bolkhata/asr/common.py](../backend/src/bolkhata/asr/common.py) (constants and `byteswap()` logic).

#### Q3.2: What is the difference between Faster-Whisper and MLX-Whisper?
- **What the interviewer is testing:** Knowledge of AI runtimes, quantization, and hardware-specific acceleration.
- **Suggested Answer:**
  > "Both run OpenAI's Whisper model architecture, but use completely different execution runtimes:
  > - **Faster-Whisper:** Powered by CTranslate2, an optimized C++ inference engine supporting INT8/FP16 quantization on x86 CPUs and NVIDIA GPUs (CUDA). It achieves up to 4x speedup over PyTorch with significantly lower memory usage.
  > - **MLX-Whisper:** Specifically designed for Apple Silicon (M1/M2/M3/M4) using Apple's MLX machine learning framework. It leverages unified memory and Metal GPU cores natively, outperforming CPU-based CTranslate2 on macOS without requiring CUDA.
  > BolKhata provides adapters for both: MLX-Whisper for Mac development/demos, and Faster-Whisper for Linux/Windows deployment."
- **Deeper Follow-Up:** How does INT8 quantization affect Word Error Rate (WER) on Indian accented speech?
- **What to show in code:** [docs/adr/0001-tooling-choices.md](adr/0001-tooling-choices.md) and [docs/adr/0003-provider-interfaces-and-registry.md](adr/0003-provider-interfaces-and-registry.md).

#### Q3.3: Why does speech recognition frequently confuse Indian spoken numbers, and how do you mitigate it?
- **What the interviewer is testing:** Domain awareness of Indian speech recognition challenges and mitigation strategies.
- **Suggested Answer:**
  > "General-purpose ASR models struggle with Indian spoken numbers for two primary reasons:
  > 1. **Acoustic Similarity in Noisy Environments:** In noisy kirana shops, words like *'saat'* (7) and *'aath'* (8), or *'pandrah'* (15) and *'pachaas'* (50) have high phonetic overlap.
  > 2. **Fractional Number Systems:** Hindi and Hinglish use fractional units (*'dhai'* = 2.5, *'dedh'* = 1.5, *'sawa'* = +0.25, *'paune'* = -0.25). Standard English ASR models transcribe *"dhai sau"* as *"die saw"* or *"thai sau"*.
  > In BolKhata, we mitigate this via:
  > - **Vocabulary Biasing (F1):** Providing prompt biasing tokens to Whisper emphasizing kirana vocabulary (*udhaar, jama, chawal, sau, hazaar*).
  > - **Deterministic Parser (S2):** Rule-based parsing mapping colloquial numeric phrases directly to floating-point amounts.
  > - **Mandatory Verbal Read-back (S4):** Explicit spoken confirmation (*'Do sau pachaas rupaye udhaar. Sahi hai?'*) so the shopkeeper catches any phonetic confusion immediately."
- **Deeper Follow-Up:** How does Whisper's `initial_prompt` parameter work for vocabulary biasing?
- **What to show in code:** Point to Section A user journey and planned S2 milestone in Section B.

---

### 4. Backend, Databases & Money Safety

#### Q4.1: What is an append-only ledger, and why is it mandatory for financial entries?
- **What the interviewer is testing:** Financial systems engineering, audit trails, and data integrity.
- **Suggested Answer:**
  > "In an append-only ledger, rows are never modified (`UPDATE`) or deleted (`DELETE`). Every state change is recorded as a new immutable event.
  > If a shopkeeper enters ₹500 by mistake and corrects it to ₹300, the database does not overwrite the record. Instead, it creates a compensating transaction of -₹200 (or reverses the ₹500 entry and adds a new ₹300 entry) with a reference to the original transaction ID.
  > This guarantees:
  > 1. **Complete Auditability:** Every mistake, correction, and voice turn is permanently auditable.
  > 2. **Offline Conflict Resolution:** When offline mobile clients sync with the server, append-only logs can be merged deterministically using vector clocks or timestamps without row-level overwrite collisions.
  > 3. **Fraud & Bug Prevention:** Accidental code bugs cannot wipe out customer balances."
- **Deeper Follow-Up:** How do you efficiently calculate a customer's current balance if the ledger contains millions of historical transactions?
- **What to show in code:** Master context rules in [bolkhata-agent-prompts.md](../bolkhata-agent-prompts.md) (Money safety principles).

#### Q4.2: Why must the LLM NEVER compute or decide financial amounts?
- **What the interviewer is testing:** AI safety, deterministic vs probabilistic systems, and financial risk management.
- **Suggested Answer:**
  > "Large Language Models are probabilistic next-token predictors. They have no internal concept of arithmetic truth and are susceptible to hallucinations, prompt injection, and stochastic variability.
  > If an LLM is asked to compute: *'Sharma ji had 250 pending, bought 120 of rice, and paid 100'*, it might output 270 on temperature 0, but output 370 under slight prompt variations or noise. In a financial ledger, a mathematical hallucination is a catastrophic failure that destroys merchant trust.
  > In BolKhata's architecture:
  > - The LLM is used strictly for **intent classification** and **semantic slot extraction** (identifying customer names and item descriptions).
  > - **All arithmetic, currency parsing, and balance calculations are performed by deterministic, unit-tested Python code**."
- **Deeper Follow-Up:** How do you handle cases where the customer speaks a complex mathematical request like *"Pichla aadha maaf kar do"*?
- **What to show in code:** Section D ADR table and [docs/adr/0003-provider-interfaces-and-registry.md](adr/0003-provider-interfaces-and-registry.md).

#### Q4.3: How does idempotency prevent duplicate transactions in voice interfaces?
- **What the interviewer is testing:** Network reliability, duplicate request handling, and distributed transaction safety.
- **Suggested Answer:**
  > "In voice applications, users frequently repeat themselves if an interface lags (*'Sharma ji 500 udhaar... Sharma ji 500 udhaar'*), or mobile networks drop the TCP connection right after the client sends a confirmation.
  > To prevent double-posting:
  > 1. Every voice session turn generates a unique `generation_id` and client-side `idempotency_key` (e.g. UUID derived from session ID + turn sequence).
  > 2. When a commit request hits the database, the ledger table enforces a unique constraint on `idempotency_key`.
  > 3. If a duplicate request arrives with the same key, the backend returns the already-committed transaction without creating a second ledger row."
- **Deeper Follow-Up:** What status code and payload should an idempotent API return when a duplicate key is submitted?
- **What to show in code:** Master context rules in [bolkhata-agent-prompts.md](../bolkhata-agent-prompts.md).

---

### 5. Reliability, Security & Data Protection

#### Q5.1: How do you prevent sensitive customer names, phone numbers, and secrets from leaking into application logs?
- **What the interviewer is testing:** Privacy regulations (DPDP Act in India, GDPR), security engineering, and custom logging handlers.
- **Suggested Answer:**
  > "We implemented a custom `StructuredJsonFormatter` in `bolkhata.common.logging` that intercepts every log record before emission.
  > It enforces privacy through:
  > 1. **Key-Based Redaction:** Automatically scrubs sensitive dictionary keys (`customer_name`, `phone`, `token`, `api_key`, `secret`, `password`) replacing them with `[REDACTED]`.
  > 2. **Regex Pattern Scrubbing:** Scans all string values and messages for Indian 10-digit mobile numbers (e.g. `\b[6-9]\d{9}\b`), bearer tokens, and JWT strings.
  > 3. **Recursive Exception Traversal:** Inspects nested exception chains and traceback frames, sanitizing local variables so that unexpected crashes cannot dump customer data into log aggregators.
  > 4. **Fail-Closed Design:** If the redaction logic itself encounters an unhandled formatting error, it emits a safe sentinel log rather than crashing or leaking unredacted raw data."
- **Deeper Follow-Up:** Why is logging raw audio bytes or transcripts at INFO level dangerous?
- **What to show in code:** [backend/src/bolkhata/common/logging.py](../backend/src/bolkhata/common/logging.py) and [tests/unit/test_logging_redaction.py](../tests/unit/test_logging_redaction.py).

#### Q5.2: What happens if the database crashes while the voice pipeline is active?
- **What the interviewer is testing:** Fault tolerance, circuit breaking, health probes, and graceful degradation.
- **Suggested Answer:**
  > "BolKhata separates liveness from readiness:
  > - `GET /health` continues returning HTTP 200 as long as the process event loop is alive.
  > - `GET /ready` actively tests the database connection with `SELECT 1`. If the database crashes, `/ready` immediately returns HTTP 503 Service Unavailable with a structured error.
  > In the voice pipeline:
  > 1. If an active session attempts to commit a transaction when the database is down, the repository raises a `DatabaseUnavailableError`.
  > 2. The pipeline transitions the session to an error state and synthesizes an immediate voice prompt: *'Khata save nahi ho paya. Kripya dobara koshish karein.'*
  > 3. The transaction payload is preserved in the client's local IndexedDB buffer so that no merchant data is lost, allowing auto-sync once the backend recovers."
- **Deeper Follow-Up:** How do you test database disconnection in automated integration tests without killing the host database server?
- **What to show in code:** [tests/integration/test_ready.py](../tests/integration/test_ready.py) (uses `mock_db_unreachable` fixture).

---

### 6. Testing, CI/CD & Engineering Workflow

#### Q6.1: How do you unit test an ASR provider without downloading gigabytes of model weights or hitting external APIs?
- **What the interviewer is testing:** Testing strategy, hermetic builds, CI cost optimization, and test doubles.
- **Suggested Answer:**
  > "Unit tests must be fast, deterministic, and 100% offline. Relying on live model downloads in CI makes builds flaky, slow, and expensive.
  > In BolKhata:
  > 1. We defined abstract contracts (`ASRProvider`, `TTSProvider`, `LLMProvider`).
  > 2. We created deterministic mock implementations (`MockASRProvider`, etc.) that simulate inference with predictable outputs. For example, `MockASRProvider` returns deterministic transcripts based on audio byte length or explicit fixtures.
  > 3. Tests verify state machine transitions, concurrency bounds, error handling, and payload transformations using these mocks.
  > 4. Real neural models are evaluated separately in dedicated benchmark and evaluation harnesses (`docs/benchmarks`), keeping standard CI test runs under 1 second."
- **Deeper Follow-Up:** How do you ensure your mock implementation does not drift from the behavior of the real provider?
- **What to show in code:** [backend/src/bolkhata/asr/mock.py](../backend/src/bolkhata/asr/mock.py) and [tests/unit/test_providers_mock.py](../tests/unit/test_providers_mock.py).

#### Q6.2: Why do you run pre-commit hooks twice consecutively in CI?
- **What the interviewer is testing:** Knowledge of formatter idempotency, git hooks, and build reproducibility.
- **Suggested Answer:**
  > "Certain code formatters (like Ruff, Black, or trailing whitespace cleaners) modify files on their first pass, causing the hook to exit with code 1.
  > Running pre-commit twice consecutively verifies two critical properties:
  > 1. **Zero Uncommitted Formatting Drift:** On the second pass, all files must already be perfectly formatted, so pre-commit must exit with code 0 without touching any files.
  > 2. **Hook Idempotency:** It proves that formatters and linters are idempotent—applying them multiple times does not produce oscillations or conflicting changes."
- **Deeper Follow-Up:** What should you do if pre-commit fails in CI on a branch that passed locally?
- **What to show in code:** `.pre-commit-config.yaml` and the verification steps in Section H.

---

### 7. Project-Specific Deep Dives

#### Q7.1: Explain the cleanup retry-order bug discovered in `ProviderRegistry` and how you solved it.
- **What the interviewer is testing:** Ability to debug subtle state-management flaws, sequence invariants, and root-cause analysis.
- **Suggested Answer:**
  > "**The Bug:** In `ProviderRegistry.shutdown()`, providers are shut down in reverse startup order (VAD $\rightarrow$ LLM $\rightarrow$ TTS $\rightarrow$ ASR). If a provider's `shutdown()` raised an exception, previously our code popped it from `_initialized_providers` and appended it to a `failed` list for retry. If multiple providers failed, their relative ordering in the retry list was reversed, violating the shutdown sequence invariant on subsequent retry attempts.
  > **The Solution:** We established a **canonical startup-order invariant**. The registry tracks initialized providers by identity in their canonical creation order (`[ASR, TTS, LLM, VAD]`). During shutdown or rollback, the registry iterates in `reversed()` order. Providers are only removed from the list when their shutdown *succeeds*. If one or more fail, the remaining providers retain their exact original relative positions, guaranteeing that any subsequent shutdown call always retries in strict reverse-startup sequence."
- **Deeper Follow-Up:** How did you test this scenario to ensure no regressions?
- **What to show in code:** `test_multiple_providers_fail_shutdown_retried_in_reverse_startup_order` in [tests/unit/test_providers_mock.py](../tests/unit/test_providers_mock.py).

#### Q7.2: Why did you use Python's standard-library `array` module instead of NumPy for audio utilities?
- **What the interviewer is testing:** Dependency minimalism, binary compatibility, and performance trade-offs.
- **Suggested Answer:**
  > "NumPy is a large C-extension dependency (tens of megabytes) that requires platform-specific wheels and compilation. In minimal container environments, cloud functions, or lightweight client utilities, requiring NumPy just to convert a few thousand PCM audio bytes to float32 introduces unnecessary bloat.
  > Python's standard library `array` module (`array.array('h')` for signed 16-bit integers and `array.array('f')` for 32-bit floats) implements Python's buffer protocol directly in C. It supports fast byte parsing via `.frombytes()`, native endian swapping via `.byteswap()`, and contiguous memory allocation without a single third-party dependency.
  > Concrete ASR engines (like CTranslate2) accept buffer protocol objects directly, allowing our shared audio utilities to remain completely zero-dependency."
- **Deeper Follow-Up:** What are the exact mathematical normalization bounds implemented in `pcm_to_float32`?
- **What to show in code:** [backend/src/bolkhata/asr/common.py](../backend/src/bolkhata/asr/common.py) and [tests/unit/test_asr_common.py](../tests/unit/test_asr_common.py).

---

## Section G — Current Status & Next Steps

### Active Component Status
*Verified as of S1 Stage 2 Prompt 1*

- **S0 Production Foundation:** **Completed** (Monorepo, FastAPI, async DB, logging redaction, Alembic, Docker, CI).
- **S0 Tooling & Secret Remediation:** **Completed** (Reproducible pre-commit, scanner allowlists, clean linting).
- **S1 Stage 1 Provider Foundation:** **Completed** (Abstract contracts, deterministic mocks, thread-safe DI registry, reverse-order lifecycle rollbacks).
- **S1 Stage 2 (Prompt 1) Audio Utilities & ASR Settings:** **Completed** (16kHz PCM utilities, float32 conversion, duration calculations, concurrency bounds).
- **S1 Stage 2 (Prompt 1 Extension) ASR Contracts & Config:** **Completed** (Honest confidence semantics `float | None`, `initial_prompt` pass-through, validated runtime settings, optional dependency groups, 134 passing tests).
- **Faster-Whisper Adapter:** *Not Implemented (Planned next)*.
- **MLX-Whisper Adapter:** *Not Implemented (Planned next)*.
- **Real Speech Inference & Evaluation:** *Not Implemented (Planned next)*.
- **WebSocket Push-to-Talk Voice Loop:** *Not Implemented (Planned S1/S4)*.
- **S2 Spoken-Number Parser & Evaluation Harness:** *Pending*.
- **S3 DomainPack & Append-Only Ledger:** *Pending*.
- **S4 Read-Back, Confirmation & Correction Loop:** *Pending*.
- **S5 Frontend PWA & Hardware Benchmarking:** *Pending*.
- **S6 Evidence & Release Freeze:** *Pending*.

### Next Implementation Sequence
1. **Faster-Whisper Provider:** Implement `FasterWhisperASRProvider` in `backend/src/bolkhata/asr/faster_whisper.py` using CTranslate2 with CPU/CUDA execution, beam search, and vocabulary biasing tokens.
2. **MLX-Whisper Provider:** Implement `MLXWhisperASRProvider` in `backend/src/bolkhata/asr/mlx_whisper.py` for hardware-accelerated Metal inference on Apple Silicon Macs.
3. **Registry Integration & Optional Dependencies:** Wire concrete ASR engines into `ProviderRegistry`, configuring optional dependency groups in `pyproject.toml` (`[project.optional-dependencies]`).
4. **Real Speech Fixtures & Accuracy Evaluation:** Create recorded Hindi/Hinglish audio fixtures in `tests/fixtures/` and verify ASR accuracy against ground truth without synthetic fabrication.
5. **Push-to-Talk WebSocket Voice Loop:** Connect audio ingest endpoint to ASR engine and return streaming transcription events to the frontend.

---

## Section H — Metrics & Verified Evidence

### Verified Gate Results

| Metric / Verification Gate | Latest Verified Result | What It Proves | Known Limitations |
|---|---|---|---|
| **Backend Unit & Integration Tests** | `134 passed in 0.18s` | All 134 tests pass across DB health, Alembic, logging redaction, provider contracts, registry lifecycles, PCM audio conversion, honest confidence contracts, and ASR settings validation. | Tests use deterministic mocks; real neural inference models are tested in separate evaluation suites. |
| **Ruff Lint Check** | `All checks passed!` | Zero PEP 8, import, flake8, or syntax violations across `src/` and `tests/`. | Verifies code style; does not test runtime logic. |
| **Ruff Format Check** | `34 files already formatted` | Repository formatting is 100% compliant with standard rules. | Whitespace/formatting only. |
| **Mypy Static Type Analysis** | `Success: no issues found in 23 source files` | Full static type safety across `bolkhata` package under strict type annotations. | Does not type-check dynamically generated runtime values. |
| **Frontend Lint & Build** | `ESLint clean (0 warnings), Vite built in 271ms` | React TypeScript compilation and production bundle build succeed with zero errors. | UI is currently at S0 baseline; push-to-talk voice controls are not yet wired. |
| **Pre-Commit Checks (Two Passes)** | `Passed (all 11 hooks passed twice)` | Formatting, JSON/TOML validation, large file checks, and branch protection are completely reproducible and idempotent. | Verifies static file integrity. |
| **Secret Scanning (`detect-secrets`)** | `0 secrets detected ("results": {})` | No API keys, passwords, high-entropy tokens, or credentials exist in tracked files. | Relies on known regex patterns and entropy thresholds. |
| **Git Diff Cleanliness** | `git diff --check clean` | Zero whitespace errors or trailing carriage returns. | Formatting check only. |
| **ASR Word Error Rate (WER)** | *Not yet measured* | Real audio evaluation will be conducted in S2/S6. | Unmeasured at current sprint. |
| **End-to-End Voice Latency (P99)** | *Not yet measured* | Latency budget profiling will occur in S5 on Mac and RTX 3050. | Unmeasured at current sprint. |

### Verified Git Commit History

The following table records the verifiable Git commit history on the repository:

| Commit SHA | Branch | Commit Message / Milestone | Key Artifacts & Deliverables |
|---|---|---|---|
| `bd11710` | `main` | `feat(s0): publish foundation baseline` | Monorepo layout, FastAPI factory, async DB, logging, health probes, Docker, Vite frontend. |
| `8aa8415` | `main` | `fix(security): make redaction fixtures scanner-safe` | Excluded synthetic PII test strings via `.secrets.baseline` line allowlists. |
| `fe97621` | `chore/s0-precommit-remediation` | `chore(tooling): make pre-commit checks reproducible` | Fixed `tsconfig.json` JSONC comments; pinned local virtualenv pre-commit hooks. |
| `96b2b52` | `feat/s1-provider-foundation` | `feat(s1): add provider contracts and mock registry` | Abstract provider contracts (`ASR`, `TTS`, `LLM`, `VAD`), deterministic mocks, and `ProviderRegistry`. |
| `687385c` | `feat/s1-provider-foundation` | `fix(s1): harden provider lifecycle and mock contracts` | Fixed early tracking on startup rollback, structured mock fallback, and documentation. |
| `e1cf4a9` | `feat/s1-provider-foundation` | `chore: fix baseline test lint and formatting` | Cleaned up pre-existing Ruff violations (PT018, PT006) in historical test files. |
| `516e03a` | `feat/s1-provider-foundation` | `fix(s1): preserve provider order across cleanup retries` | Implemented canonical startup-order invariant and identity-based tracking for reverse cleanup. |
| `863b07d` | `feat/s1-provider-foundation` | `feat(s1): add PCM utilities and ASR settings` | Created `bolkhata.asr.common` (16kHz s16le PCM to float32), `asr_max_concurrency` setting, and 14 new tests. |
| `b065ab8` | `feat/s1-provider-foundation` | `docs: add engineering progress and interview guide` | Established `docs/progress.md` living engineering journal and interview defense manual. |
| `b6b7461` | `feat/s1-provider-foundation` | `docs: add engineering knowledge base and deep dive` | Created `docs/decision.md`, `docs/architecture-deep-dive.md`, `docs/README.md`, and updated `agent.md`. |
| `b261680` | `feat/s1-provider-foundation` | `docs: fix repository-relative documentation links` | Made all documentation file links portable using repository-relative Markdown paths. |
| *(Pending)* | `feat/s1-provider-foundation` | `feat(s1): define ASR runtime config and confidence semantics` | Honest confidence semantics (`float \| None`), vocabulary-prompt contract, validated ASR runtime settings, platform-specific optional dependencies, and 38 new unit tests. |

---

## Section I — How This Document Must Be Maintained

To ensure `docs/progress.md` remains the authoritative source of truth for engineering decisions, onboarding, and interview review, all future contributors and coding agents must adhere to the following maintenance instructions:

1. **Update After Every Task:** Never complete an implementation task or prompt without updating this document.
2. **Honesty Over Optimism:** Never mark a milestone or feature as completed until its code is written, its tests pass, and its git commit hash is verified. If a benchmark has not been run, state: *"Not yet measured"*.
3. **Capture Architectural Rationale:** When writing code, document *why* a particular pattern was chosen (e.g., standard library `array` over NumPy, canonical ordering over retry lists).
4. **Grow the Interview Question Bank:** Every challenging bug or architectural trade-off encountered during development must be converted into an interview question in Section F.
5. **Keep Git History Auditable:** Record verified commit SHAs, test counts, and gate results after every push.
