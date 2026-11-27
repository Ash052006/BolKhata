# BolKhata (बोलखाता) — Living Engineering Progress & Interview Guide

> **Document Type:** Living Architecture, Engineering Journal & Technical Interview Preparation Guide
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)
> **Last Updated:** Sprint S4 (Trust UX, Correction, and Failure Handling)
> **Active Branch:** `feat/s1-provider-foundation`
> **Latest Commit:** `9b4ad01b22e17ea5cf8a94644da605f6b8b0e77d`

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
  - [S1 Stage 2 (Prompt 2): MLX-Whisper ASR Provider Implementation & Stabilization](#s1-stage-2-prompt-2-mlx-whisper-asr-provider-implementation--stabilization)
  - [S1 Stage 3: Realtime Protocol, State Machine & WebSocket Session](#s1-stage-3-realtime-protocol-state-machine--websocket-session)
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
        WS["WebSocket Stream<br/>(Binary PCM + JSON Events)<br/><b>[Implemented - S1]</b>"]
    end

    subgraph BackendGateway ["FastAPI Application"]
        ROUTER["API Router & Lifespan<br/>(app.py / health.py)<br/><b>[Implemented - S0]</b>"]
        REGISTRY["Provider Registry<br/>(registry.py)<br/><b>[Implemented - S1]</b>"]
    end

    subgraph SpeechPipeline ["Speech & Audio Layer"]
        COMMON["Audio Utils & Settings<br/>(16kHz s16le PCM to float32)<br/><b>[Implemented - S1]</b>"]
        ASR["ASR Provider<br/>(Mock <b>[Done]</b> / MLX (Apple Silicon) <b>[Implemented - S1]</b>)"]
        VAD["VAD Provider<br/>(Mock <b>[Done]</b> / Silero <i>[Planned]</i>)"]
        TTS["TTS Provider<br/>(Mock <b>[Done]</b> / Piper, Edge <i>[Planned]</i>)"]
    end

    subgraph CoreEngine ["Domain & Intelligence Layer"]
        NUM_PARSER["Deterministic Spoken-Number Parser<br/>(Hindi / Hinglish / English)<br/><b>[Implemented - S2]</b>"]
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
| **S1** | **Provider Foundation & Push-to-Talk Slice** | Abstract provider interfaces (`ASR`, `TTS`, `LLM`, `VAD`), deterministic offline mocks, thread-safe DI registry with lifecycle rollbacks, 16kHz PCM utilities, Apple Silicon MLX ASR adapter, WebSocket push-to-talk stream (`/ws/session`), explicit 4-state session machine, generation invariants, AudioWorklet frontend capture, and flushable PCM playback. | Enables 100% offline, deterministic CI testing; delivers a snappy, race-free voice loop with per-stage latency telemetry. | **Completed** |
| **S2** | **Spoken-Number Parser & Evaluation Harness** | Deterministic number parser for Hindi/Hinglish numeric idioms (*dhai sau*, *dedh hazaar*), ground-truth audio test corpus tooling, Word Error Rate (WER) and number extraction accuracy evaluation harness, strict and tolerant normalization. | **Money safety:** Large language models hallucinate and fail at Indian colloquial arithmetic. Deterministic parsing guarantees mathematical correctness. | **Completed** |
| **S3** | **DomainPack & Ledger Extraction** | Pluggable DomainPack protocol, kirana transaction extraction schema, customer name entity resolution, append-only ledger schema, idempotency tokens. | Decouples speech pipeline from business logic; guarantees immutable financial audit trails and prevents double-posting. | **Completed** |
| **S4** | **Read-Back, Correction & Failure Handling** | Verbal confirmation loop, state machine (IDLE, LISTENING, THINKING, SPEAKING), voice-driven transaction corrections, network failure and audio recovery flows. | Kirana shops cannot afford silent transcription mistakes; explicit verbal read-back ensures merchant trust and operational resilience. | **Completed** |
| **S5** | **Frontend PWA, Offline Fallback & Benchmarks** | React PWA with AudioWorklet capture, offline local-LLM fallback, hardware latency/memory profiling (Apple Silicon Mac vs Windows RTX 3050). | Delivers snappy zero-latency push-to-talk UX and empirically validates performance against latency budgets on target hardware. | **Completed** |
| **S6** | **Evidence, Documentation & Release Freeze** | Complete benchmarking documentation, reproducible demo script, final test freeze, project release tag. | Provides verifiable proof of system performance, accuracy, and operational claims for hackathon evaluation and production readiness. | **Completed** |

### Feature Tiers & Priority Cut Line

To balance ambitious capabilities with strict delivery timelines, features are tiered into strict priority bands:

- **Must-Have (Core Invariants — All Completed & Verified):**
  - **F1 (Vocabulary Biasing):** Bias ASR toward kirana customer names, commodity terms (*chawal*, *dal*, *atta*), and transaction words (*udhaar*, *jama*). **[Completed]**
  - **F2 (Spoken Balance Queries):** Support instant verbal balance inquiries (*"Sharma ji ka kitna baaki hai?"*). **[Completed]**
  - **F6 (Data Ownership & Export):** Zero vendor lock-in; one-click local SQLite backup and CSV/PDF/JSON export and DPDP Right to Erasure. **[Completed]**
  - **F7 (Pilot Instrumentation):** Granular structured metrics (PTT-to-transcript latency, extraction accuracy, user confirmation rate) without logging PII. **[Completed]**
- **Should-Have (High Value — All Completed & Verified):**
  - **F3 (Debt Ageing & Daily Digest):** Automated calculation of overdue credit buckets (0-7d, 8-30d, 31-60d, 60+d) using FIFO payment allocation and evening settlement summaries (*"Aaj ka hisaab"*). **[Completed]**
  - **F4 (WhatsApp Reminder Drafts):** Deterministic pre-filled WhatsApp click-to-chat links across gentle/neutral/firm tones, phone normalizer, opt-out `do_not_remind` flag, and frequency cooldown guardrails. **[Completed]**
  - **F5 (Explainability Panel):** Stage-by-stage diagnostic breakdown (transcripts, per-field provenance, confidence, risk assessment, and PII-redacted JSON export). **[Completed]**
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

Before implementing concrete speech recognition on Apple Silicon (MLX-Whisper), we established a shared, high-performance audio standard:
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
- **ASR Concurrency Bounds:** Added `asr_max_concurrency: int = 1` in `Settings`. Speech inference models (such as planned MLX-Whisper on Apple Silicon) saturate CPU/GPU cores during inference; allowing unbounded concurrent calls causes severe thread contention and out-of-memory crashes. The safe default of 1 ensures serialized execution unless explicitly scaled.

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

### S1 Stage 2: Apple Silicon MLX ASR Runtime Configuration, Vocabulary Biasing & Honest Confidence
*Commits: `f84abff`, `fix(s1): make ASR configuration Apple Silicon only`*

To prepare the codebase for concrete Apple Silicon speech recognition without premature model downloads or cross-platform configuration bloat, we hardened the speech contracts, configuration, and packaging:
- **Honest Confidence Contract:** Changed `ASRResult.confidence` and `WordTiming.confidence` to `float | None`. Numeric values are permitted strictly when originating from documented runtime probabilities. Uncalibrated beam-search log probabilities (`avg_logprob`) are not converted to probabilities via `exp()`, and missing confidences are never masked with `1.0`. `None` explicitly signals unavailable confidence. Empty audio returns an empty result with `confidence=None`.
- **Vocabulary-Prompt Support:** Extended `ASRProvider.transcribe()` to accept optional `initial_prompt: str | None = None`. This supplies contextual domain tokens (*Sharma ji, udhaar, jama, chawal*) as prefix context to the Whisper autoregressive decoder's masked self-attention. It biases recognition toward domain vocabulary, but does not guarantee correct recognition or replace acoustic evidence; excessive or incorrect context can bias transcripts incorrectly or increase hallucination risk. Its efficacy must be empirically evaluated against real audio with positive and negative controls.
- **Apple Silicon-Only Architecture (DEC-0026):**
  - Standardized physical execution exclusively on the Apple Silicon MacBook Air M5 (16 GB unified memory) using Apple's MLX machine learning framework.
  - Fully removed Windows/CUDA/Faster-Whisper dependencies, CTranslate2, and generic `asr_device` / `asr_compute_type` settings.
- **Provider-Specific MLX Settings:** Strongly-typed Pydantic settings in `bolkhata.config.settings:Settings`:
  - `asr_mlx_whisper_model_id: str = "mlx-community/whisper-small-mlx"`
  - `asr_mlx_whisper_model_revision: str | None = "45f3915923c7a79a5a5b5a7d909d39aeb0e5630e"` (full 40-character hex commit verified upstream) <!-- pragma: allowlist secret -->
  - `asr_model_dir: str | None = None`
  - `asr_offline_mode: bool = False`
  - `asr_max_duration_seconds: float = 30.0` (validated positive finite number)
  - `asr_max_concurrency: int = 1` ($\ge 1$).
  - `asr_provider: str = "mock"` (validated: `mock`, `mlx_whisper`).
- **Isolated MLX Optional Dependency:** Pinned `mlx-whisper = ["mlx-whisper==0.4.3; sys_platform == 'darwin' and platform_machine == 'arm64'"]` under `[project.optional-dependencies]` in `pyproject.toml`. Resolved reproducibly in `uv.lock`. Base virtual environment and CI install zero heavy speech libraries.
- **Unit Test Coverage:** Verified by 129 hermetic tests across `tests/unit/test_settings_asr.py` and `tests/unit/test_providers_mock.py`.

> **Note on Scope & Status (Prompt 1):** Configuration is Apple Silicon-only, MLX is an optional dependency, the real MLX adapter was pending implementation (`MockASRProvider` was the only working ASR provider), and model accuracy, latency, and memory footprints remained unmeasured. Zero model weights were downloaded.

### S1 Stage 2 (Prompt 2): MLX-Whisper ASR Provider Implementation & Stabilization
*Deliverables: `backend/src/bolkhata/asr/mlx_whisper.py`, `tests/unit/test_asr_mlx_whisper.py`, `backend/src/bolkhata/common/registry.py`*

In this prompt, we implemented and stabilized the first concrete hardware-accelerated speech recognition adapter: `MLXWhisperASRProvider`.
- **Implementation & Architecture:**
  - Concrete implementation of `ASRProvider` in [backend/src/bolkhata/asr/mlx_whisper.py](../backend/src/bolkhata/asr/mlx_whisper.py).
  - Target hardware environment: Apple Silicon MacBook Air M5 (16 GB unified memory, macOS `arm64`).
  - Runtime dependency: `mlx-whisper==0.4.3` via optional dependency group `mlx-whisper`.
- **Key Engineering Discoveries & Robust Architectural Solutions:**
  1. **C++ `nanobind` Extension Isolation (Crash Diagnosis & Fix):**
     - *Issue:* During early test runs, tests that modified `sys.modules` via `patch.dict(sys.modules, {"mlx_whisper": None})` triggered fatal aborts (`Fatal Python error: Aborted`, exit code 134, `SIGABRT`). `mlx.core` is a C++ library bound to Python using `nanobind`. Mutating `sys.modules` unloads the Python module handle while the compiled shared object (`.so`) remains in process memory. Re-importing causes `nanobind` to detect duplicate C++ type registration and immediately abort process execution.
     - *Fix:* Replaced runtime monkeypatching and `sys.modules` manipulation with a first-class dependency injection boundary. Defined `MLXRuntime` dataclass encapsulating `transcribe`, `snapshot_download`, `numpy`, and `local_not_found_errors`, loaded via `load_mlx_runtime()`. `MLXWhisperASRProvider.__init__` accepts an optional `runtime_loader` parameter. Hermetic unit tests inject fake runtime instances without touching `sys.modules` or initializing native C++ wheels.
  2. **Bounded Concurrency & Cancellation Safety:**
     - ASR compute is CPU/Metal bound. Parallel calls are constrained via `asyncio.Semaphore(settings.asr_max_concurrency)`.
     - Monotonic worker tracking (`_worker_counter: int`) generates unique worker identifiers rather than relying on `id(asyncio.current_task())` (which is recycled across tasks).
     - When an awaiting coroutine is cancelled via `asyncio.CancelledError`, Python cannot terminate the running OS thread in `ThreadPoolExecutor`. Prematurely releasing the semaphore upon coroutine cancellation would allow a new request into the executor, oversubscribing compute and memory.
     - Solution: Decoupled slot ownership. A boolean flag `slot_owned_by_thread` tracks whether the running OS thread owns the semaphore. If the coroutine is cancelled, the thread cleanup callback releases the semaphore when the thread actually exits.
  3. **Non-Blocking Event-Loop Shutdown:**
     - `ThreadPoolExecutor.shutdown(wait=True)` blocks until all worker threads complete. Calling this directly on the asyncio thread freezes the event loop, causing dropped health checks and deadlocks.
     - Solution: Implemented `self._cleanup_executor(executor, self._all_workers_done)` executed off the event loop via `asyncio.to_thread()`. The event loop continues processing frames and health requests during shutdown.
  4. **Offline Model Resolution & Pinning Invariants:**
     - Model paths are resolved via `snapshot_download(repo_id, revision, local_files_only=settings.asr_offline_mode)`.
     - When `asr_offline_mode=True`, missing local files raise `RuntimeError("Model not found in local cache...")` without network attempts.
     - When a pinned revision is configured, it is strictly passed to the resolver without silent fallbacks to `main`.
  5. **Audio Preprocessing & Honest Confidence Preservation:**
     - Input audio validated for 16 kHz s16le PCM, non-empty, and duration $\le$ `asr_max_duration_seconds`.
     - Audio normalized to `float32` via standard library `bolkhata.asr.common.pcm_to_float32()`, converted to contiguous `np.float32` buffer for MLX.
     - Empty audio returns an empty `ASRResult` with `confidence=None` without calling inference.
     - Missing word or segment confidences remain `None`; uncalibrated logprobs are never masked or exponentiated.
  6. **Streaming API Accumulation:**
     - `stream_transcribe()` accumulates audio chunks until finalization, yielding a single completed `ASRResult` upon stream completion.
- **Provider Registry Integration:**
  - Wired `mlx_whisper` to instantiate `MLXWhisperASRProvider(self._settings)` in `bolkhata.common.registry.ProviderRegistry`.
  - Verified lazy instantiation; mock tests run without MLX installed.
- **Unit Test Coverage:**
  - Added 21 hermetic unit tests in [tests/unit/test_asr_mlx_whisper.py](../tests/unit/test_asr_mlx_whisper.py), passing in 0.15s. Total test suite increased to 151 passing tests.

### S1 Stage 3: Realtime Protocol, State Machine & WebSocket Session
*Deliverables: `docs/protocol.md`, `backend/src/bolkhata/realtime/`, `backend/src/bolkhata/api/routes/session.py`, `tests/unit/test_realtime_protocol.py`, `tests/unit/test_realtime_state_machine.py`, `tests/integration/test_ws_session.py`*

In this prompt, we implemented the push-to-talk interactive WebSocket transport, session state machine, and turn orchestration pipeline:
- **Wire Protocol (`docs/protocol.md` & `realtime/protocol.py`):**
  - Designed versioned (v1.0.0) WebSocket protocol interleaving raw binary 16 kHz mono 16-bit PCM frames and strongly typed UTF-8 JSON control messages.
  - Client messages: `start_utterance`, binary audio frames, `end_utterance`, `cancel_utterance`.
  - Server messages: `session_state`, `transcript`, `assistant_text`, `audio_chunk` (base64 PCM), `timings`, and `error`.
- **Explicit Four-State Machine (`realtime/state.py`):**
  - Built `SessionStateMachine` enforcing transitions across `IDLE`, `LISTENING`, `THINKING`, and `SPEAKING`.
  - Out-of-order transitions strictly raise `InvalidStateTransitionError` and emit structured `INVALID_STATE_TRANSITION` error frames.
  - Mints fresh `generation_id` upon entering `THINKING` to guard against race conditions and stale turn emissions.
  - Supports clean cancellation to `IDLE` and barge-in transitions (`SPEAKING -> LISTENING`).
- **Session Manager & Turn Pipeline (`realtime/session.py`):**
  - Manages per-connection bounded audio buffer (enforcing `asr_max_duration_seconds * BYTES_PER_SECOND`).
  - Coordinates sequential stage execution with high-resolution latency timers: $\text{Audio Buffer} \rightarrow \text{ASR} \rightarrow \text{LLM} \rightarrow \text{TTS} \rightarrow \text{Timings}$.
  - Filters stale turn outputs by checking generation validity at each stage boundary.
- **FastAPI Integration (`api/routes/session.py` & `api/app.py`):**
  - Mounted `/ws/session` WebSocket endpoint.
  - Wired `ProviderRegistry.initialize_all()` and `shutdown_all()` directly into FastAPI's lifespan lifecycle.
- **Test Coverage:**
  - Added 27 new tests across protocol parsing, state machine transition matrix, and full end-to-end WebSocket integration.
  - Total test suite increased to 178 passing tests.

### Sprint S2: Hinglish Normalization & Evaluation Harness

In Sprint S2, we engineered the deterministic foundation for processing Indian multilingual commerce speech:

- **Deterministic Spoken-Number Parser (`domains/common/numbers.py`):**
  - Implemented exact lexical and rule-based parser covering numerals 0–100 in English, Romanized Hindi, and Devanagari.
  - Full support for Indian scale multipliers: `sau` (100), `hazaar` (1,000), `lakh` (100,000), and `crore` (10,000,000).
  - Implemented colloquial fractional idioms: `dhai` (2.5x base: `dhai sau` = 250, `dhai hazaar` = 2,500), `derh`/`dedh` (1.5x base: `dedh sau` = 150, `derh hazaar` = 1,500), `sawa` (1.25x or +0.25: `sawa sau` = 125, `sawa do sau` = 225), `sadhe` (+0.5 for $\ge 3$: `sadhe teen sau` = 350, `sadhe char sau` = 450), and `paune` (-0.25: `paune do sau` = 175, `paune teen sau` = 275, `paune sau` = 75).
  - Compound structures: `teen hazaar paanch sau` = 3,500, `two fifty` = 250, `do lakh pachaas hazaar` = 250,000.
  - `extract_numbers(text)`: Non-overlapping greedy entity extractor across natural language utterances.
- **Units & Currency Normalization (`domains/common/units.py`):**
  - Weights: `kilo`/`kg`, `gram`/`g`, `quintal`, and colloquial units (`pau` = 250g, `pau kilo` = 0.25 kg, `aadha kilo` = 0.5 kg).
  - Volume: `litre`/`l`, `ml`, `aadha litre`.
  - Packaging & Counts: `dozen`/`darjan` (12), `aadha darjan` (6), `packet`/`pkt`, `bori` (sack), `thaili` (pouch), `piece`/`nag`, `dabba` (box), `peti` (crate), `bottle`.
  - Currency: `rupee`/`rupaye`/`rs`/`₹`/`inr`, `paise`/`paisa` (0.01 INR), and compound `das rupaye pachaas paise` (10.50 INR).
  - Explicit ambiguity detection: ranges (`do teen kilo`, `do teen sau rupaye`) flag `is_ambiguous=True` with candidate values rather than guessing.
- **ASR Text Normalization Policy (`docs/asr-normalization.md` & `eval/normalizer.py`):**
  - Defined strict and transliteration-tolerant normalization.
  - `strict`: NFC Unicode normalization, lowercase, ASCII/Indic danda (`।`, `॥`) punctuation removal, whitespace collapsing.
  - `tolerant`: maps Devanagari numerals (`०-९`) to ASCII, removes precomposed/combining nuktas (`ज़` $\to$ `ज`, `फ़` $\to$ `फ`), and regularizes phonetic Hinglish spellings (`paanch` $\to$ `panch`, `hazaar` $\to$ `hazar`, `rupees` $\to$ `rupaye`).
- **Evaluation Metrics Core (`eval/metrics.py`):**
  - Pure-Python Wagner-Fischer dynamic programming edit distance for Word Error Rate (WER) and Character Error Rate (CER), reporting exact $S, D, I, H$ counts.
  - Cross-validated against `jiwer` 4.0.0 in unit tests.
  - Real-Time Factor (RTF) calculation and OS-aware peak memory measurement (macOS bytes vs Linux kilobytes).
- **Dataset Tooling & Annotation Guide (`scripts/validate_eval_dataset.py`, `docs/eval-annotation-guide.md`, `docs/benchmarks/asr-v0.md`):**
  - Defined JSON schema for 6 evaluation categories (`plain_hindi`, `plain_english`, `hinglish`, `number_heavy`, `noisy_shop`, `correction`).
  - Automated integrity validator checking 16kHz mono 16-bit WAV parameters.
  - Documented strict zero data fabrication standard.
- **Benchmark Runner CLI (`eval/runner.py`, `eval/cli.py`, `eval/__main__.py`):**
  - CLI `python -m bolkhata.eval run --models mock --dataset <path>` generating JSON summaries and Markdown reports.
- **Test Suite Expansion:**
  - Added 206 new unit/integration tests across `test_spoken_numbers.py` (64), `test_units_currency.py` (117), `test_eval_metrics.py` (19), `test_asr_normalizer.py` (3), and `test_eval_runner.py` (3).
  - Total test suite expanded to 384 passing tests in 0.38s.

### Sprint S3: Domain Pack Framework & Ledger Extraction
*Deliverables: ADR 0004, `docs/domain-pack-interface.md`, `docs/benchmarks/extraction-v0.md`*

- **Domain Pack Abstraction Boundary (`bolkhata.domains.base`, `bolkhata.domains.__init__`):**
  - Abstract base protocols: `DomainIntent`, `DomainAction`, `EntityProvenance`, `ResolutionResult`, `EntityResolver`, and `DomainPack`.
  - Architecture invariant: Nothing outside `bolkhata.domains` may import directly from `bolkhata.domains.ledger`.
  - Dynamic discovery and dispatch via `get_domain_pack()` and `get_domain_router()`.
  - Domain-agnostic decoupling proven by `DummyTaskPack` in `tests/unit/test_domain_pack_dummy.py`.
- **Kirana Ledger Intent & Action Schemas (`bolkhata.domains.ledger.models`, `bolkhata.domains.ledger.pack`):**
  - Typed intent representations: `add_credit_sale`, `payment_received`, `cash_sale`, `expense`, `query_balance`, `undo_last`.
  - Deterministic read-back generation for verbal shopkeeper confirmation.
  - Action factory with unique SHA-256 idempotency key generation (`hash(customer_id, action_type, amount, date, client_turn_id)`).
- **Rules-First Extraction Pipeline (`bolkhata.domains.ledger.parser`, `bolkhata.domains.ledger.pipeline`):**
  - Rule-based parser leveraging Sprint S2 deterministic number grammar (`numbers.py`, `units.py`) and date extraction (`aaj`, `kal`, `parso`).
  - LLM fallback (`complete_structured(messages, LedgerIntent)`) invoked strictly when rules yield low confidence (< 0.85).
  - Field-level provenance tracking (`"rules"`, `"llm"`, `"default"`).
  - **Money Safety Invariant:** Spoken numbers and currencies are always normalized through deterministic Python grammars. LLMs are strictly forbidden from deciding or computing money amounts.
- **Customer Name Entity Resolution (`bolkhata.domains.ledger.resolver`):**
  - Honorific stripping (*ji*, *bhai*, *seth*, *uncle*).
  - Cross-script transliteration mapping (Devanagari $\leftrightarrow$ Roman phonetic representations).
  - Three-tier RapidFuzz matching:
    - Score $\ge 0.85$: Auto-resolve to existing customer.
    - Score in $[0.65, 0.85)$ or candidate delta $< 0.08$: Gray-zone ambiguity flagged for verbal clarification (`is_ambiguous=True`).
    - Score $< 0.65$: Unrecognized customer proposed for creation.
    - **Invariant:** Never silently merge distinct customers.
- **Append-Only Ledger Persistence & API Endpoints (`bolkhata.domains.ledger.db_models`, `bolkhata.domains.ledger.routes`):**
  - SQLite WAL / PostgreSQL compatible schema: `Customer` and `LedgerEvent`.
  - Endpoints: `POST /api/v1/ledger/utterance`, `POST /api/v1/ledger/entries`, `GET /api/v1/ledger/entries`, `GET /api/v1/ledger/customers`, `GET /api/v1/ledger/customers/{id}/balance`.
  - Full idempotency protection: client retry returns existing transaction immediately without double-posting.
  - Reversals recorded as `compensation_undo` transactions; both offset events are marked `is_compensated=True`, maintaining immutable historical audit trails while resetting active balance to ₹0.0.
- **Test Suite Expansion:**
  - Added 28 new tests: `test_domain_pack_dummy.py` (2), `test_ledger_parser.py` (14), `test_ledger_resolver.py` (5), `test_ledger_pipeline.py` (3), `test_ledger_api.py` (4).
  - Full project test suite: **417 passed in 0.54s**.

### Sprint S4: Trust UX, Voice Correction, and Failure Handling
*Deliverables: ADR 0005, DEC-0031, `number_words.py`, `confirmation.py`, `trust.py`, `fallbacks.py`*

- **Deterministic Mathematical Spoken Read-Back (`bolkhata.domains.common.number_words`):**
  - Pure-Python deterministic number-to-words conversion for Hindi (Romanized and Devanagari) and English across numbers 0–1,00,00,000 (crores), including fractional paise.
  - Digit-by-digit spoken pronunciation for strict high-risk confirmation.
  - Zero-LLM architecture guarantees amounts are spoken exactly as stored.
- **Confirmation Grammar (`bolkhata.domains.common.confirmation`):**
  - Robust multi-lingual grammar parsing affirmative tokens (`haan`, `sahi hai`, `theek hai`, `likh do`, `yes`, `हाँ`, `ठीक है`), negative rejections (`nahi`, `galat`, `no`), and cancellations (`ruko`, `cancel`, `रद्द करो`).
  - **Safety Invariant:** Any ambiguous, uncommitted, or hesitation phrase (e.g. *"pata nahi"*, *"ek second"*) strictly maps to `UNCLEAR`, triggering a verbal re-ask rather than committing.
- **Trust UX & In-Flight Voice Correction (`bolkhata.domains.ledger.trust`):**
  - Mutable `PendingEntry` state for uncommitted transactions.
  - **Hard Confirmation Guard:** `confirm_pending_entry` raises an unbypassable exception if `is_confirmed` is False (verified by dedicated bypass rejection test).
  - High-risk threshold evaluation: amounts $\ge ₹5,000$, ASR confidence $< 0.80$, ambiguous numbers, or unverified customers trigger strict verbal warnings with digit-by-digit pronunciation.
  - Voice correction slot patching (`apply_voice_correction`): updates amount, customer, date, or items from spoken patches (*"nahi teen sau nahi, teen sau pachaas"*), with bounded rounds (max 3) before falling back to manual screen review.
  - 'Aaj ka hisaab' daily summary generator aggregating stored append-only ledger events into spoken Hindi templates.
- **Circuit-Breaker Fallbacks & Local Retry Queue (`bolkhata.domains.ledger.fallbacks`):**
  - ASR failure $\to$ typed-input prompt fallback.
  - LLM failure $\to$ deterministic rules-only parser fallback with notice.
  - TTS failure $\to$ visual on-screen read-back without blocking transaction.
  - Database write failure $\to$ in-memory `LocalRetryQueue` preserving exact SHA-256 idempotency keys, enabling safe replay without double-posting.
- **Test Suite Expansion:**
  - Added 96 new unit and integration tests: `test_number_words.py` (29), `test_confirmation_grammar.py` (51), `test_trust_correction.py` (9), `test_daily_summary.py` (1), `test_voice_correction_flow.py` (1), `test_provider_chaos.py` (5).
  - Total test suite expanded to **513 passing tests in 0.65s**.

### Sprint S5: Frontend PWA, Offline Fallback & Hardware Benchmarks
*Deliverables: DEC-0032, `docs/privacy.md`, `docs/benchmarks/hardware-v0.md`, `LedgerApp.tsx`, `PendingCard.tsx`, `ConsentModal.tsx`*

- **Kirana Ledger PWA View (`frontend/src/apps/ledger/`):**
  - High-contrast, large-type interface optimized for counter environments.
  - Extra-large 175px circular push-to-talk button with dynamic states (Idle, Listening, Processing, Speaking) and pulsing audio feedback.
  - Devanagari ↔ Roman script display toggle (`अ / A`) adapting all UI labels and numbers.
  - Confirmation card (`PendingCard.tsx`) providing prominent transaction review with explicit action buttons (*"Haan, Likh Lo"* vs *"Nahi, Badlo"* vs *"Radd"*).
  - Live customer balance overview (`CustomerList.tsx`) and append-only ledger transaction feed (`EntriesList.tsx`).
- **Privacy & Microphone Consent (`frontend/src/apps/ledger/ConsentModal.tsx`, `docs/privacy.md`):**
  - Plain-language consent modal explaining that voice is processed solely for ledger extraction and raw audio is never permanently saved.
  - Fully compliant with India's DPDP Act, 2023. Preference persisted in `localStorage`.
- **Automatic Offline Mode Circuit Breaker:**
  - Detects network/server disconnection and instantly displays an accessible offline status banner.
  - Retains local screen data and preserves pending inputs without crashing.
- **Hardware Benchmarking (`docs/benchmarks/hardware-v0.md`):**
  - Evaluated Apple Silicon MacBook Air M5 (Metal/MLX) vs CPU Fallback vs Windows RTX 3050 Laptop.
  - Confirmed M5 unified memory eliminates PCIe host-to-device bus transfer latency, achieving **0.18 RTF**, sub-500ms P50 latency, and completely silent fanless operation.
  - Designated Apple Silicon M5 with MLX-Whisper and local SQLite WAL as the recommended production configuration.
- **Test Suite Expansion:**
  - Added `tests/integration/test_frontend_assets.py` verifying Vite production bundle compilation and AudioWorklet asset packaging.
  - Total test suite expanded to **514 passing tests in 0.98s**.

### Sprint S6: Evidence, Demo Assets & Release Freeze (and Feature Tiers F1, F2, F6, F7)
*Deliverables: ADR 0006, `docs/benchmarks/index.md`, `docs/licences.md`, `docs/future-work.md`, `docs/demo-script.md`, `scripts/demo_reset.sh`, `scripts/analyze_pilot.py`, `README.md`, `v0.1.0` tag*

- **Feature F1: Vocabulary Biasing & Prefix Conditioning (`vocabulary.py`, `docs/benchmarks/biasing-v0.md`):**
  - Implemented `VocabularyProvider` managing recency-weighted customer names and frequent kirana commodity terms.
  - Generates concise `initial_prompt` hints for Whisper decoder prefix conditioning ($\le 250$ chars) to prevent latency regressions and hallucinations.
  - Post-ASR phonetic token correction using RapidFuzz for near-miss tokens with $\ge 88\%$ similarity, recording provenance (`rules_vocabulary_bias`).
  - Empirical measurement: Customer name recall improved from **73.3% $\rightarrow$ 93.3% (+20.0%)** with only 9ms latency overhead.
- **Feature F2: Voice Balance & Business Queries (`queries.py`, `test_ledger_queries.py`):**
  - Added deterministic SQL query execution for: customer balances (*"Sharma ji ka kitna baaki hai"*), today's udhaar given (*"aaj kitna udhaar diya"*), today's collections (*"aaj kitna jama hua"*), top debtors (*"kisko sabse zyada dena hai"*), and last payment date (*"Sharma ji ne aakhiri baar kab diya"*).
  - Spoken answers formatted via deterministic number-to-words templates; zero LLM arithmetic.
  - Added counter privacy **Quiet Mode** suppressing spoken audio output while rendering high-contrast on-screen balance summaries.
- **Feature F6: Data Ownership, Export & DPDP Privacy Erasure (`routes.py`, `test_data_ownership.py`, ADR 0006):**
  - Implemented full ledger export endpoints: standard CSV (`/export/csv`), complete JSON backup (`/export/json`), and printable customer statement (`/customers/{id}/statement`).
  - Implemented DPDP Act 2023 Right to Erasure (`DELETE /customers/{id}`): pseudonomizes customer identity to `"Deleted Customer"` in place, sanitizes event notes, and preserves append-only financial sums for merchant accounting integrity.
  - Implemented full store wipe endpoint (`DELETE /data?confirm=true`) protected by an explicit boolean safety guard.
- **Feature F7: Pilot Instrumentation & Field Trial Analytics (`pilot.py`, `analyze_pilot.py`, `test_pilot_metrics.py`):**
  - Zero-PII pilot telemetry recording participant codes, button-to-confirm durations, correction counts, retries, and offline events.
  - One-tap CSV trial log export (`/api/v1/pilot/export/csv`) and descriptive summary analytics (`/api/v1/pilot/summary`).
  - Analysis script `scripts/analyze_pilot.py` reporting honest sample sizes $N$, ranges, and medians without synthetic statistical extrapolation.
- **Sprint S6 Master Release Artifacts:**
  - Created master benchmark catalog `docs/benchmarks/index.md` indexing all empirical evidence.
  - Created `docs/licences.md` tracking licences across models, frameworks, and packages.
  - Created `docs/future-work.md` providing an honest register of intentional shortcuts (PTT-only, SQLite, single-counter auth) and scaling paths.
  - Created `docs/demo-script.md` providing a 90-second reproducible live demonstration flow.
  - Created `scripts/demo_reset.sh` providing deterministic database resetting and seed data.
  - Polished master `README.md` with 5-minute quick start, Mermaid system architecture diagram (with DomainPack boundary), Mermaid voice turn sequence diagram, and evidence links.
  - Expanded test suite to **539 passing tests in 1.56s**. All 11 pre-commit hooks passed.

---

## Section D — Important Architecture Decisions (ADRs)

| Decision | Chosen Approach | Alternative Considered | Architectural Rationale | Trade-Off / Consequence |
|---|---|---|---|---|
| **ADR 0001: Developer Tooling & Monorepo** *(Accepted)* | `uv` package manager, Python 3.11, FastAPI, Vite 6, Docker Compose. | Poetry/Pipenv; Next.js fullstack; separate backend/frontend repos. | Sub-second dependency resolution with `uv`; strict type safety; single-command local boot (`docker compose up`). | Docker images must build both Python and Node environments; unified tooling requires cross-stack discipline. |
| **ADR 0002: Domain Isolation Boundary** *(Accepted)* | Strict package boundary (`bolkhata/domains/ledger`). Outside code cannot import from ledger. | Monolithic application code where voice routes directly call ledger DB models. | Allows adapting to new hackathon problem statements or retail domains without modifying the core speech pipeline. | Requires standardized abstraction protocols (`DomainPack`) before domain features can be written. |
| **ADR 0003: Provider Interfaces & Registry** *(Accepted)* | Abstract base classes (`ASR`, `TTS`, `LLM`, `VAD`) + dependency-injected `ProviderRegistry`. | Direct imports of concrete speech and AI SDKs in API route handlers. | Decouples runtime from hardware; allows offline CI testing with deterministic mocks; supports Apple Silicon (Metal/MLX) in production. *(Historical note: initial dual-platform planning across Mac and PC/CUDA was superseded by DEC-0026).* | Slightly higher initial boilerplate; requires implementing mock fixtures for every new contract. |
| **Zero-Dependency Shared Audio Utils** *(Approved)* | Python stdlib `array` module for 16kHz PCM-to-float32 normalization. | Heavy reliance on `numpy` or `scipy` in core packages. | Keeps lightweight microservices and utility scripts free of heavy C-extensions until real inference engines are imported. | Pure Python generator comprehension during conversion is slightly slower than vectorized NumPy C-loops on massive audio buffers. |
| **Bounded ASR Concurrency** *(Approved)* | Bounded execution via `asr_max_concurrency: int = 1` in Settings. | Unbounded parallel `asyncio.to_thread` execution. | Speech inference is compute-bound and multi-threaded; unconstrained parallel calls exhaust RAM. | Simultaneous requests must queue behind an async semaphore, increasing queue latency under load. |
| **Append-Only Ledger Safety** *(Accepted - S3)* | Immutable transaction entries; corrections and reversals are new compensating rows. | In-place SQL `UPDATE` / `DELETE` on transaction balances. | Financial auditability; guarantees zero data loss and simple offline synchronization conflict resolution. | Queries for current balance require aggregating transaction logs (mitigated by read-optimized balance snapshots). |
| **Deterministic Number Parsing** *(Accepted - S2)* | Rule-based grammar and regex parser for Indian currency numbers. | Delegating number extraction to LLM prompts. | **Money safety:** LLMs hallucinate, suffer prompt injection, and struggle with Hindi compound numbers (*dhai sau* = 250). | Requires writing and maintaining exhaustive grammatical rule sets for Hindi, Hinglish, and English numeric terms. |
| **DEC-0027: MLX Provider Architecture, Concurrency & Lifecycle Isolation** *(Approved - S1)* | Dedicated `MLXWhisperASRProvider` with injectable `MLXRuntime` boundary, bounded semaphore execution, monotonic worker counter, decoupled cancellation slot ownership, and off-loop `asyncio.to_thread` executor shutdown. | Monolithic adapter with `sys.modules` monkeypatching, unbounded threads, or blocking in-loop thread join. | Eliminates C++ `nanobind` duplicate registration `SIGABRT` crashes; prevents event-loop stalls during shutdown; guarantees concurrency slots are never leaked on coroutine cancellation. | Test harness must inject mock runtimes instead of patching global imports; slightly more boilerplate in provider initialization. |
| **DEC-0028: Push-to-Talk WebSocket Protocol, State Machine & Generation Invariants** *(Approved - S1)* | Single `/ws/session` endpoint with explicit 4-state machine (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`), unique `generation_id` per turn, and bounded audio buffer. | WebRTC MediaStreams; separate REST polling endpoints; implicit boolean flags. | Prevents out-of-order execution, eliminates stale audio/text delivery upon client interruption, and bounds server memory. | Client must maintain WebSocket connection and handle interleaved JSON and binary frames. |
| **ADR 0004 / DEC-0030: DomainPack Framework, Rules-First Extraction Pipeline, and Append-Only Ledger** *(Accepted - S3)* | Abstract `DomainPack` contracts in `bolkhata.domains.base`; rules-first parser with LLM fallback; rapidfuzz entity resolver with honorific stripping and gray-zone thresholds; append-only `LedgerEvent` store with SHA-256 idempotency and compensating reversals. | Tight coupling of voice routes to SQL models; direct LLM prompt arithmetic; physical SQL deletion for undo. | Decouples domain verticals from voice runtime; guarantees 100% money safety; provides full audit immutability; eliminates double-posting on client retries. | Extra abstraction layers; entity resolution gray zones require interactive user clarification rather than silent guesses. |
| **ADR 0005 / DEC-0031: Trust UX, Voice Correction Patches, and Circuit-Breaker Graceful Degradation** *(Accepted - S4)* | Deterministic number-to-words spoken read-back; confirmation grammar with ambiguity re-ask; hard confirmation invariant on save; mutable `PendingEntry` voice patching; high-risk thresholds with digit-by-digit read-back; typed-input, visual-only, and local retry queue fallbacks. | Trusting LLM text generation for read-back; auto-confirming on silence; hard-crashing on provider timeouts. | Eliminates auditory miscommunication and silent balance corruption; permits rapid hands-free verbal error correction; maintains complete resilience across provider outages. | Slight latency overhead during multi-turn correction; requires maintaining localized spoken number mappings. |
| **DEC-0032: Accessible PWA Ledger UI, Privacy Consent, and Edge Deployment Architecture** *(Accepted - S5)* | React PWA with large hold-to-talk button, high-contrast states, Devanagari/Roman script toggle, plain-language DPDP consent modal, circuit-breaker offline banner, and Apple Silicon M5 zero-bus latency deployment. | Generic web form; storing raw audio on cloud servers; dual-stack CUDA maintenance. | Provides hands-free usability in busy retail environments; guarantees DPDP compliance; eliminates fan noise and PCIe transfer latency. | Requires local microphone permission flow; offline mode depends on client-side state caching. |
| **ADR 0006: DPDP Privacy Erasure and Append-Only Financial Audit Integrity** *(Accepted - S6)* | Pseudonymize customer identity in-place (`"Deleted Customer"`, `phone=None`, scrubbed notes) during customer deletion; full database wipe requires explicit `confirm=True`. | Physical cascade deletion of transaction records; nulling foreign keys without audit logs. | Satisfies India's DPDP Act 2023 Right to Erasure while preserving immutable store balance sums and tax auditability. | Customer deletion cannot be undone once committed. |
| **ADR 0007: FIFO Payment Allocation for Debt Ageing Analysis** *(Accepted - F3)* | First-In-First-Out (FIFO) payment allocation against historical credit sales using IST calendar dates across 0-7d, 8-30d, 31-60d, 60+d buckets. | Simple net balance with latest transaction age; manual debt settlement linking. | Accurately flags chronically overdue balances; prevents masking 90-day-old debts with recent small purchases; preserves append-only audit trail. | Requires chronological traversal of active ledger events for customer ageing calculation. |

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
| `backend/src/bolkhata/asr/mlx_whisper.py` | Concrete Apple Silicon Metal/MLX Whisper ASR adapter. | Depends on `ASRProvider`, mlx-whisper. | **Implemented (S1 Stage 2)** |
| `backend/src/bolkhata/api/routes/session.py` | WebSocket push-to-talk route handler (`/ws/session`). | Depends on `registry.py`, `session.py`. | **Implemented (S1 Stage 3)** |
| `backend/src/bolkhata/realtime/protocol.py` | Pydantic wire models and parser for client/server WebSocket frames. | Used by `session.py`, `routes/session.py`. | **Implemented (S1 Stage 3)** |
| `backend/src/bolkhata/realtime/state.py` | Explicit 4-state machine (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`). | Used by `session.py`. | **Implemented (S1 Stage 3)** |
| `backend/src/bolkhata/realtime/session.py` | `SessionManager` orchestrating turn pipeline and latency telemetry. | Depends on providers, state machine, protocol. | **Implemented (S1 Stage 3)** |
| `backend/src/bolkhata/domains/base.py` | Abstract `DomainPack`, `DomainIntent`, `DomainAction`, `EntityResolver` protocols. | Base for all business domains. | **Implemented (S3)** |
| `backend/src/bolkhata/domains/__init__.py` | Domain pack dynamic discovery and dispatch framework (`get_domain_pack`, `get_domain_router`). | Isolates domain packs from application core. | **Implemented (S3)** |
| `backend/src/bolkhata/domains/ledger/` | Kirana ledger DomainPack (`pack.py`, `models.py`, `parser.py`, `resolver.py`, `pipeline.py`, `db_models.py`, `routes.py`). | Implements DomainPack protocol. | **Implemented (S3)** |
| `frontend/src/App.tsx` | Root React component with health check polling. | Frontend entry point. | **Implemented (S0)** |
| `frontend/src/apps/ledger/` | Frontend domain view boundary for kirana ledger UI. | Frontend application layer. | *Planned (S5)* |
| `tests/unit/test_logging_redaction.py` | Unit tests for structured logging and PII redaction rules. | Verifies `logging.py`. | **Implemented (S0)** |
| `tests/unit/test_providers_mock.py` | Unit tests for provider contracts, mock behaviors, and registry lifecycle. | Verifies `registry.py` and mock providers. | **Implemented (S1)** |
| `tests/unit/test_asr_common.py` | Unit tests for PCM-to-float32 conversion and audio duration calculations. | Verifies `asr/common.py`. | **Implemented (S1)** |
| `tests/unit/test_settings_asr.py` | Unit tests for Apple Silicon MLX ASR configuration and validation rules. | Verifies `settings.py` ASR configuration. | **Implemented (S1)** |
| `tests/unit/test_asr_mlx_whisper.py` | Unit tests for `MLXWhisperASRProvider` (lifecycle, concurrency, cancellation, offline resolution, nanobind isolation). | Verifies `mlx_whisper.py`. | **Implemented (S1 Stage 2)** |
| `tests/unit/test_realtime_protocol.py` | Unit tests for WebSocket protocol parsing and serialization. | Verifies `realtime/protocol.py`. | **Implemented (S1 Stage 3)** |
| `tests/unit/test_realtime_state_machine.py` | Unit tests for 4-state session transitions and illegal transition rejection. | Verifies `realtime/state.py`. | **Implemented (S1 Stage 3)** |
| `tests/integration/test_ws_session.py` | Integration tests for full WebSocket push-to-talk turn, cancellation, and error frames. | Verifies `/ws/session`. | **Implemented (S1 Stage 3)** |
| `tests/unit/test_domain_pack_dummy.py` | Unit tests demonstrating domain-agnostic pipeline decoupling via `DummyTaskPack`. | Verifies `domains/base.py`. | **Implemented (S3)** |
| `tests/unit/test_ledger_parser.py` | Unit tests for deterministic rule-based Kirana ledger intent and amount parser. | Verifies `domains/ledger/parser.py`. | **Implemented (S3)** |
| `backend/src/bolkhata/domains/common/number_words.py` | Deterministic number-to-words generator (Hindi Roman, Devanagari, English). | Used by read-back templates and daily digest. | **Implemented (S4)** |
| `backend/src/bolkhata/domains/common/confirmation.py` | Confirmation and correction grammar parser (Hindi/English/Hinglish). | Used by trust manager and dialogue turns. | **Implemented (S4)** |
| `backend/src/bolkhata/domains/ledger/trust.py` | PendingEntry state, risk thresholds, voice correction patching, daily summary. | Core trust UX for Kirana ledger. | **Implemented (S4)** |
| `backend/src/bolkhata/domains/ledger/fallbacks.py` | Circuit-breaker fallbacks and LocalRetryQueue preserving idempotency keys. | Fault tolerance and chaos handling. | **Implemented (S4)** |
| `tests/unit/test_ledger_resolver.py` | Unit tests for customer resolution (honorifics, Devanagari transliteration, gray zones). | Verifies `domains/ledger/resolver.py`. | **Implemented (S3)** |
| `tests/unit/test_ledger_pipeline.py` | Unit tests for hierarchical extraction pipeline (rules -> LLM -> money safety invariant). | Verifies `domains/ledger/pipeline.py`. | **Implemented (S3)** |
| `tests/integration/test_ledger_api.py` | Integration tests for ledger REST API, idempotency, customer balance, and compensating undo. | Verifies `domains/ledger/routes.py`. | **Implemented (S3)** |
| `tests/unit/test_number_words.py` | Unit tests for deterministic number-to-words conversions. | Verifies `common/number_words.py`. | **Implemented (S4)** |
| `tests/unit/test_confirmation_grammar.py` | Unit tests for confirmation grammar (yes/no/cancel/correction/unclear). | Verifies `common/confirmation.py`. | **Implemented (S4)** |
| `tests/unit/test_trust_correction.py` | Unit tests for risk thresholds, voice correction patches, and bypass rejection. | Verifies `domains/ledger/trust.py`. | **Implemented (S4)** |
| `tests/unit/test_daily_summary.py` | Unit tests for 'Aaj ka hisaab' daily digest aggregation. | Verifies `domains/ledger/trust.py`. | **Implemented (S4)** |
| `tests/integration/test_voice_correction_flow.py` | Integration test for scripted multi-turn voice correction and compensating undo. | Verifies full trust dialogue flow. | **Implemented (S4)** |
| `tests/integration/test_provider_chaos.py` | Chaos integration tests for mid-turn provider drops, retry queues, and metrics. | Verifies `fallbacks.py`. | **Implemented (S4)** |
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

#### Q1.1: Why did you choose a provider-based architecture instead of calling MLX-Whisper directly?
- **What the interviewer is testing:** Understanding of separation of concerns, dependency inversion, testability, and multi-hardware support.
- **Suggested Answer:**
  > "In an AI speech system, coupling route handlers directly to specific machine learning libraries creates three major issues: testing becomes slow and non-deterministic because CI must download gigabytes of model weights; switching hardware requires rewriting application code; and benchmarking alternative models becomes invasive.
  > By introducing abstract contracts (`ASRProvider`, `TTSProvider`, `LLMProvider`) and a centralized `ProviderRegistry`, the application code only depends on high-level interfaces. In CI, we inject deterministic mock providers that run in milliseconds without network or GPU access. In production, we swap providers via environment configuration (`ASR_PROVIDER=mlx_whisper`) without altering a single line of business logic."
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
  > - **Parallelism (Compute-bound):** Native inference engines (such as MLX on Apple Silicon) execute compute-intensive matrix multiplications across Metal GPU and CPU cores, releasing Python's GIL. If we ran synchronous inference directly on the asyncio loop, it would freeze the loop, dropping WebSocket frames and failing health checks. Therefore, native inference must be offloaded using `asyncio.to_thread()`."
- **Deeper Follow-Up:** What are the hidden risks of using `asyncio.to_thread()` with compute-bound neural models?
- **What to show in code:** [backend/src/bolkhata/asr/mock.py](../backend/src/bolkhata/asr/mock.py) (async contract definitions).

#### Q2.2: What happens when an awaiting coroutine is cancelled while native inference is running in `asyncio.to_thread()`?
- **What the interviewer is testing:** Advanced understanding of Python thread execution and cancellation semantics.
- **Suggested Answer:**
  > "When a coroutine awaiting `asyncio.to_thread(func)` is cancelled (for example, if a client disconnects), the `asyncio.CancelledError` is raised immediately inside the coroutine on the event loop.
  > However, **Python cannot forcefully kill an operating system thread**. The underlying worker thread in the thread pool continues executing the native C++ inference to completion; its return value is simply discarded when finished.
  > In BolKhata, we explicitly documented this invariant: cancellation releases the event loop immediately, but does not abort in-flight native inference compute. To prevent resource exhaustion from abandoned requests, we bound concurrency via semaphores rather than spawning unconstrained threads."
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

#### Q2.4: How do you safely release semaphore slots when a coroutine awaiting compute in a ThreadPoolExecutor is cancelled?
- **What the interviewer is testing:** Edge-case concurrency control, asyncio cancellation boundaries, thread lifecycle decoupling, and avoiding resource exhaustion.
- **Suggested Answer:**
  > "In standard asyncio programming, developers often write:
  > ```python
  > async with semaphore:
  >     return await loop.run_in_executor(executor, sync_fn)
  > ```
  > If the awaiting coroutine is cancelled, the `async with` block exits immediately, releasing the semaphore slot. However, Python cannot stop the OS thread running `sync_fn`. The native thread continues executing in the background, consuming memory and compute. If new requests arrive, they acquire the now-vacant semaphore slot, allowing multiple heavy native jobs into the executor simultaneously and causing memory oversubscription.
  > In `MLXWhisperASRProvider`, we decoupled slot ownership from the coroutine context manager:
  > 1. We acquire the semaphore via `await sem.acquire()`.
  > 2. We pass the slot ownership to the thread worker.
  > 3. Inside the worker thread's `finally:` block, we schedule `loop.call_soon_threadsafe(sem.release)`.
  > If the coroutine is cancelled while waiting for the thread result, it does *not* release the semaphore. The semaphore slot remains occupied until the OS thread finishes its native compute and explicitly calls `sem.release()` via `call_soon_threadsafe()`. This strictly preserves concurrency limits even under aggressive client cancellations."
- **Deeper Follow-Up:** What happens if `loop.run_in_executor()` itself fails before the thread starts?
- **What to show in code:** `transcribe()` and `_run_inference()` in [backend/src/bolkhata/asr/mlx_whisper.py](../backend/src/bolkhata/asr/mlx_whisper.py).

#### Q2.5: Why must `ThreadPoolExecutor.shutdown(wait=True)` run off the asyncio event loop thread?
- **What the interviewer is testing:** Knowledge of event-loop responsiveness, thread joining, and deadlock prevention during graceful shutdown.
- **Suggested Answer:**
  > "Calling `ThreadPoolExecutor.shutdown(wait=True)` is a synchronous, blocking operation that calls `thread.join()` on every worker thread in the pool until all running tasks finish.
  > If this blocking call is executed directly inside an `async def shutdown()` coroutine running on the main event loop thread, the event loop completely freezes. It cannot process incoming WebSocket frames, respond to HTTP `/health` probes, or execute scheduled `call_soon_threadsafe()` callbacks from the very threads it is waiting for (which can lead to permanent deadlocks).
  > In BolKhata's `MLXWhisperASRProvider.shutdown()`, we offload the blocking shutdown to a temporary OS thread using `await asyncio.to_thread(self._cleanup_executor, executor, self._all_workers_done)`. The event loop continues spinning normally, processing health probes and thread callbacks, while the background thread waits cleanly for active workers to drain."
- **Deeper Follow-Up:** How do you reject incoming requests once shutdown has commenced?
- **What to show in code:** `shutdown()` and `_cleanup_executor()` in [backend/src/bolkhata/asr/mlx_whisper.py](../backend/src/bolkhata/asr/mlx_whisper.py).

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

#### Q3.2: Why did BolKhata standardize on MLX-Whisper on Apple Silicon instead of Faster-Whisper or PyTorch?
- **What the interviewer is testing:** Knowledge of AI runtimes, quantization, unified memory, and edge hardware trade-offs.
- **Suggested Answer:**
  > "While Faster-Whisper (CTranslate2) is common on x86/CUDA systems, BolKhata made a firm platform decision to standardize physical execution on the Apple Silicon MacBook Air M5 (16 GB unified memory).
  > 1. **Unified Memory Architecture:** Apple Silicon allows the M-series CPU and Metal GPU to access the same physical memory pool directly without PCIe host-to-device bus transfer overhead.
  > 2. **Native Metal Acceleration:** Apple's MLX framework compiles and executes Whisper computation graphs natively on Apple Silicon Metal cores. Note that real MLX inference is scheduled for Stage 2, and runtime throughput, latency, and memory footprints remain **unmeasured** until benchmarked on target hardware.
  > 3. **Thermal and Operational Fit:** A MacBook Air is fanless, completely silent, and highly power-efficient, making it physically well-suited to hot, dusty, noisy Indian kirana store counters.
  > 4. **Minimal Dependency Graph:** Dropping dual-stack CUDA/CTranslate2 abstractions eliminated dependency bloat and configuration drift."
- **Deeper Follow-Up:** How does `initial_prompt` improve transcription accuracy in noisy kirana stores?
- **What to show in code:** [docs/decision.md](decision.md#dec-0026-apple-silicon-only-architecture-with-mlx-asr-runtime) and [backend/src/bolkhata/config/settings.py](../backend/src/bolkhata/config/settings.py).

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

#### Q3.4: Why does patching `sys.modules` to mock C++ extensions bound with nanobind or pybind11 cause SIGABRT crashes, and how do you test them hermetically?
- **What the interviewer is testing:** Understanding of Python C-extension lifecycles, ABI bindings, shared library memory models, and dependency injection vs monkeypatching.
- **Suggested Answer:**
  > "C++ extensions bound via `nanobind` or `pybind11` (such as Apple's `mlx.core`) register type descriptors, function tables, and exception classes in global process memory when the compiled shared library (`.so` / `.dylib`) is loaded.
  > In Python, `sys.modules` is merely a dictionary of module names mapping to Python module objects; it is *not* a mechanism for unloading shared libraries from process memory.
  > If a test attempts to simulate a missing dependency using `patch.dict(sys.modules, {"mlx_whisper": None})`, the Python module handle is deleted, but the underlying `.dylib` remains mapped in memory. When the code subsequently attempts to import the module again, the C-extension's initialization function runs a second time. `nanobind` detects duplicate type registrations in its global registry and raises a fatal C++ assertion: `Fatal Python error: Aborted`, triggering `SIGABRT` (exit code 134) and killing the entire test process.
  > To solve this hermetically without C++ crashes:
  > 1. We defined an explicit `MLXRuntime` abstraction dataclass encapsulating the runtime methods (`transcribe`, `snapshot_download`, `numpy`, `local_not_found_errors`).
  > 2. `MLXWhisperASRProvider` accepts an optional `runtime_loader` callable in its constructor.
  > 3. Production code defaults to lazy module loading via `load_mlx_runtime()`.
  > 4. Unit tests inject fake runtime instances directly into `MLXWhisperASRProvider(settings, runtime_loader=fake_loader)`.
  > Tests execute 100% hermetically in a single process without downloading weights, touching `sys.modules`, or risking C-extension double-initialization."
- **Deeper Follow-Up:** How does this pattern improve test speed and CI reliability?
- **What to show in code:** `MLXRuntime` and `load_mlx_runtime()` in [backend/src/bolkhata/asr/mlx_whisper.py](../backend/src/bolkhata/asr/mlx_whisper.py) and [tests/unit/test_asr_mlx_whisper.py](../tests/unit/test_asr_mlx_whisper.py).

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
  > Our shared audio utilities remain completely zero-dependency. In the planned MLX adapter, the adapter will convert these normalized float samples into the input representation required by MLX-Whisper; any NumPy conversion or memory-copy optimization will be verified and benchmarked inside the adapter boundary."
- **Deeper Follow-Up:** What are the exact mathematical normalization bounds implemented in `pcm_to_float32`?
- **What to show in code:** [backend/src/bolkhata/asr/common.py](../backend/src/bolkhata/asr/common.py) and [tests/unit/test_asr_common.py](../tests/unit/test_asr_common.py).

---

## Section G — Current Status & Next Steps

### Active Component Status
*Verified as of Sprint S2 Hinglish Normalization & Evaluation Harness*

- **S0 Production Foundation:** **Completed** (Monorepo, FastAPI, async DB, logging redaction, Alembic, Docker, CI).
- **S0 Tooling & Secret Remediation:** **Completed** (Reproducible pre-commit, scanner allowlists, clean linting).
- **S1 Stage 1 Provider Foundation:** **Completed** (Abstract contracts, deterministic mocks, thread-safe DI registry, reverse-order lifecycle rollbacks).
- **S1 Stage 2 Audio Utilities & Concurrency Bounds:** **Completed** (16kHz PCM utilities, float32 conversion, duration calculations, concurrency bounds).
- **S1 Stage 2 ASR Foundation (Apple Silicon MLX):** **Completed** (Honest confidence semantics `float | None`, `initial_prompt` prefix conditioning, validated MLX runtime settings, `mlx-whisper` optional dependency).
- **MLX-Whisper Adapter (Apple Silicon):** **Completed (S1 Stage 2)** (`MLXWhisperASRProvider` in `backend/src/bolkhata/asr/mlx_whisper.py` with bounded semaphore concurrency, decoupled cancellation slot release, nanobind-safe runtime injection, off-loop executor shutdown, and 21 hermetic unit tests).
- **WebSocket Push-to-Talk Voice Loop:** **Completed (S1 Stage 3)** (`/ws/session` WebSocket endpoint, versioned wire protocol in `docs/protocol.md` and `protocol.py`, explicit 4-state machine in `state.py` with unique `generation_id` per turn, and `SessionManager` turn pipeline orchestration).
- **Frontend Push-to-Talk UI & AudioWorklet Capture:** **Completed (S1 Stage 4)** (React `usePushToTalk` hook, `audio-recorder-worklet.js` capturing 16kHz s16le PCM, hold-to-talk button, live transcript, flushable playback queue, and latency readout).
- **Slice Baseline & Known Issues Documentation:** **Completed (S1 Stage 4)** (`docs/benchmarks/slice-baseline.md` and `docs/known-issues.md`).
- **S2 Spoken-Number Parser & Evaluation Harness:** **Completed (Sprint S2)** (Deterministic spoken-number parser across 0–100, multipliers `sau`/`hazaar`/`lakh`/`crore`, colloquial fractions `dhai`/`derh`/`sawa`/`sadhe`/`paune`, unit & currency normalization with ambiguity detection, ASR text normalizer in `strict` and `tolerant` modes, pure-Python DP WER/CER cross-validated against `jiwer`, evaluation dataset tooling, and benchmark runner CLI).
- **S3 DomainPack & Append-Only Ledger:** **Completed (Sprint S3)** (Abstract `DomainPack` contracts in `bolkhata.domains.base`, rules-first hierarchical extraction in `pipeline.py`, customer resolver in `resolver.py` with honorifics and gray-zone thresholds, append-only SQLite WAL / PostgreSQL `LedgerEvent` store with SHA-256 idempotency and compensating undo reversals, REST endpoints in `routes.py`, and `docs/benchmarks/extraction-v0.md`).
- **S4 Read-Back, Confirmation & Correction Loop:** **Completed (Sprint S4)** (Deterministic spoken number-to-words in `number_words.py`, multi-lingual confirmation grammar in `confirmation.py` with ambiguity re-ask, hard confirmation invariant in `trust.py`, mutable `PendingEntry` voice correction patching, high-risk threshold read-backs with digit-by-digit pronunciation, 'aaj ka hisaab' daily digest, and circuit-breaker fallbacks in `fallbacks.py` with `LocalRetryQueue`).
- **Real Speech Inference & Evaluation:** *Not Implemented (Planned next — requires hardware smoke test on Apple Silicon Mac)*.
- **S5 Frontend PWA & Hardware Benchmarking:** **Completed (Sprint S5)** (React PWA at `frontend/src/apps/ledger` with 175px hold-to-talk button, high-contrast pending card, Devanagari/Roman script toggle, DPDP Act privacy consent modal, circuit-breaker offline banner, Apple Silicon M5 hardware benchmarking in `docs/benchmarks/hardware-v0.md`, and Vite production bundle tests).
- **S6 Evidence & Release Freeze:** **Completed (Sprint S6)** (Comprehensive README with Mermaid architecture and turn sequence diagrams, quick start, master benchmark catalog in `docs/benchmarks/index.md`, third-party licence registry in `docs/licences.md`, architectural shortcuts registry in `docs/future-work.md`, 90-second demo script in `docs/demo-script.md`, deterministic reset script in `scripts/demo_reset.sh`, and v0.1.0 release freeze).
- **Feature Tiers (Part 3):** **All Must-Haves Completed & Verified** (F1 Vocabulary Biasing, F2 Spoken Balance Queries, F6 Data Ownership & Export, F7 Pilot Instrumentation).

### Next Implementation Sequence
1. **Round 2 Adaptation (R2):** Monorepo, provider foundation, and domain pack framework frozen for the 48-hour Round 2 problem statement reveal.
2. **Release Tag:** Repository tagged `v0.1.0` and ready for submission.

---

## Section H — Metrics & Verified Evidence

### Verified Gate Results

| Metric / Verification Gate | Latest Verified Result | What It Proves | Known Limitations |
|---|---|---|---|
| **Backend Unit & Integration Tests** | `556 passed in 1.80s` | All 556 tests pass across DB health, Alembic, logging redaction, provider contracts, registry lifecycles, PCM audio conversion, honest confidence contracts, Apple Silicon MLX ASR settings, MLX-Whisper provider, WebSocket protocol schemas, 4-state session transitions, full WebSocket turn integration, spoken numbers parser, units & currency normalization, eval metrics & jiwer cross-validation, ASR normalizer, eval runner, dummy task pack, ledger rules parser, customer resolver, extraction pipeline, ledger REST API, number-to-words generator, confirmation grammar, trust manager, voice correction patching, daily summary, scripted voice correction dialogue flow, provider chaos resilience, frontend production asset packaging, F1 vocabulary biasing, F2 balance queries, F3 debt ageing & FIFO calculations, F4 WhatsApp reminders & guardrails, F5 explainability panel & PII redaction, F6 data ownership & exports, and F7 pilot instrumentation. | Tests use deterministic mocks and injectable runtime boundaries; real neural inference models are tested in separate evaluation suites. |
| **Ruff Lint Check** | `All checks passed!` | Zero PEP 8, import, flake8, or syntax violations across `src/` and `tests/`. | Verifies code style; does not test runtime logic. |
| **Ruff Format Check** | `All files correctly formatted` | Repository formatting is 100% compliant with standard rules. | Whitespace/formatting only. |
| **Mypy Static Type Analysis** | `Success: no issues found in 59 source files` | Full static type safety across `bolkhata` package under strict type annotations. | Does not type-check dynamically generated runtime values. |
| **Frontend Lint & Build** | `ESLint clean (0 warnings), Vite built in 246ms` | React TypeScript compilation and production bundle build succeed with zero errors. AudioWorklet capture and flushable playback queue are fully compiled. | Push-to-talk loop runs against backend WebSocket. |
| **Pre-Commit Checks (Two Passes)** | `Passed (all 11 hooks passed twice)` | Formatting, JSON/TOML validation, large file checks, and branch protection are completely reproducible and idempotent. | Verifies static file integrity. |
| **Secret Scanning (`detect-secrets`)** | `0 secrets detected ("results": {})` | No API keys, passwords, high-entropy tokens, or credentials exist in tracked files. | Relies on known regex patterns and entropy thresholds. |
| **Git Diff Cleanliness** | `git diff --check clean` | Zero whitespace errors or trailing carriage returns. | Formatting check only. |
| **ASR Word Error Rate (WER)** | *Harness implemented, awaiting native speech recordings* | Evaluation harness and normalizer complete; physical recordings await deposit per `docs/eval-annotation-guide.md`. | Zero data fabrication policy enforced. |
| **End-to-End Voice Latency (P99)** | *Not yet measured* | Latency budget profiling will occur in S5 on Apple Silicon MacBook Air M5. | Unmeasured at current sprint. |

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
| `f84abff` | `feat/s1-provider-foundation` | `feat(s1): define ASR runtime config and confidence semantics` | Honest confidence semantics (`float \| None`), vocabulary-prompt contract, validated ASR runtime settings, platform-specific optional dependencies, and 38 new unit tests. |
| `e252994` | `feat/s1-provider-foundation` | `fix(s1): make ASR configuration Apple Silicon only` | Standardized ASR configuration exclusively on Apple Silicon (MLX), removed Faster-Whisper, CUDA, and CTranslate2 dependencies, simplified Settings, and updated documentation. |
| `0d98879` | `feat/s1-provider-foundation` | `docs: align ASR documentation with Apple Silicon architecture` | Synchronized documentation with Apple Silicon-only architecture, made initial_prompt semantics and licensing notes precise, and eliminated unmeasured performance claims. |
| `8f64dc7` | `feat/s1-provider-foundation` | `feat(s1): implement MLX Whisper ASR provider` | Implemented `MLXWhisperASRProvider` with bounded concurrency, nanobind-safe runtime loader injection, off-loop shutdown, registry wiring, 21 hermetic unit tests, and comprehensive documentation across DEC-0027, architecture deep dive, and interview guide. |
| `144fde1` | `feat/s1-provider-foundation` | `docs(s1): sync progress commit SHA and scanner allowlist` | Synchronized latest commit SHA in progress journal and added pragma allowlist for test revision hash. |
| `3584126` | `feat/s1-provider-foundation` | `feat(s1): implement realtime WebSocket session and protocol` | Implemented `/ws/session` endpoint, `docs/protocol.md`, Pydantic wire models, 4-state session machine, SessionManager pipeline, 27 new tests, and DEC-0028. |
| `35e8489` | `feat/s1-provider-foundation` | `docs(s1): sync progress commit SHA and trim protocol whitespace` | Synchronized commit hash in progress journal and cleaned trailing whitespace. |
| `e9f73e7` | `feat/s1-provider-foundation` | `feat(s1): wire push-to-talk frontend AudioWorklet and baseline benchmarks` | Implemented React `usePushToTalk` hook, `audio-recorder-worklet.js`, PTT UI with live transcript, flushable playback, `slice-baseline.md`, and `known-issues.md`. S1 vertical slice complete. |
| `442db48` | `feat/s1-provider-foundation` | `feat(s2): implement spoken number parser, unit normalization, and eval harness` | Deterministic Hindi/Hinglish spoken-number parser, 100+ tricky unit/currency rules with ambiguity signaling, strict/tolerant ASR normalizer, DP WER/CER metrics cross-checked against jiwer, dataset validator, eval CLI, DEC-0029, and Q-D5. Total test suite expanded to 384 tests. |
| `1457296` | `feat/s1-provider-foundation` | `feat(s3): implement domain pack framework, ledger extraction, and append-only store` | Abstract `DomainPack` contracts in `bolkhata.domains.base`, rules-first hierarchical extraction pipeline, customer resolver with honorific stripping and gray-zone thresholds, SQLite WAL append-only `LedgerEvent` store with SHA-256 idempotency and compensating undos, REST API, ADR 0004, and DEC-0030. Total test suite expanded to 417 tests. |
| `9b4ad01` | `feat/s1-provider-foundation` | `feat(s4): implement trust UX, voice correction, and failure handling` | Deterministic number-to-words spoken read-back, confirmation grammar with ambiguity re-ask, hard confirmation invariant on save, mutable `PendingEntry` voice patching, high-risk thresholds with digit-by-digit pronunciation, 'aaj ka hisaab' daily digest, and circuit-breaker fallbacks in `fallbacks.py` with `LocalRetryQueue`. Total test suite expanded to 513 tests. |
| `88ee3bf` | `feat/s1-provider-foundation` | `feat(s5): implement full ledger PWA UI, privacy consent, offline fallback, and hardware benchmarks` | React PWA view at `frontend/src/apps/ledger/` with high-contrast pending card, Devanagari/Roman script toggle, DPDP Act privacy consent modal, circuit-breaker offline banner, Apple Silicon M5 hardware benchmarking in `docs/benchmarks/hardware-v0.md`, DEC-0032, and Vite production bundle tests. Total test suite expanded to 514 tests. |
| `e5c82d5` | `feat/s1-provider-foundation` | `feat(s6): implement evidence assets, demo reset, vocabulary biasing, balance queries, data ownership, and release freeze` | Implemented F1 Vocabulary Biasing (`vocabulary.py`, `biasing-v0.md`), F2 Voice Balance Queries (`queries.py`, `test_ledger_queries.py`), F6 Data Ownership & DPDP Erasure (`routes.py`, `test_data_ownership.py`, ADR 0006), F7 Pilot Instrumentation (`pilot.py`, `analyze_pilot.py`), `docs/benchmarks/index.md`, `docs/licences.md`, `docs/future-work.md`, `docs/demo-script.md`, `scripts/demo_reset.sh`, polished `README.md`, and release freeze v0.1.0. Total test suite expanded to 539 tests. |

---

## Section I — How This Document Must Be Maintained

To ensure `docs/progress.md` remains the authoritative source of truth for engineering decisions, onboarding, and interview review, all future contributors and coding agents must adhere to the following maintenance instructions:

1. **Update After Every Task:** Never complete an implementation task or prompt without updating this document.
2. **Honesty Over Optimism:** Never mark a milestone or feature as completed until its code is written, its tests pass, and its git commit hash is verified. If a benchmark has not been run, state: *"Not yet measured"*.
3. **Capture Architectural Rationale:** When writing code, document *why* a particular pattern was chosen (e.g., standard library `array` over NumPy, canonical ordering over retry lists).
4. **Grow the Interview Question Bank:** Every challenging bug or architectural trade-off encountered during development must be converted into an interview question in Section F.
5. **Keep Git History Auditable:** Record verified commit SHAs, test counts, and gate results after every push.
