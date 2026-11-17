# BolKhata Documentation Knowledge Base

Welcome to the engineering documentation knowledge base for **BolKhata**, a voice-first ledger for Indian kirana shopkeepers.

This directory serves as the centralized, living engineering repository for architecture specifications, design rationale, internal implementation mechanics, and interview defense guides.

---

## Documentation Index

| Document | Question It Answers | Primary Audience & When to Use It |
|---|---|---|
| [**progress.md**](progress.md) | **What did we do?** | Project history, sprint milestones, completed tasks, and verified Git evidence. Consult to know the exact status of any feature or milestone. |
| [**decision.md**](decision.md) | **Why did we do it?** | Chronological log of architectural and technical decisions, alternatives rejected, trade-offs, and consequences. Consult before refactoring or proposing architectural changes. |
| [**architecture-deep-dive.md**](architecture-deep-dive.md) | **How does it work?** | In-depth technical breakdown of internal mechanics, provider registry state machines, audio PCM normalization, lifecycles, and failure handling. |
| [**interview-guide.md**](interview-guide.md) | **How do I explain it?** | Technical interview questions, system defense scenarios, critical challenges, and preparation checklists grounded in actual code. |
| [**adr/**](adr/) | **What was formally accepted?** | Formal Architecture Decision Records (ADR 0001: Tooling, ADR 0002: Domain Boundary, ADR 0003: Provider Interfaces). |
| [**slo.md**](slo.md) | **What are the performance goals?** | Service Level Objectives and latency budget allocations on target hardware. |

---

## Source-of-Truth Hierarchy

When evaluating system behavior or resolving conflicting statements between documents, always adhere to the following strict order of precedence:

1. **Actual Source Code and Tests:** The code and passing tests in `backend/`, `frontend/`, and `tests/` represent the ultimate truth of what is currently implemented.
2. **Accepted ADRs and Decision Records:** `docs/adr/*.md` and `docs/decision.md` document binding architectural decisions and rationale.
3. **`bolkhata-agent-prompts.md`:** The master project roadmap and original functional/non-functional requirements.
4. **`docs/progress.md`:** The verified chronological log of sprint accomplishments, Git commits, and test metrics.
5. **`docs/architecture-deep-dive.md`:** Detailed explanations of system internals, differentiating implemented from planned features.
6. **`docs/interview-guide.md`:** Framing, defense strategies, and interview explanations.

> **Conflict Resolution Rule:** If any document claims a feature is implemented, but the source code or tests do not exist, the document is in error. Never repeat an outdated or false claim. Correct the document immediately to reflect reality.

---

## How AI Agents Must Use These Documents

AI coding agents working on BolKhata must follow these operating principles:
1. **Read Before Acting:** Inspect `docs/README.md`, `docs/progress.md`, and `docs/decision.md` before planning or implementing changes.
2. **Respect Status Boundaries:** Never assume a feature is implemented simply because it appears in the roadmap or prompts. Check the actual source files and tests.
3. **Preserve Document Invariants:**
   - When completing an implementation task, update `docs/progress.md`.
   - When making an architectural choice, log it in `docs/decision.md`.
   - When modifying internal mechanics, update `docs/architecture-deep-dive.md`.
   - When encountering a notable bug or design trade-off, add it to `docs/interview-guide.md`.
4. **Honesty Over Optimism:** Clearly label every component as `[IMPLEMENTED]`, `[PARTIALLY IMPLEMENTED]`, or `[PLANNED]`. Never fabricate benchmark numbers or user study results.

---

## Documentation Maintenance Lifecycle

Whenever code is added, modified, or refactored:
1. Ensure unit and integration tests pass.
2. Verify quality gates (Ruff, Mypy, pre-commit, detect-secrets).
3. Update the corresponding sections in `docs/progress.md`, `docs/decision.md`, `docs/architecture-deep-dive.md`, and `docs/interview-guide.md`.
4. Reference the resulting Git commit hash in `docs/progress.md`.
