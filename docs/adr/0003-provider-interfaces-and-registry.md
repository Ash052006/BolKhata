# ADR 0003: Provider Interfaces and Registry

## Status
Accepted *(Amended by [DEC-0026](../decision.md#dec-0026-apple-silicon-only-architecture-with-mlx-asr-runtime))*

## Context
BolKhata is a voice-first ledger for kirana shopkeepers requiring speech recognition (ASR), speech synthesis (TTS), and language model reasoning (LLM).

The project operates under strict operational constraints:
1. **Target Hardware & Execution Isolation:** Standardized on Apple Silicon Macs for local inference; mock providers remain cross-platform for CI. *(Historical note: initial dual-platform planning across Mac and Windows RTX 3050 was superseded by DEC-0026).*
2. **Offline & Test Reliability:** Development, unit testing, and continuous integration must run deterministically without downloading multi-gigabyte neural weights or relying on external cloud APIs.
3. **Decoupled Architecture:** Swapping an AI model (e.g. switching between mock and real MLX-Whisper, or Piper and Edge-TTS) must not require changes outside the provider module.
4. **Money Safety:** The LLM must never compute, correct, or decide monetary amounts.

## Decisions

### 1. Abstract Provider Contracts
All model modalities are defined as abstract base classes (`ASRProvider`, `TTSProvider`, `LLMProvider`, `VADProvider`) under their respective packages:
- `backend/src/bolkhata/asr/base.py`
- `backend/src/bolkhata/tts/base.py`
- `backend/src/bolkhata/llm/base.py`
- `backend/src/bolkhata/asr/vad.py`

Key Contract Invariants:
- **Audio Format:** Standardized strictly on headerless 16,000 Hz, 16-bit Signed Little-Endian Mono Linear PCM (`pcm_s16le`).
- **Immutable Results:** `ASRResult` uses immutable dataclasses with `words: tuple[WordTiming, ...] = ()` to prevent accidental in-place mutation or type incompatibilities.
- **Typed Chat Messages:** `ChatMessage` uses strict role typing (`Literal["system", "user", "assistant"]`).
- **Structured Output:** `LLMProvider.complete_structured` accepts caller-defined Pydantic schemas (`type[T] -> T`).
- **Accurate Streaming Semantics:** ASR streaming is documented honestly as chunked sliding-window transcription, reflecting the architectural reality of Transformer sequence-to-sequence models (Whisper).

### 2. Provider Registry & Lifecycle
Provider creation and lifecycle are orchestrated via `ProviderRegistry` (`backend/src/bolkhata/common/registry.py`):
- **Configuration-Driven:** Provider selection is governed by validated Pydantic settings (`asr_provider`, `tts_provider`, `llm_provider`, `vad_provider`).
- **No Import-Time Side Effects:** Importing provider modules never initializes models or allocates memory.
- **Concurrency & Failure Safety:** `initialize_all()` and `shutdown_all()` are guarded by an `asyncio.Lock` for idempotency. If an error occurs during startup, already-initialized providers are torn down in reverse order.
- **Reverse-Order Shutdown:** Clean teardown proceeds in reverse order of initialization (`VAD -> LLM -> TTS -> ASR`).

### 3. Async Execution and Bounded Worker Architecture
All provider interfaces are async (`async def`).
- Synchronous native inference engines (CTranslate2, ONNX Runtime, Piper) must never execute directly in the async event loop.
- In future implementation stages, synchronous C++ inference calls will run inside bounded thread executors (`asyncio.to_thread` with explicit worker limits).
- Note on Timeouts: A timeout wrapped around a coroutine (`asyncio.wait_for`) does not terminate an in-flight synchronous C/C++ thread; cancellation semantics must explicitly release engine references on task abort.

### 4. Deterministic Mock Implementations
Each modality provides a deterministic mock implementation (`MockASRProvider`, `MockTTSProvider`, `MockLLMProvider`, `MockVADProvider`):
- Mocks generate mathematically valid 16kHz linear PCM frames and deterministic transcripts.
- Mocks maintain explicit lifecycle state flags (`initialize_calls`, `is_initialized`, etc.) so unit tests verify initialization without fragile timing assertions.

## Alternatives Considered
1. **Direct Concrete Class Usage:** Importing `FasterWhisper` directly in WebSocket handlers. Rejected: couples networking and session state machines to specific engine binaries and breaks offline testing.
2. **Global Mutable Registry Singleton:** Storing active providers in a module-level dictionary. Rejected: introduces hidden state across test runs and causes race conditions during teardown.
3. **Mutable `list` Defaults for Word Timings:** Defaulting `words: list[WordTiming] = []`. Rejected: introduces mutable shared default state and violates strict type checking.

## Consequences
- **Positive:** CI runs 100% offline in milliseconds without downloading weights.
- **Positive:** High cohesion and clean inversion of control; replacing an engine requires implementing its provider interface only.
- **Positive:** Strict typing and failure-safe initialization prevent resource leaks.
- **Deferred:** Real engine adapters (`mlx-whisper`, `piper`, `groq`, `ollama`) and WebSocket routing are deferred to subsequent gated stages. *(Historical note: Faster-Whisper was removed per DEC-0026).*
