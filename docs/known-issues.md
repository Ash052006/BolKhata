# BolKhata — Known Issues & Architectural Boundaries

> **Document Type:** Honest Technical Register of Current Limitations & Operational Boundaries
> **Last Updated:** Release Freeze v0.1.0 (Sprint S6, November 2026)
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)

In adherence to BolKhata's core engineering principles (*"Never claim without a measurement"*, *"Honesty over optimism"*), this document records the intentional boundaries, known edge cases, and architectural constraints present in the v0.1.0 release.

---

## 1. Speech & Acoustic Processing

1. **Autoregressive Segment Decoding:**
   - OpenAI Whisper and MLX-Whisper are sequence-to-sequence transformers operating on 30-second log-mel spectrogram windows. They do not perform streaming token emission during active speech.
   - *Current Behavior:* 16 kHz mono PCM frames are buffered during the `LISTENING` state and transcribed upon push-to-talk button release. Turnaround latency on Apple Silicon M5 is **391 ms P50**, which feels instantaneous to retail merchants.
2. **Heavy Acoustic Noise at Counter (< 5 dB SNR):**
   - High background noise (industrial spice grinders, continuous diesel engine horns) can degrade transcription tokens.
   - *Mitigation:* Bounded risk thresholds in `trust.py` detect low ASR confidence and force an explicit digit-by-digit spoken read-back before committing transactions.
3. **Absence of Server-Side Acoustic Echo Cancellation (AEC):**
   - The system enforces push-to-talk turn boundaries, eliminating feedback loops during normal interaction. Continuous open-mic barge-in with server-side DSP AEC is reserved for future versions (see [docs/future-work.md](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/docs/future-work.md)).

---

## 2. Intelligence & Natural Language Processing

1. **Phonetic Surname Ambiguities (*"Sharma"* vs *"Varma"*):**
   - When background noise obscures the initial consonant between phonetically adjacent surnames, fuzzy token matching falls into an ambiguous gray zone ([0.65, 0.85)).
   - *Behavior:* The system does not guess or silently merge accounts; it presents a disambiguation query (*"Sharma ji ya Verma ji?"*).
2. **Zero LLM Arithmetic Invariant:**
   - LLMs are strictly prohibited from calculating balances, computing amounts, or deciding money transactions. All numbers are parsed deterministically via pure Python grammar rules (`numbers.py`, `number_words.py`).

---

## 3. Storage & Privacy Controls

1. **Single-Store SQLite Default:**
   - SQLite WAL mode is ideal for single-counter retail terminals. Horizontal multi-tenant server clustering requires switching to the PostgreSQL database profile (`--profile pg`).
2. **DPDP Customer Erasure Irreversibility:**
   - Per ADR 0006, when a customer exercises their Right to Erasure, all personal identifiers (name, phone) are scrubbed in place to `"Deleted Customer"` and notes are wiped. This action is mathematically irreversible to preserve financial audit sums.
