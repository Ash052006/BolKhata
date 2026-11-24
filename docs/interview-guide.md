# BolKhata — Technical Interview Preparation & Defense Guide

> **Document Type:** Senior/Staff Software Engineer Interview Guide & System Defense Manual
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)
> **Target Roles:** Senior Python Backend Engineer, AI/Speech Systems Engineer, Software Architect
> **Current Version:** Sprint S1 Stage 2

---

## Purpose & How to Use This Guide

This guide prepares you to explain, defend, and deep-dive into BolKhata during high-bar technical interviews. It moves beyond generic textbook definitions by grounding every answer in the **actual architectural choices, bugs discovered, source code, and verified tests** of this repository.

### Rules of Engagement in an Interview
1. **Never Claim Planned Work as Implemented:** Be brutally honest about what is merged (`S0` foundation, `S1` provider contracts, mock registry, 16 kHz PCM utilities) versus what is planned (`S2` number parser, `S3` ledger, concrete MLX adapter on Apple Silicon). Interviewers respect engineers who know exact system boundaries.
2. **Anchor Answers in Invariants:** When explaining architecture, focus on core invariants (fail-closed security, append-only ledger, zero-network CI, money safety).
3. **Walk Through Real Bugs:** Senior engineers are defined by how they diagnose and solve subtle distributed and concurrent failure modes (e.g., the registry retry-order bug, thread cancellation limits).

---

## Table of Contents

- [Topic A — Project Pitch & Architectural Introductions](#topic-a--project-pitch--architectural-introductions)
- [Topic B — Architecture & System Design](#topic-b--architecture--system-design)
- [Topic C — Python & Asynchronous Systems](#topic-c--python--asynchronous-systems)
- [Topic D — AI, Speech Recognition & Signal Processing](#topic-d--ai-speech-recognition--signal-processing)
- [Topic E — Backend, Databases & Money Safety](#topic-e--backend-databases--money-safety)
- [Topic F — Reliability, Fault Tolerance & Security](#topic-f--reliability-fault-tolerance--security)
- [Topic G — Testing Strategies & Engineering Workflows](#topic-g--testing-strategies--engineering-workflows)
- [Topic H — Project-Specific Deep Dives & Bug Walkthroughs](#topic-h--project-specific-deep-dives--bug-walkthroughs)
- [Topic I — Critical Interviewer Challenges (Hard Scenarios)](#topic-i--critical-interviewer-challenges-hard-scenarios)
- [Topic J — Interview Preparation Checklist](#topic-j--interview-preparation-checklist)

---

## Topic A — Project Pitch & Architectural Introductions

### The 30-Second Elevator Pitch
> "BolKhata is a voice-first, push-to-talk digital ledger designed for Indian kirana shopkeepers. In busy retail stores, shopkeepers can't type on screens while weighing goods or handling cash. With BolKhata, they press a button and speak in code-switched Hindi, English, or Hinglish—for example, *'Sharma ji ko dhai sau udhaar'*. The app deterministically parses the numbers, reads back the entry aloud for explicit confirmation, and commits an immutable, append-only ledger transaction. It runs on local hardware and keeps working even when the internet drops."

### The 1-Minute Executive Summary
> "Over 12 million micro-merchants in India extend daily credit to local customers using paper notebooks. Digital ledger apps fail them because typing while serving customers is too high-friction, leading to forgotten debts. Traditional voice assistants fail because kirana stores are noisy, Indian code-switched dialects are misunderstood, and a misrecognized financial amount directly loses money.
> BolKhata solves this with three non-negotiable architectural principles:
> 1. **Money Safety:** Spoken numbers like *'dhai sau'* (250) are parsed by deterministic rule-based algorithms, never by hallucination-prone LLMs.
> 2. **Explicit Spoken Confirmation:** Every entry is read back aloud (*'Sharma ji, 250 rupaye udhaar. Sahi hai?'*) before anything is saved.
> 3. **Provider-Based Architecture & Hardware Isolation:** The core system is completely decoupled from machine learning weights using abstract contracts and dependency injection. Real ASR execution is planned exclusively for Apple Silicon Macs using MLX, while deterministic zero-network mocks in CI run 129 tests in under 200 milliseconds across any development platform without downloading weights."

### The 3-Minute Technical Architecture Walkthrough
> "Architecturally, BolKhata is built as a FastAPI async application coupled with a React/TypeScript voice PWA in a monorepo.
> Looking at the data flow:
> The client captures microphone audio via browser `AudioWorklet` strictly as uncompressed 16 kHz mono signed 16-bit little-endian PCM. This standard 32 KB/s stream is sent over WebSockets to our backend.
> In the backend, we use the Dependency Injection pattern via a centralized `ProviderRegistry`. All machine learning models—ASR, TTS, LLM, and VAD—sit behind abstract contracts (`BaseProvider`). This design ensures that our CI runs deterministically without downloading models or requiring GPUs, while production can toggle between mock, real MLX-Whisper on Apple Silicon, or local models via environment variables.
> When audio arrives, our shared audio module normalizes signed 16-bit integers to float32 tensors in the range $[-1.0, 1.0]$ using Python's standard-library `array` module—avoiding heavy C-extensions like NumPy in core utilities.
> Once speech is transcribed, we separate intent extraction from financial parsing: intent and entities are handled via structured outputs, while currency amounts are parsed deterministically.
> Finally, transactions are committed to an append-only database using SQLAlchemy 2.0 and Alembic. We use SQLite with WAL mode by default for zero-dependency local setups and provide a PostgreSQL profile for scaled multi-container deployments. All structured logs pass through a fail-closed JSON scrubber that scrubs customer PII and phone numbers before writing to disk."

### The 5-Minute Deep-Dive Walkthrough
*(Structure your response using the component breakdown in `docs/architecture-deep-dive.md`: Monorepo $\rightarrow$ Async Lifespan $\rightarrow$ Provider DI Registry $\rightarrow$ Audio Contract $\rightarrow$ Money Safety & Append-Only Ledger $\rightarrow$ CI/CD Quality Gates).*

---

## Topic B — Architecture & System Design

### Q-B1: Why did you build a custom Provider Registry instead of using an established DI framework?
1. **What the interviewer wants to evaluate:** Evaluation of framework bloat vs simplicity; understanding of async lifecycles; clean dependency management.
2. **Technically correct answer:** Established Python DI frameworks (like `dependency-injector` or `injector`) were primarily designed for synchronous enterprise applications and add complex container abstractions and reflection overhead. In BolKhata, we only have four core provider singletons (ASR, TTS, LLM, VAD). What they need isn't complex wiring, but **strict async lifecycle guarantees**: sequential startup, automatic rollback on partial failure, GPU warmup passes, and strict reverse-order teardown protected by async mutexes. Building a focused `ProviderRegistry` using standard library `asyncio.Lock` gave us complete control over retry semantics and rollback ordering with zero external dependencies.
3. **BolKhata concrete example:** In `backend/src/bolkhata/common/registry.py`, the registry manages lazy instantiation, canonical startup order, and identity-based reverse cleanup.
4. **Follow-up question:** How do API route handlers access the registry?
5. **Deeper follow-up answer:** The registry is instantiated in the FastAPI `lifespan` context manager and stored on `app.state.provider_registry`. Route handlers retrieve it via standard FastAPI dependency injection (`Depends`), ensuring loose coupling and trivial test overriding.
6. **Relevant files/tests:** `backend/src/bolkhata/common/registry.py`, `tests/unit/test_providers_mock.py`.
7. **What not to claim:** Do not claim the registry currently manages dynamic hot-swapping of models at runtime without restarts; models are configured at startup via `Settings`.

---

## Topic C — Python & Asynchronous Systems

### Q-C1: Why must synchronous machine learning inference never run directly on the asyncio event loop?
1. **What the interviewer wants to evaluate:** Deep understanding of the Python GIL, event loop mechanics, thread starvation, and async I/O.
2. **Technically correct answer:** The `asyncio` event loop runs on a single OS thread. It relies on cooperative multitasking where tasks yield control via `await`. Neural network speech inference engines (such as Whisper via MLX) are compute-bound matrix operations that execute continuous computation for hundreds of milliseconds. If called synchronously inside an async route or WebSocket handler, the execution never yields to the event loop. The entire process freezes: WebSocket heartbeats are dropped, incoming TCP frames buffer and disconnect, HTTP health checks time out, and all other concurrent users are starved.
3. **BolKhata concrete example:** All compute-bound inference calls in provider adapters are scheduled via `asyncio.to_thread()`, moving execution to Python's background worker thread pool where native worker threads release the GIL.
4. **Follow-up question:** What happens if an awaiting coroutine is cancelled while the worker thread is running `asyncio.to_thread()`?
5. **Deeper follow-up answer:** Python cannot kill native OS threads. Cancelling the coroutine raises `asyncio.CancelledError` immediately on the event loop, unblocking the calling task, but the underlying worker thread continues running until native C++ inference completes. Because abandoned tasks still consume compute, we enforce bounded concurrency with semaphores (`asr_max_concurrency`) so abandoned requests do not pile up.
6. **Relevant files/tests:** `docs/adr/0003-provider-interfaces-and-registry.md`, `backend/src/bolkhata/asr/base.py`.
7. **What not to claim:** Do not claim that calling `task.cancel()` frees GPU/CPU memory immediately.

### Q-C2: How does `MLXWhisperASRProvider` prevent semaphore slot leakage and capacity oversubscription when caller coroutines are cancelled?
1. **What the interviewer wants to evaluate:** Concurrency design under async cancellation, thread lifecycle management, and threadsafe callback scheduling.
2. **Technically correct answer:** Standard Python async context managers (`async with semaphore:`) automatically call `semaphore.release()` if the enclosing coroutine raises `asyncio.CancelledError`. However, native synchronous worker threads (executing MLX matrix operations) cannot be interrupted by Python coroutine cancellation. If the semaphore were released upon coroutine cancellation, a new request could immediately acquire the slot, causing multiple heavy model executions to run concurrently and saturate Apple Silicon unified memory.
In `MLXWhisperASRProvider`, we decouple semaphore release from coroutine lifecycle. The concurrency slot is acquired before scheduling the thread, but is released **strictly and exclusively** within the OS worker thread's `finally:` block via `loop.call_soon_threadsafe(sem.release)`. If the caller coroutine is cancelled, the coroutine exits with `CancelledError` without releasing the semaphore. The slot remains occupied until the native thread completes.
3. **BolKhata concrete example:** In `backend/src/bolkhata/asr/mlx_whisper.py`, `slot_owned_by_thread` guards whether the thread or the coroutine owns the slot. If task submission fails before the thread runs, the coroutine cleans up; once the thread starts, the thread's `finally:` handler guarantees atomic slot release.
4. **Follow-up question:** How do you test this deterministically without fragile timing sleeps?
5. **Deeper follow-up answer:** In `tests/unit/test_asr_mlx_whisper.py::test_cancellation_does_not_release_concurrency_slot_prematurely`, we use OS `threading.Event` barriers. Worker 1 signals entry and blocks on an event gate. The test cancels Task 1's coroutine and starts Task 2. Because Worker 1's thread is still blocked on the gate, Task 2 is blocked on the semaphore. Only when Worker 1's gate is opened does Worker 1 finish, releasing the semaphore so Task 2 can proceed.
6. **Relevant files/tests:** `backend/src/bolkhata/asr/mlx_whisper.py`, `tests/unit/test_asr_mlx_whisper.py`.
7. **What not to claim:** Do not claim that cancelling the task kills the running thread.

### Q-C3: How does the push-to-talk WebSocket session prevent stale turn race conditions when users interrupt or cancel speech?
1. **What the interviewer wants to evaluate:** Distributed state management, asynchronous cancellation semantics, event-driven race condition prevention, and generation tagging.
2. **Technically correct answer:** In real-time voice applications, users frequently interrupt audio playback (barge-in) or cancel an utterance mid-way. In an asynchronous pipeline where ASR, LLM, and TTS execute across separate stages, in-flight background tasks from an earlier turn might complete *after* the user has already started a new turn. If unhandled, this results in out-of-order text tokens, wrong audio playback, or corrupted state.
BolKhata solves this via three complementary mechanisms:
- **Explicit Four-State Machine:** The session transitions strictly (`IDLE` -> `LISTENING` -> `THINKING` -> `SPEAKING` -> `IDLE`). Illegal transitions (e.g. `start_utterance` while in `THINKING`) are rejected immediately with an error frame.
- **Generation Invariant (`generation_id`):** Every time a turn transitions to `THINKING`, a fresh, unique `generation_id` (UUID v4) is minted. Downstream pipeline stages check `if self.state_machine.generation_id != generation_id:` between stage boundaries (after ASR, during LLM streaming, and before TTS emission). Any result matching a previous generation is dropped silently.
- **Task Cancellation:** Upon receiving `start_utterance` or `cancel_utterance`, any running `_active_turn_task` is explicitly cancelled (`task.cancel()`), allowing coroutines awaiting I/O or provider results to unwind immediately.
3. **BolKhata concrete example:** `SessionStateMachine` in `backend/src/bolkhata/realtime/state.py` and `SessionManager._execute_turn` in `backend/src/bolkhata/realtime/session.py`.
4. **Follow-up question:** What happens if the shopkeeper speaks for longer than the maximum supported duration?
5. **Deeper follow-up answer:** The audio buffer is strictly bounded by `asr_max_duration_seconds * BYTES_PER_SECOND`. If binary frames exceed this limit, the session emits an `AUDIO_TOO_LONG` error frame, purges the buffer, and resets the state machine to `IDLE` to protect server memory.
6. **Relevant files/tests:** `backend/src/bolkhata/realtime/state.py`, `backend/src/bolkhata/realtime/session.py`, `tests/unit/test_realtime_state_machine.py`, `tests/integration/test_ws_session.py`.
7. **What not to claim:** Do not claim that cancelling `_active_turn_task` instantly aborts compute already executing in a native C++ thread; generation ID filtering handles the scenario where the thread finishes its computation after the coroutine has been cancelled.

---

## Topic D — AI, Speech Recognition & Signal Processing

### Q-D1: Explain how you convert raw PCM bytes to float32 samples and why you avoided NumPy.
1. **What the interviewer wants to evaluate:** Binary data handling, audio DSP fundamentals, memory layout, and dependency minimalism.
2. **Technically correct answer:** Raw audio from our 16 kHz mono contract arrives as signed 16-bit little-endian integers (two's complement, range $[-32768, 32767]$). Neural models require float32 values normalized to $[-1.0, 1.0]$.
We implemented this in `bolkhata.asr.common.pcm_to_float32` using Python's standard-library `array` module:
- We parse bytes into `array.array('h')` (signed 16-bit).
- On big-endian architectures, we call `.byteswap()` to guarantee little-endian decoding.
- We divide each sample by `32768.0`. This maps $-32768$ exactly to $-1.0$, $0$ to $0.0$, and $+32767$ to $32767/32768.0 \approx +0.99997$, strictly bounded in $[-1.0, 1.0]$.
We avoided NumPy in shared utilities because NumPy is a large C-extension dependency. Using Python's standard-library `array` keeps core audio utilities completely hermetic and zero-dependency. In the planned MLX adapter, the adapter itself will convert these normalized samples into the input representation required by MLX-Whisper; any NumPy conversion or memory-copy optimization will be verified in the adapter and benchmarked against real audio.
3. **BolKhata concrete example:** `backend/src/bolkhata/asr/common.py`.
4. **Follow-up question:** Why divide by 32768.0 instead of 32767.0?
5. **Deeper follow-up answer:** Dividing by 32767.0 causes the minimum possible 16-bit signed integer ($-32768$) to map to $-1.0000305$. In neural audio encoders (like Whisper's log-mel filterbanks), values strictly outside $[-1.0, 1.0]$ cause clipping warnings, gradient instability, or numerical overflow. Dividing by 32768.0 guarantees that all values fall within $[-1.0, 1.0]$.
6. **Relevant files/tests:** `tests/unit/test_asr_common.py` (specifically `test_normalization_boundaries`).
7. **What not to claim:** Do not claim that the standard-library `array` buffer can be passed directly to CTranslate2 or PyTorch as an implemented integration; the concrete MLX-Whisper adapter is implemented in `bolkhata.asr.mlx_whisper` and verified with hermetic unit tests; real hardware inference evaluation remains pending. Do not claim standard-library `array` generator division is faster than NumPy on a 1-hour audio file; on short kirana voice clips, execution is sub-millisecond, making dependency reduction the superior trade-off.

### Q-D2: Why does BolKhata treat ASR confidence as `float | None` rather than computing `exp(avg_logprob)`?
1. **What the interviewer wants to evaluate:** Statistical calibration, ASR decoder mechanics, and honest contract design for safety-critical systems.
2. **Technically correct answer:** Autoregressive encoder-decoder models like Whisper output token log-probabilities (`avg_logprob`). These raw scores are uncalibrated and sequence-length dependent. Exponentiating `avg_logprob` using `math.exp()` produces a pseudo-probability that does not represent a true Bayesian posterior or calibrated confidence. In a financial application where low-confidence words trigger verbal clarification, fabricating a confidence number creates dangerous false certainty. By defining `confidence: float | None`, we enforce honest semantics: numeric values are allowed strictly when provided by a documented runtime probability field; otherwise, it is explicitly `None` (unavailable).
3. **BolKhata concrete example:** `backend/src/bolkhata/asr/base.py` and `tests/unit/test_providers_mock.py`.
4. **Follow-up question:** How do you handle word-level timestamps when the engine does not provide confidence?
5. **Deeper follow-up answer:** `WordTiming` also defines `confidence: float | None = None`. If an engine outputs start and end timestamps but no probability, timing is preserved while confidence remains `None`.
6. **Relevant files/tests:** `backend/src/bolkhata/asr/base.py`, `tests/unit/test_providers_mock.py`.
7. **What not to claim:** Do not claim that Whisper's `avg_logprob` is useless; it is useful for relative thresholding within a single model run, but must not be presented as a calibrated $[0.0, 1.0]$ probability to callers.

### Q-D3: How does `initial_prompt` work for vocabulary biasing in Whisper, and how does it differ from an LLM prompt?
1. **What the interviewer wants to evaluate:** Understanding of acoustic decoder conditioning vs natural language prompt engineering.
2. **Technically correct answer:** An LLM prompt is an open-ended instruction telling the model what task to perform. In Whisper, `initial_prompt` does not give instructions. Instead, it injects preceding context tokens into the autoregressive text decoder. When the decoder generates words, the self-attention mechanism attends to these prompt tokens, biasing the language modeling prior toward specific spelling, terminology, and domain vocabulary (*"Sharma ji, udhaar, jama, chawal, pachaas"*). However, `initial_prompt` does not guarantee correct recognition and does not replace acoustic evidence. Excessive or incorrect prompt context can bias the transcript incorrectly or increase hallucination risk.
3. **BolKhata concrete example:** `initial_prompt` parameter in `ASRProvider.transcribe()` (`backend/src/bolkhata/asr/base.py`).
4. **Follow-up question:** What happens if the `initial_prompt` is too long?
5. **Deeper follow-up answer:** Whisper decodes text in 30-second context windows (up to 448 tokens). Long prompts consume decoder token context, reducing the space available for transcribing speech. Therefore, initial prompts should be concise domain token lists rather than long prose.
6. **Relevant files/tests:** `backend/src/bolkhata/asr/base.py`, `tests/unit/test_providers_mock.py`.
7. **What not to claim:** Do not claim that `initial_prompt` is an infallible constraint or that it cannot cause hallucinations; incorrect or excessive context can bias the decoder to hallucinate suggested words that were never spoken. Vocabulary prompting must be empirically evaluated using real Hindi/Hinglish audio, including negative examples where a suggested word was not spoken.

### Q-D4: Why did testing with `unittest.mock.patch.dict(sys.modules)` cause fatal `SIGABRT` crashes in `mlx.core`, and how did you resolve it?
1. **What the interviewer wants to evaluate:** C-extension lifecycle in CPython, `nanobind` internals, and test isolation design.
2. **Technically correct answer:** Apple MLX is written in C++ and binds to Python via `nanobind`. `nanobind` maintains global C++ registry tables for Python types and enumerations. In early tests, missing optional dependencies were simulated with `patch.dict(sys.modules, {"mlx_whisper": None})`. When `initialize()` attempted `import mlx.core`, the native dynamic library was loaded via `dlopen`. When the test exited, `patch.dict` restored `sys.modules`, removing `mlx.core` from Python's module table. However, compiled C-extensions cannot be unloaded from memory. A subsequent test attempted `import mlx.core` again, causing Python to call `PyInit_core()` a second time. `nanobind` detected duplicate enum registrations in its static C++ tables and called `abort()`, terminating the test runner with `SIGABRT` (code 134).
We resolved this by replacing global module patching with an explicit, injectable `runtime_loader` interface (`MLXRuntime`). Tests inject fake runtime dependencies or failure callables directly into the provider constructor, completely eliminating `sys.modules` mutation.
3. **BolKhata concrete example:** `backend/src/bolkhata/asr/mlx_whisper.py` (`load_mlx_runtime`, `MLXRuntime`) and `tests/unit/test_asr_mlx_whisper.py`.
4. **Follow-up question:** Does importing `bolkhata.asr.mlx_whisper` at module level import `mlx.core`?
5. **Deeper follow-up answer:** No. All runtime imports are deferred until `initialize()` is executed, keeping the base package load zero-dependency and CI hermetic.
6. **Relevant files/tests:** `backend/src/bolkhata/asr/mlx_whisper.py`, `tests/unit/test_asr_mlx_whisper.py` (`test_lazy_imports_do_not_import_mlx_runtime`).
7. **What not to claim:** Do not claim that reloading native dynamic C-extensions is safe in Python; C-extension reloading is fundamentally unsupported by CPython's architecture.

---

## Topic E — Backend, Databases & Money Safety

### Q-E1: How do you guarantee money safety when using AI in a kirana ledger?
1. **What the interviewer wants to evaluate:** AI safety, deterministic vs probabilistic design, and financial risk mitigation.
2. **Technically correct answer:** In BolKhata, **the LLM is never allowed to parse, calculate, or decide monetary values**.
We enforce a strict 4-layer defense:
1. **Deterministic Parsing:** Numeric amounts are parsed using rule-based grammar and regular expressions (`S2`), handling Hindi fractions (*dhai sau* $\rightarrow$ 250) mathematically.
2. **Mandatory Spoken Read-Back:** The system synthesizes and reads back the exact parsed transaction (*'Sharma ji, do sau pachaas rupaye udhaar. Sahi hai?'*) before anything is persisted.
3. **Explicit User Confirmation:** The transaction is only committed if the merchant explicitly confirms verbally (*'Haan'*) or taps the screen.
4. **Append-Only Ledger:** The database schema has no `UPDATE` or `DELETE` statements. Errors are corrected via new compensating entries referencing the original transaction ID, guaranteeing a complete audit trail.
3. **BolKhata concrete example:** Documented in master constraints in `agent.md` and ADR 0003.
4. **Follow-up question:** How do you prevent double-posting if a shopkeeper says "Haan" twice during a network lag?
5. **Deeper follow-up answer:** Every voice session turn generates a unique client-side `idempotency_key` based on the session ID and turn sequence. The database ledger table enforces a unique constraint on `idempotency_key`. A duplicate request returns the existing transaction record without creating a second entry.
6. **Relevant files/tests:** `agent.md`, `docs/architecture-deep-dive.md` (Section 8).
7. **What not to claim:** Do not claim the append-only ledger tables are already implemented; they are planned for S3.

---

## Topic F — Reliability, Fault Tolerance & Security

### Q-F1: How does BolKhata prevent sensitive merchant and customer PII from leaking into logs?
1. **What the interviewer wants to evaluate:** Security engineering, compliance (India DPDP Act), fail-closed design, and custom logging pipelines.
2. **Technically correct answer:** We implemented a custom `StructuredJsonFormatter` in `bolkhata.common.logging`. It intercepts every log record emitted by standard library logging, Uvicorn, or SQLAlchemy.
It applies three layers of scrubbing:
1. **Key Scrubbing:** Recursively scrubs dictionary keys containing sensitive terms (`customer_name`, `phone`, `token`, `password`, `secret`, `api_key`).
2. **Regex Scrubbing:** Scans all string messages for Indian 10-digit mobile numbers (`\b[6-9]\d{9}\b`), JWT tokens, and Bearer authentication headers.
3. **Recursive Exception Traversal:** Sanitizes local variables and formatted tracebacks across nested exception chains (`__cause__` and `__context__`).
4. **Fail-Closed Guarantee:** If formatting encounters an unexpected error, it catches it and emits a safe generic sentinel rather than leaking unredacted data or crashing the process.
3. **BolKhata concrete example:** `backend/src/bolkhata/common/logging.py`.
4. **Follow-up question:** How did you test this without triggering your automated secret scanner?
5. **Deeper follow-up answer:** We wrote comprehensive unit tests verifying that phone numbers and tokens are replaced with `[REDACTED]`. Because `detect-secrets` scans all repository files, our synthetic test tokens initially triggered false positives. Rather than disabling the scanner, we used line-level allowlisting in `.secrets.baseline` to maintain 100% detector rigor across production code.
6. **Relevant files/tests:** `tests/unit/test_logging_redaction.py`, `.secrets.baseline`.
7. **What not to claim:** Do not claim we encrypt logs on disk; log encryption is handled by host infrastructure, while our code ensures scrubbing before emission.

### Q-F2: How does `shutdown()` coordinate with active worker threads without deadlocking or blocking the asyncio event loop?
1. **What the interviewer wants to evaluate:** Async/thread lifecycle boundaries, event-loop non-blocking invariants, and idempotent shutdown.
2. **Technically correct answer:** When `shutdown()` is called while worker threads are executing, it must prevent new requests, await existing workers, and release executor resources. If `all_workers_done.wait()` or `executor.shutdown(wait=True)` is called directly inside an async function on the event loop thread, it blocks the entire loop, preventing other coroutines or callbacks (such as `loop.call_soon_threadsafe(sem.release)`) from processing.
In `MLXWhisperASRProvider`, `shutdown()` executes in two phases:
1. **Synchronous Immediate Marking:** Before any `await` suspension point, it sets `self._is_shutdown = True` and signals `shutdown_started_event`. Any queued or new `transcribe()` call immediately rejects with `RuntimeError`.
2. **Off-Loop Thread Joining:** The blocking thread join `all_workers_done.wait()` and `executor.shutdown(wait=True)` are executed off the event loop thread via `asyncio.to_thread(_cleanup_executor, ...)`. The event loop remains responsive and callbacks can execute cleanly until shutdown completes.
3. **BolKhata concrete example:** `backend/src/bolkhata/asr/mlx_whisper.py` (`shutdown` and `_cleanup_executor`).
4. **Follow-up question:** What happens if `shutdown()` is called multiple times concurrently?
5. **Deeper follow-up answer:** The method is idempotent. If `self._is_shutdown` or not `self._is_initialized`, it returns immediately.
6. **Relevant files/tests:** `backend/src/bolkhata/asr/mlx_whisper.py`, `tests/unit/test_asr_mlx_whisper.py::test_shutdown_waits_for_active_workers_and_prevents_new_calls`.
7. **What not to claim:** Do not claim that calling `shutdown()` terminates running synchronous inferences immediately; it safely drains and joins running threads.

---

## Topic G — Testing Strategies & Engineering Workflows

### Q-G1: How do you verify provider lifecycles and concurrency without live model weights?
1. **What the interviewer wants to evaluate:** Test doubles, hermetic testing, isolation of concerns, and race-condition detection.
2. **Technically correct answer:** We built deterministic mock providers (`MockASRProvider`, `MockTTSProvider`, etc.) that track their internal state (`is_initialized`, `is_warmed_up`, `is_shutdown`) and allow injecting controlled failures via boolean flags (e.g. `mock_asr.fail_initialize = True` or `fail_warmup = True`).
Using pytest-asyncio, we write tests that:
- Trigger partial initialization failures and verify that earlier providers undergo immediate reverse rollback.
- Trigger shutdown failures on multiple providers and verify that repeated shutdown calls preserve canonical reverse sequence.
- Fire concurrent `asyncio.gather(registry.initialize(), registry.initialize())` calls to prove that internal `asyncio.Lock` prevents duplicate initialization.
3. **BolKhata concrete example:** `tests/unit/test_providers_mock.py`.
4. **Follow-up question:** Why is `MockTTSProvider` generating real sine-wave PCM audio instead of empty bytes?
5. **Deeper follow-up answer:** If a mock returns empty bytes or fake ASCII text, downstream audio consumers (like duration calculators, audio format validators, or streaming WebSocket serializers) cannot verify real audio framing. Our mock generates mathematically valid 16 kHz 16-bit mono sine-wave PCM chunks matching the expected duration, enabling high-fidelity integration testing.
6. **Relevant files/tests:** `backend/src/bolkhata/tts/mock.py`, `tests/unit/test_providers_mock.py`.
7. **What not to claim:** Do not claim that passing mock tests proves MLX-Whisper won't run out of unified memory; hardware benchmarking is explicitly separated into S5.

---

## Topic H — Project-Specific Deep Dives & Bug Walkthroughs

### Q-H1: Walk me through a complex bug you found in the Provider Registry and how you solved it.
1. **What the interviewer wants to evaluate:** Root-cause analysis, debugging complex state machines, and defensive design.
2. **Technically correct answer:**
   > "**The Bug:** In our provider registry, providers must be torn down in strict reverse-startup order (VAD $\rightarrow$ LLM $\rightarrow$ TTS $\rightarrow$ ASR). In an early implementation, when a provider's `shutdown()` raised an exception, we popped it from `_initialized_providers` and appended it to a `failed_providers` list for retry. When multiple providers failed (e.g., both LLM and TTS failed teardown), popping them in reverse order and appending them to the retry list inverted their relative ordering. On subsequent retry calls, the retry list executed them in forwards order instead of reverse order, violating our sequence invariant.
   > **Root Cause:** Treating the list of active providers as a mutable queue and moving failed items into an auxiliary list destroyed the global sequence invariant.
   > **The Solution:** We established an **identity-based canonical tracking invariant**. We maintain a single list of providers in their original startup order. During shutdown, we iterate over `reversed(self._initialized_providers)`. We only remove a provider from the list if its `shutdown()` call *succeeds*. If a provider fails, it stays in the list at its exact original index. On any subsequent retry call, iterating over `reversed()` naturally preserves the correct reverse sequence regardless of failure combinations.
   > We proved this fix with regression test `test_multiple_providers_fail_shutdown_retried_in_reverse_startup_order`."
3. **BolKhata concrete example:** Git commit `516e03a` and `backend/src/bolkhata/common/registry.py`.
4. **Follow-up question:** How did you handle exceptions when multiple providers failed during the same shutdown loop?
5. **Deeper follow-up answer:** We collect all caught exceptions in a list. We continue attempting shutdown for all remaining providers. At the end of the loop, if errors occurred, we raise an `ExceptionGroup` (or re-raise the primary failure chained with `__context__`), ensuring no provider teardown is abandoned due to an earlier failure.
6. **Relevant files/tests:** `backend/src/bolkhata/common/registry.py` (lines 190–240), `tests/unit/test_providers_mock.py`.
7. **What not to claim:** Do not claim the bug was caught in production; it was caught during rigorous unit testing of provider failure rollbacks.

---

## Topic I — Critical Interviewer Challenges (Hard Scenarios)

### Challenge 1: "Why not just use OpenAI's Whisper API and GPT-4 directly instead of building all this local provider abstraction?"
- **Defense:**
  1. **Connectivity & Latency:** Kirana stores operate in congested markets with spotty internet. Cloud APIs require uploading 100 KB+ audio over slow uplinks, waiting 2–4 seconds for transcription, and making another network roundtrip for LLM extraction. Total latency exceeds 5 seconds, which feels broken during a customer transaction.
  2. **Cost at Scale:** A busy kirana store handles 300+ transactions a day. Paying cloud API fees per transaction would completely eliminate our profit margin.
  3. **Offline Reliability:** When the shopkeeper's 4G drops, a cloud-dependent app stops working. Our architecture supports running lightweight quantized models (MLX-Whisper on Apple Silicon Mac, local LLMs) completely offline.

### Challenge 2: "Why is an LLM involved in a financial application at all if it can hallucinate?"
- **Defense:**
  The LLM is strictly restricted to **semantic entity extraction** (identifying customer names, item names, and transaction intent like credit vs debit). It is **physically barred from performing arithmetic or deciding amounts**. Numbers are extracted by deterministic code, read back verbally, and explicitly confirmed by the human shopkeeper before persistence. The LLM provides conversational flexibility, while deterministic code provides financial safety.

### Challenge 3: "Why did you drop Windows/NVIDIA CUDA support and standardize exclusively on Apple Silicon?"
- **Defense:**
  In local edge AI, hardware selection dictates runtime efficiency. A kirana store counter requires compact, silent, fanless, and power-efficient hardware. The Apple Silicon MacBook Air M5 provides 16 GB of high-bandwidth unified memory accessible directly by the CPU and Metal GPU without PCIe host-to-device bus transfer bottlenecks. Maintaining dual-stack configuration (CUDA, CTranslate2, Faster-Whisper) alongside Apple's MLX created unnecessary complexity, configuration bloat, and leaky abstractions. Standardizing on Apple Silicon and MLX allows us to optimize directly for Metal unified memory and keep our dependency graph lean. Note that MLX-Whisper is planned for Stage 2, and runtime performance, latency, and memory footprints remain unmeasured until physical benchmarks are executed against the implemented adapter.

### Challenge 4: "What if two shopkeeper devices attempt to update the same customer simultaneously?"
- **Defense:**
  Because the ledger is **append-only**, there are no in-place row updates or lock contentions. Both devices insert immutable transaction event rows with unique IDs and client timestamps. A customer's balance is computed as the sum of all transaction rows. If offline devices sync later, their append-only event logs merge deterministically without write-write conflicts.

### Challenge 5: "Why did you default ASR concurrency to 1? Isn't that terrible for scalability?"
- **Defense:**
  On local edge nodes or developer laptops, neural inference engines internally saturate available CPU/GPU cores during multi-threaded matrix multiplication. If you accept two concurrent speech inferences on a constrained machine, thread contention causes CPU cache thrashing, doubling the latency for both users. Serializing inference via an async semaphore guarantees deterministic, minimum latency per request. On production clusters, concurrency is scaled via `ASR_MAX_CONCURRENCY` in `.env`.

### Challenge 6: "What are the biggest limitations of the current implementation?"
- **Defense (Honest & Evidence-Based):**
  1. Concrete speech recognition adapter (MLX-Whisper on Apple Silicon) is not yet merged; we are currently running on verified deterministic mocks and audio utilities (`MockASRProvider` is the only active provider).
  2. The push-to-talk WebSocket loop is not yet connected to the frontend UI.
  3. Acoustic accuracy (WER), memory footprint, and latency budgets on physical Apple Silicon hardware have not yet been benchmarked.

### Challenge 7 (Q-D5): "Why do LLMs fail at Indian spoken arithmetic, and how does BolKhata guarantee money safety?"
- **Defense:**
  1. **Linguistic Complexity of Indian Numbers:** Indian speech frequently uses regional multipliers (`sau`, `hazaar`, `lakh`, `crore`) and fractional idioms like `dhai` (2.5x base), `derh` (1.5x base), `sawa` (1.25x or +0.25 of multiplier), `sadhe` (+0.5 of unit for $\ge 3$), and `paune` (-0.25 of unit). For instance, `dhai sau` is 250, `derh hazaar` is 1,500, `sawa sau` is 125, `sadhe teen sau` is 350, and `paune do sau` is 175.
  2. **Probabilistic Hallucinations:** LLMs are autoregressive token predictors, not mathematical execution engines. Prompting an LLM to parse these phrases produces subtle, non-deterministic arithmetic errors (e.g. interpreting `dhai sau` as 200 or 50, or `paune do sau` as 275 instead of 175). In a ledger system tracking credit and debts, an error of ₹100 or ₹1,000 immediately destroys user trust.
  3. **Architectural Hard Boundary:** BolKhata physically isolates the LLM from number parsing and arithmetic. A deterministic, table-driven Python grammar (`bolkhata.domains.common.numbers` and `bolkhata.domains.common.units`) parses 0–100 numbers, multipliers, fractions, and units. When an utterance is truly ambiguous (such as `do teen kilo` or `do teen sau rupaye`), the parser flags `is_ambiguous=True` and returns candidate values (`[200.0, 300.0]`) so the dialogue manager clarifies with the shopkeeper rather than guessing. Money amounts have mathematical provenance and never touch an LLM reasoning step.

---

## Topic E — Domain Architecture, Entity Resolution & Append-Only Financial Safety

### Q-E1: How does the Domain Pack framework enforce architectural isolation between the core voice pipeline and domain logic?
1. **What the interviewer wants to evaluate:** Modular architecture, dependency inversion, clean boundaries, and avoiding domain leakage.
2. **Technically correct answer:** The core voice and dialogue engine knows nothing about credit, debit, or Kirana stores. It interacts solely with abstract contracts defined in `bolkhata.domains.base` (`DomainPack`, `DomainIntent`, `DomainAction`, `EntityResolver`). The invariant is strictly enforced: *nothing outside `bolkhata.domains` may import from `bolkhata.domains.ledger`*. Core routes dynamically dispatch via `get_domain_router()` and `get_domain_pack()`. To prove complete domain-agnosticism, our hermetic test suite implements a `DummyTaskPack` in `tests/unit/test_domain_pack_dummy.py`, proving that swapping to a todo-list or pharmacy domain requires zero changes to the underlying platform infrastructure.
3. **BolKhata concrete example:** `backend/src/bolkhata/domains/base.py`, `backend/src/bolkhata/domains/__init__.py`, `tests/unit/test_domain_pack_dummy.py`.

### Q-E2: Why does BolKhata use an append-only event store with compensating undos instead of SQL UPDATE and DELETE statements?
1. **What the interviewer wants to evaluate:** Financial data integrity, auditability, idempotency, and concurrent consistency.
2. **Technically correct answer:** In financial accounting and Indian GST / mercantile standards, physical deletion (`DELETE FROM`) destroys forensic auditability. If an entry is created accidentally or cancelled, a hard delete erases the historical record and breaks offline replication synchronization.
BolKhata stores all ledger mutations as immutable append-only events (`LedgerEvent`) with unique SHA-256 idempotency keys (`hash(customer_id, event_type, amount, date, client_turn_id)`). If a network timeout causes a client to retry creating an entry, the unique key match returns the existing event immediately without double-posting. Reversals are recorded as explicit `compensation_undo` events linking to `compensated_event_id`. Both the original event and compensating event are marked `is_compensated = True`, excluding them from active balance aggregation while keeping the immutable historical audit trail 100% intact.
3. **BolKhata concrete example:** `backend/src/bolkhata/domains/ledger/db_models.py`, `backend/src/bolkhata/domains/ledger/routes.py` (`create_ledger_entry`, `list_customers`), `tests/integration/test_ledger_api.py`.

### Q-E3: How does customer name resolution handle cross-script variations (Devanagari vs Roman), honorifics, and phonetic gray zones without silent false-positive merges?
1. **What the interviewer wants to evaluate:** Fuzzy matching algorithms, entity disambiguation, cross-lingual normalization, and safety thresholds.
2. **Technically correct answer:** Indian retail speech mixes Hindi honorifics (*ji*, *bhai*, *uncle*, *seth*) and varying scripts (Devanagari vs Romanized Hindi).
`CustomerResolver` handles this via a multi-stage deterministic pipeline:
1. **Honorific Stripping:** Removes common cultural prefixes and suffixes (*"Ramesh ji"* $\to$ *"Ramesh"*).
2. **Devanagari Transliteration:** Maps Devanagari tokens to Roman phonetic equivalents (*"रमेश"* $\to$ *"ramesh"*).
3. **Similarity Scoring:** Uses token sort ratio via `RapidFuzz`.
4. **Three-Tier Safety Thresholds:**
   - Score $\ge 0.85$: Auto-resolves to the existing customer ID.
   - Score in $[0.65, 0.85)$ or close competing candidates (score difference $< 0.08$): Gray zone $\to$ sets `is_ambiguous=True` and populates `candidates` for verbal clarification.
   - Score $< 0.65$: Unrecognized $\to$ proposes creating a new customer record.
The invariant is: **Never silently merge two distinct customers**.
3. **BolKhata concrete example:** `backend/src/bolkhata/domains/ledger/resolver.py`, `tests/unit/test_ledger_resolver.py`.

---

## Topic F — Trust UX, Voice Correction & Chaos Resilience

### Q-F1: How does BolKhata prevent unconfirmed transactions from corrupting financial ledger records?
1. **What the interviewer wants to evaluate:** Hard system invariants, defensive API design, and dialogue state verification.
2. **Technically correct answer:** In hands-free voice applications, users may mumble, hesitate, or get cut off by background noise. Defaulting ambiguous responses to 'yes' or auto-committing without verbal verification is fatal in fintech. BolKhata enforces a strict code-level guard: `confirm_pending_entry(pending)` verifies `if not pending.is_confirmed: raise ValueError(...)`. The confirmation grammar evaluates affirmative tokens (`haan`, `sahi hai`, `theek hai`, `likh do`, `yes`, `हाँ`, `ठीक है`) and rejection tokens (`nahi`, `galat`, `no`). Crucially, any unrecognized, ambiguous, or hesitation phrase (e.g. *"pata nahi"*, *"ek second"*) strictly maps to `UNCLEAR`, triggering a verbal re-ask rather than committing.
3. **BolKhata concrete example:** `tests/unit/test_trust_correction.py::test_hard_confirmation_safety_bypass_rejected` and `backend/src/bolkhata/domains/common/confirmation.py`.

### Q-F2: How does voice correction work without restarting the entire dialogue turn?
1. **What the interviewer wants to evaluate:** Incremental dialogue management, slot patching, and state preservation.
2. **Technically correct answer:** Instead of restarting from scratch when a merchant spots an error, BolKhata maintains an uncommitted `PendingEntry`. When the merchant says *"nahi teen sau nahi, teen sau pachaas"* or *"customer Verma ji hai"*, the confirmation parser detects `ConfirmationType.CORRECTION`. The `apply_voice_correction` engine identifies the target slot (`amount`, `customer`, `date`, or `items`), updates the pending model in place, records an audit trail in `patch_history`, increments the `correction_count`, and generates an updated read-back confirmation. To prevent infinite loops caused by severe acoustic noise, corrections are bounded (max 3 rounds) before prompting manual screen review.
3. **BolKhata concrete example:** `backend/src/bolkhata/domains/ledger/trust.py` (`PendingEntry`, `apply_voice_correction`), `tests/integration/test_voice_correction_flow.py`.

### Q-F3: How does the system degrade when individual AI providers or database connections crash mid-turn?
1. **What the interviewer wants to evaluate:** Fault tolerance, circuit breakers, and offline resilience.
2. **Technically correct answer:** Each system boundary defines a deterministic fallback:
- **ASR Failure:** Returns a typed-input prompt so merchants can type amounts manually without losing turn context.
- **LLM Failure:** Bypasses probabilistic models and executes the deterministic Python rule parser (`bolkhata.domains.ledger.parser`), logging `provenance={"llm_fallback": "rules_only"}`.
- **TTS Failure:** Omits audio synthesis while preserving on-screen visual read-back, preventing audio driver crashes from blocking ledger commits.
- **Database Write Failure:** Catches connection and lock errors (`OperationalError`) and queues payloads in `LocalRetryQueue` preserving their exact SHA-256 `idempotency_key`. When database connectivity resumes, retrying the queue commits transactions safely without duplicate records.
3. **BolKhata concrete example:** `backend/src/bolkhata/domains/ledger/fallbacks.py`, `tests/integration/test_provider_chaos.py`.

---

## Topic J — Interview Preparation Checklist

Before walking into a technical interview, ensure you can live-code or explain:

- [ ] **Files to Know Thoroughly:**
  - `backend/src/bolkhata/common/registry.py` (Registry lifecycle, locks, reverse shutdown).
  - `backend/src/bolkhata/asr/common.py` (PCM normalization, byte alignment, stdlib `array`).
  - `backend/src/bolkhata/common/logging.py` (Fail-closed PII scrubbing, regex, exception traversal).
  - `backend/src/bolkhata/asr/base.py` (Immutable dataclasses, async generator interfaces).
  - `backend/src/bolkhata/domains/base.py` (`DomainPack` abstraction, provenance, idempotency).
  - `backend/src/bolkhata/domains/common/number_words.py` (Number-to-Hindi/English words).
  - `backend/src/bolkhata/domains/ledger/trust.py` (PendingEntry, voice correction, high-risk threshold).
  - `backend/src/bolkhata/domains/ledger/fallbacks.py` (Chaos handling, local retry queue).
- [ ] **Tests to Highlight:**
  - `test_multiple_providers_fail_shutdown_retried_in_reverse_startup_order` (Retry sequence).
  - `test_normalization_boundaries` ($-32768 \rightarrow -1.0$, $+32767 \rightarrow +0.99997$).
  - `test_transcript_redacted_at_all_levels` (PII scrubbing at DEBUG/INFO/WARNING/ERROR).
  - `test_resolve_gray_zone_ambiguity` (Gray zone $[0.65, 0.85)$ returns candidate ambiguity).
  - `test_hard_confirmation_safety_bypass_rejected` (Hard confirmation invariant).
  - `test_full_scripted_voice_correction_and_undo_flow` (Full 4-turn correction and compensating undo).
  - `test_db_failure_local_retry_queue_and_recovery` (DB write failure queue and retry).
- [ ] **Key Architectural Numbers:**
  - 16 kHz Mono Signed 16-bit PCM = 32,000 bytes/sec.
  - Normalization divisor = `32768.0`.
  - 513 passing unit/integration tests running in ~0.65s.
  - Strict Mypy type-checking across 52 backend source files.
