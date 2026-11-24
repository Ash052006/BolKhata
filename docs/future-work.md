# BolKhata Architectural Registry: Deliberate Shortcuts & Future Roadmap

> **Document Classification:** Engineering Transparency & Technical Debt Register
> **Repository:** BolKhata (बोलखाता)
> **Status:** Release Freeze v0.1.0 (November 2026)

---

## 1. Intentional Shortcuts & Pragmatic Architecture Decisions

In a focused engineering build for the Scaler x Wispr Flow hackathon, certain constraints were chosen deliberately to prioritize **reliability, financial safety, and reproducible measurements** over peripheral complexity.

This document records these decisions honestly, explains why they were taken, and provides the architectural plan to scale each component.

---

### Shortcut 1: Push-to-Talk (PTT) vs Continuous Streaming Acoustic Barge-In
- **Current Behavior:** The merchant presses and holds a screen button (or hardware pedal) to speak, and releases it to trigger processing. Continuous hot-word listening (*"Hey Bolkhata"*) and real-time barge-in during audio read-back are omitted.
- **Why Taken:**
  - In a noisy kirana shop (traffic horns, radio, counter chatter), continuous open microphones cause severe false-trigger rates.
  - Acoustic barge-in requires real-time Acoustic Echo Cancellation (AEC) across the operating system audio stack so the microphone doesn't transcribe the app's own TTS read-back.
  - PTT guarantees bounded audio buffers, clear turn boundaries, and immediate privacy.
- **Future Solution:**
  - Integrate a WebRTC AEC3 audio pipeline combined with streaming Silero VAD.
  - Implement an on-device wake-word engine (openWakeWord) running locally in a dedicated WebAssembly or native thread.

---

### Shortcut 2: Single-Counter SQLite WAL vs Distributed Multi-Tenant PostgreSQL
- **Current Behavior:** Default storage runs on local SQLite with Write-Ahead Logging (WAL) and synchronous normal mode. A PostgreSQL profile is provided in Docker Compose for enterprise deployments.
- **Why Taken:**
  - A micro-merchant operates a single checkout counter. SQLite requires zero external daemons, zero configuration, and eliminates network latency between backend and database.
  - File-based SQLite makes data ownership trivial: merchants can copy their entire ledger database onto a USB drive.
- **Future Solution:**
  - Implement local-first CRDT synchronization (e.g., ElectricSQL or Automerge) enabling offline sync across multiple counter tablets and the shopkeeper's personal mobile phone.

---

### Shortcut 3: Single-Shop Authentication vs Multi-Tenant RBAC
- **Current Behavior:** The app runs in single-merchant counter mode without username/password login walls.
- **Why Taken:**
  - A busy shopkeeper cannot afford session timeouts, password resets, or captcha challenges during peak store hours.
  - The threat model assumes physical control of the counter machine.
- **Future Solution:**
  - Introduce WebAuthn / Passkey biometric unlock (Touch ID / Android fingerprint) on app launch without recurring friction.

---

### Shortcut 4: Deterministic Templated Spoken Read-Back vs Generative Voice
- **Current Behavior:** Spoken confirmations are assembled from deterministic templates and a mathematical number-to-words generator (`number_words.py`), rather than allowing an LLM to generate conversational replies.
- **Why Taken:**
  - Money safety invariant: A probabilistic model must **never** be responsible for speaking a monetary amount to a customer. Hallucinating ₹2500 instead of ₹250 destroys merchant credibility.
  - Generative TTS introduces 300–800ms of audio generation latency; templated synthesis starts in under 50ms.
- **Future Solution:**
  - Deploy an edge-optimized neural phoneme synthesizer (e.g. Piper TTS with Indian English/Hindi models) preserving the deterministic phonetic input while providing more natural intonation.

---

### Shortcut 5: Two-Phase Rules + Hosted LLM Fallback vs Heavy On-Device SLM
- **Current Behavior:** The primary extraction engine uses a pure-Python deterministic rule parser. Ambiguous or grammatically complex sentences fall back to Groq Cloud LLM, which is circuit-broken to local rules when offline.
- **Why Taken:**
  - 85%+ of daily kirana transactions (*"Sharma ji ko 250 udhaar"*, *"Verma ji 100 jama"*) follow standard syntactic structures that require zero neural tokens.
  - Running a 7B parameter LLM locally on an 8 GB or 16 GB machine competes with Whisper for unified memory bandwidth and thermal dissipation.
- **Future Solution:**
  - Fine-tune a specialized 1B–2B Small Language Model (e.g., SmolLM2 or Qwen2.5-1.5B) quantized to 4-bit MLX, running in a dedicated low-priority background process on Apple Silicon.
