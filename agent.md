# Project: Bolkhata
A voice-first ledger for Indian kirana shopkeepers (Hindi, English, Hinglish), built for the Scaler x Wispr Flow "India Runs on Voice" hackathon. Reliable, measured, and honest about its limits. Team: [solo / N people].

## Hard constraints
- Hardware: a MacBook (Apple Silicon, 16 GB unified memory) is the primary dev and demo machine. A Windows laptop (RTX 3050 6 GB VRAM, 8 GB RAM) is an optional inference and benchmark node: run only one heavy service at a time there. Prefer small, quantized, or CPU-friendly models and measure memory before loading models together.
- Every model sits behind a provider interface (ASRProvider, TTSProvider, LLMProvider, VADProvider). Swapping a model must not require changes outside its provider module. Hosted providers are optional and always have a local fallback. Prefer open-source and local models; check the hackathon rules on tools and APIs when they are published.
- Must run locally with one command (docker compose up). No Kubernetes, no multi-tenant auth, no WebRTC, no barge-in.
- Interaction is push-to-talk.

## Stack
Python 3.11+, FastAPI, asyncio, Pydantic v2, SQLAlchemy 2 + Alembic (SQLite by default, PostgreSQL via a docker compose profile), faster-whisper plus a Metal/MLX-based option on the Mac, optional Silero VAD, a local TTS (evaluate), React + TypeScript + Vite as a PWA, AudioWorklet, WebSockets, Docker, pytest, Ruff, mypy, Playwright.

## Package layout
backend/src/bolkhata/{config,api,common,asr,tts,llm,realtime,domains}. Ledger-specific code goes ONLY in backend/src/bolkhata/domains/ledger and frontend/src/apps/ledger. Nothing outside domains/ may import from domains/ledger. Every domain implements the DomainPack interface (schema, prompts, normalizers, entity resolver, actions, read-back templates, eval set) so a new problem statement can be built by adding a pack, not changing the pipeline.

## Money safety
- Amounts are parsed by deterministic code, never computed or decided by the LLM.
- Every amount is read back and explicitly confirmed before it is saved.
- The ledger is append-only. Corrections and undo are new compensating entries.
- Actions use idempotency keys so a retry cannot double-record.

## Engineering rules
1. Plan before coding. For any non-trivial task, write a short plan and wait for approval.
2. Type hints everywhere; mypy strict on new code; Ruff clean.
3. Every external call has a timeout. No unbounded queues. No bare except. No blocking calls inside async code.
4. All config via environment variables validated by Pydantic settings. No secrets in the repo. Provide .env.example.
5. Structured JSON logging with session_id, turn_id, generation_id on every line in a session. Never log raw transcripts, audio, customer names, phone numbers, or secrets at INFO level.
6. Every feature ships with tests. Audio tests use deterministic fixtures in tests/fixtures, never a live microphone.
7. Sessions follow an explicit state machine: IDLE, LISTENING, THINKING, SPEAKING. Illegal transitions are rejected.
8. Every response has a generation_id, so stale output can be dropped later. Build this in now because it is expensive to retrofit.
9. Capture audio with AudioWorklet at 16 kHz mono PCM, and keep playback flushable.
10. Measure before claiming. Performance and accuracy claims need numbers, hardware, dataset, and method recorded in docs/benchmarks.
11. When you make a design decision, add a short ADR in docs/adr/NNNN-title.md (context, decision, alternatives, consequences).
12. Never claim something works unless you ran it. Report exactly what you ran and what the output was. If you could not verify something, say so.
13. Never fabricate recordings, transcripts, user data, quotes, or benchmark numbers.
14. Time-box everything. If a task will take more than its sprint budget, stop, say so, and propose the smallest cut.

## Definition of done for any task
Code + tests passing + lint/type clean + docs updated + ADR if a decision was made + a short summary of what changed and how it was verified.

## Working style
Small commits with clear messages. Ask me when requirements are ambiguous rather than guessing. Point out risks and tradeoffs honestly, including when my idea is a bad one.

## Documentation Maintenance Contract

Every future implementation prompt must:

1. Update `docs/progress.md` with what was implemented.
2. Update `docs/decision.md` when an architectural or technical decision is made.
3. Update `docs/architecture-deep-dive.md` when internal architecture, interfaces, data flow or lifecycle behavior changes.
4. Update `docs/interview-guide.md` with new interview questions and grounded explanations arising from the implementation.
5. Update `docs/README.md` if the documentation structure changes.
6. Link the implementation commit.
7. Distinguish implemented, partially implemented, planned and measured functionality.
8. Never fabricate performance or accuracy numbers.
9. Never overwrite historical decisions without recording why they were superseded.

Future AI agents should read these documents before answering questions about the project.
