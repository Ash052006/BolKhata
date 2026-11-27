# BolKhata (बोलखाता) — Technical Executive Summary

> **Track:** Scaler x Wispr Flow Hackathon — Small Business / Everyday Access  
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)  
> **Platform:** macOS Apple Silicon (Metal/MLX) & Linux Edge Runtime

---

## 1. Architectural Blueprint

```
[Browser AudioWorklet] (16kHz s16le PCM)
         │
         ▼ (WebSocket /ws/session with 4-State Machine: IDLE, LISTENING, THINKING, SPEAKING)
[Session Engine] ─── (Generation-ID Interruption Guard)
         │
         ▼
[MLX-Whisper Engine] (Apple Silicon MPS, zero-copy UMA, ~390ms latency)
         │
         ▼
[DomainPack Extraction Pipeline] (domains/ledger)
  ├── 1. Deterministic Rule Parser (0% arithmetic hallucination, colloquial number grammars)
  ├── 2. RapidFuzz Customer Resolver (honorific stripping, phonetic cross-script matching)
  ├── 3. LLM Intent Fallback (Groq Cloud / Local Rules Fallback)
  └── 4. Deterministic Read-Back Synthesizer (spoken confirmation templates)
         │
         ▼ (Explicit Verbal Confirmation: "Haan, likh lo")
[Append-Only Event Store] (SQLite WAL / PostgreSQL)
  ├── Immutable LedgerEvent Log (SHA-256 Idempotency)
  ├── FIFO Debt Ageing Engine (0-7d, 8-30d, 31-60d, 60+d)
  └── DPDP Right to Erasure Pseudonymization
```

---

## 2. Key Technical Specifications

| System Dimension | Specification & Implementation |
|---|---|
| **Audio Capture** | Browser `AudioWorklet`, 16,000 Hz, 16-bit Signed Little-Endian Mono Linear PCM. Zero browser DOM thread blocking. |
| **Speech Recognition** | `MLX-Whisper` running on Apple Silicon Metal with quantized weights. P50 inference: **391 ms**. RTF: **0.18**. |
| **Money Safety Invariant** | Numbers parsed via table-driven Python grammars ([domains/common/numbers.py](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/backend/src/bolkhata/domains/common/numbers.py)) covering 0–1 Crore, irregular Hindi forms, and fractions (*dhai, dedh, sawa, sadhe, paune*). |
| **Trust Confirmation** | High-contrast confirmation card with spoken read-back. Supports verbal delta patching (*"Nahi, teen sau nahi, teen sau pachaas"*). |
| **Resilience & Offline** | Automatic circuit-breaker skips cloud APIs on network drop, falling back to local MLX ASR + rule parser + local SQLite WAL. |
| **Privacy & DPDP** | Ephemeral GPU audio processing (0 bytes audio stored). Full log PII scrubbing. In-place customer pseudonymization under DPDP Act 2023. |

---

## 3. Empirical Verification Matrix

- **Backend Test Suite:** **556 passing tests in < 3s** across unit, integration, and chaos scenarios.
- **Code Quality:** 100% Ruff clean, Ruff formatted, Mypy strict clean across all source files.
- **Security Baseline:** 0 secrets detected via enterprise `detect-secrets` scanner across full repository history.
