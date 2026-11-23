# BolKhata — Known Issues & Architectural Simplifications

> **Document Type:** Honest Technical Register of Current Limitations & Shortcuts  
> **Last Updated:** Sprint S1 Stage 4 (Push-to-Talk Vertical Slice)  
> **Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)  

In adherence to the project's engineering principles (*"Never claim without a measurement"*, *"Honesty over optimism"*), this document records the intentional simplifications, crude edges, and unmeasured components present in the codebase at this stage.

---

## 1. Speech & Audio Processing

1. **Non-Causal Speech Recognition:**
   - OpenAI Whisper and MLX-Whisper are autoregressive sequence-to-sequence models operating on log-mel spectrogram windows. They do not natively support causal token-by-token streaming while audio is being spoken.
   - *Current Implementation:* Audio frames are buffered during the `LISTENING` state and transcribed upon `end_utterance`.
   - *Planned Resolution:* Evaluation of sliding-window chunking or local causal ASR engines in future stages.

2. **Mock Speech Synthesis in CI:**
   - The default `MockTTSProvider` generates mathematically valid 16 kHz sine wave PCM bytes to verify pipeline mechanics and Web Audio playback without external weights.
   - Natural Hindi and Indian English voice synthesis will be evaluated with a dedicated local TTS runtime.

3. **No Hardware Acoustic Echo Cancellation (AEC):**
   - Push-to-talk eliminates feedback loops because the microphone is muted during assistant speech. If a user interrupts via barge-in, browser-native `echoCancellation: true` is requested, but server-side DSP acoustic filtering is not implemented.

---

## 2. Intelligence & Extraction

1. **Colloquial Spoken Number Parsing (Pending S2):**
   - Colloquial Indian numeric forms (*"dhai sau"* = 250, *"dedh hazaar"* = 1500, *"sawa sau"* = 125) are not yet mathematically normalized.
   - *Planned Resolution:* Sprint S2 Spoken-Number Parser (`backend/src/bolkhata/domains/common/numbers.py`).

2. **DomainPack & Append-Only Ledger Extraction (Pending S3):**
   - The current LLM dialogue stage uses mock tokens (*"Sharma ji, do sau pachaas rupaye udhaar. Sahi hai?"*).
   - Dynamic intent classification, customer fuzzy entity matching, and append-only database transaction rows are scheduled for Sprint S3.

---

## 3. Storage & Networking

1. **Local In-Memory WebSocket Session State:**
   - Session state machines and audio buffers are held in server process memory.
   - If the FastAPI process restarts mid-utterance, active push-to-talk turns are discarded. The client detects disconnect and resets to `IDLE`.
   - Horizontal scaling across multi-node server clusters will require a distributed pub/sub broker (e.g. Redis Streams).

2. **Offline Fallback & Mobile PWA Sync (Pending S5):**
   - If the network drops, the current client shows a disconnected badge. Local IndexedDB event queueing and conflict-free synchronization are planned for Sprint S5.
