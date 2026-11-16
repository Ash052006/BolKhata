# 2. Hackathon Scope and Domain Isolation Boundary

Date: 2026-11-16
Status: Accepted

## Context

The Scaler x Wispr Flow hackathon problem statement centers on voice-first tools for India. Bolkhata targets the Small Business track (kirana shopkeepers). However, hackathon requirements, problem statement nuances, and evaluation rubrics often evolve between rounds (Round 1 idea, Round 2 mystery problem statement, Round 3 finale).

A common architectural pitfall is tightly coupling voice pipelines (ASR, audio streaming, VAD, LLM intent extraction, TTS read-back) directly into domain entities (e.g., kirana credit ledger models, balance calculations, udhaar reconciliation). Doing so makes adapting to new problem statements or pivoting domains prohibitively slow.

At the same time, prematurely building complete abstraction layers (such as full DomainPack implementations, abstract provider factories, or unused ASR/TTS interfaces) before evaluating concrete models and runtime constraints adds unnecessary complexity during Sprint S0.

## Decision

1. **Defer Provider and Domain Implementations to S1 & S3**:
   - In Sprint S0, create only package boundaries: `bolkhata/domains/` and `frontend/src/apps/ledger/`.
   - Do NOT implement dummy/empty ASR, TTS, LLM provider classes or DomainPack protocols until real model evaluations and concrete domain requirements occur in S1 and S3.

2. **Strict Isolation Boundary**:
   - Ledger-specific domain logic, database tables, prompts, and actions shall live exclusively inside `backend/src/bolkhata/domains/ledger/` and `frontend/src/apps/ledger/`.
   - Code outside `domains/` is forbidden from importing from `domains/ledger`.
   - When introduced in S3, each domain must conform to a standardized interface (schema, normalizers, actions, read-back templates, eval sets) so that swapping or adding a domain does not alter the core real-time voice pipeline.

3. **No Heavy Distributed Systems**:
   - Enforce push-to-talk interaction. No WebRTC, no barge-in, no Kubernetes, no distributed workers, and no Redis in S0.
   - Run everything with a single `docker compose up` command.

## Consequences

- S0 codebase remains clean, focused strictly on foundational infrastructure (FastAPI app factory, health checks, DB readiness, logging with fail-closed redaction, CI/CD, and dockerization).
- S1 can evaluate concrete speech models (`faster-whisper`, `mlx-whisper`) on real audio fixtures before locking down provider protocol definitions.
- The system remains easily extensible if Round 2 reveals an updated or adjacent problem statement.
