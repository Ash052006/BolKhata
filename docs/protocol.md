# BolKhata Realtime WebSocket Protocol

**Version:** 1.0.0
**Transport:** WebSocket (RFC 6455)
**Endpoint:** `/ws/session`
**Audio Format:** 16,000 Hz, 16-bit Signed Linear PCM, Mono, Little-Endian (`pcm_s16le`)

---

## 1. Overview

BolKhata uses a single full-duplex WebSocket connection per interactive push-to-talk session. The protocol interleaves UTF-8 JSON control messages and raw binary audio frames.

### Session Lifecycle & State Machine
Every session adheres strictly to the four-state lifecycle:
```
           +-----------------------------------------+
           |                                         |
           v                                         |
       [ IDLE ] ----(start_utterance)----> [ LISTENING ]
          ^                                     |
          |                                (end_utterance)
          |                                     v
          |                                [ THINKING ]
          |                                     |
          |                              (tts_started)
          |                                     v
          +---------(tts_completed)------- [ SPEAKING ]
```

- **Cancellation / Interruption:** From `LISTENING`, `THINKING`, or `SPEAKING`, a `cancel_utterance` message or client interruption forces an immediate transition back to `IDLE`.
- **Illegal Transitions:** Any out-of-order transition (e.g. `start_utterance` while already in `THINKING`) is rejected with an `error` frame.
- **Generation Tracking:** Whenever a turn transitions to `THINKING`, a new `generation_id` is generated. All subsequent downstream events (`transcript`, `assistant_text`, `audio_chunk`, `timings`) carry this `generation_id`. If a turn is cancelled or superseded, any lingering output with a stale `generation_id` is dropped.

---

## 2. Client-to-Server Messages

### 2.1 `start_utterance` (JSON)
Signals that the shopkeeper has pushed the talk button and microphone recording has begun.

```json
{
  "type": "start_utterance",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "language": "hi",
  "initial_prompt": "Sharma ji, udhaar, jama, chawal"
}
```

- `turn_id` *(string, required)*: Client-generated unique identifier for this turn.
- `language` *(string, optional)*: ISO language code (e.g., `"hi"`, `"en"`). Defaults to `"hi"`.
- `initial_prompt` *(string, optional)*: Contextual vocabulary prompt biasing prefix.

### 2.2 Binary Audio Frame (Binary)
While in `LISTENING` state, the client streams binary messages containing raw uncompressed `pcm_s16le` audio chunks (recommended chunk size: 20 ms to 100 ms, i.e., 640 to 3200 bytes per message).

The server accumulates binary audio in memory. If total duration exceeds `asr_max_duration_seconds` (default 30.0 s), the server automatically finalizes or raises an `AUDIO_TOO_LONG` error.

### 2.3 `end_utterance` (JSON)
Signals that the shopkeeper has released the talk button. Triggers state transition to `THINKING` and begins speech recognition.

```json
{
  "type": "end_utterance",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### 2.4 `cancel_utterance` (JSON)
Aborts the current turn immediately, discards buffered audio, and transitions to `IDLE`.

```json
{
  "type": "cancel_utterance",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

---

## 3. Server-to-Client Messages

### 3.1 `session_state` (JSON)
Emitted whenever the state machine changes state.

```json
{
  "type": "session_state",
  "session_id": "urn:uuid:8b1a4570-8d59-4d87-9bb3-7848f2c69d80",
  "state": "IDLE",
  "turn_id": null,
  "generation_id": null
}
```

Valid `state` values: `"IDLE"`, `"LISTENING"`, `"THINKING"`, `"SPEAKING"`.

### 3.2 `transcript` (JSON)
Emitted when ASR transcription finishes.

```json
{
  "type": "transcript",
  "session_id": "urn:uuid:8b1a4570-8d59-4d87-9bb3-7848f2c69d80",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "generation_id": "urn:uuid:12345678-1234-5678-1234-567812345678",
  "text": "Sharma ji ko dhai sau udhaar",
  "confidence": 0.94,
  "language": "hi",
  "duration_ms": 2400.0,
  "words": [
    {"word": "Sharma", "start_ms": 0.0, "end_ms": 420.0, "confidence": 0.95},
    {"word": "ji", "start_ms": 420.0, "end_ms": 650.0, "confidence": 0.98},
    {"word": "ko", "start_ms": 650.0, "end_ms": 820.0, "confidence": 0.96},
    {"word": "dhai", "start_ms": 820.0, "end_ms": 1200.0, "confidence": 0.91},
    {"word": "sau", "start_ms": 1200.0, "end_ms": 1600.0, "confidence": 0.93},
    {"word": "udhaar", "start_ms": 1600.0, "end_ms": 2200.0, "confidence": 0.92}
  ]
}
```

### 3.3 `assistant_text` (JSON)
Emitted as LLM/template assistant response tokens are produced.

```json
{
  "type": "assistant_text",
  "session_id": "urn:uuid:8b1a4570-8d59-4d87-9bb3-7848f2c69d80",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "generation_id": "urn:uuid:12345678-1234-5678-1234-567812345678",
  "token": "Sharma ji, do sau pachaas rupaye udhaar. Sahi hai?",
  "is_final": true
}
```

### 3.4 `audio_chunk` (JSON or Binary)
Synthesized PCM audio chunks for client-side playback.

```json
{
  "type": "audio_chunk",
  "session_id": "urn:uuid:8b1a4570-8d59-4d87-9bb3-7848f2c69d80",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "generation_id": "urn:uuid:12345678-1234-5678-1234-567812345678",
  "sequence_number": 0,
  "is_final": false,
  "sample_rate": 16000,
  "data_b64": "<base64_encoded_pcm_s16le>"
}
```

### 3.5 `timings` (JSON)
Per-stage telemetry emitted at turn completion.

```json
{
  "type": "timings",
  "session_id": "urn:uuid:8b1a4570-8d59-4d87-9bb3-7848f2c69d80",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "generation_id": "urn:uuid:12345678-1234-5678-1234-567812345678",
  "asr_ms": 115.4,
  "llm_ms": 32.1,
  "tts_ms": 84.7,
  "total_ms": 232.2
}
```

### 3.6 `error` (JSON)
Emitted when an operational or validation error occurs.

```json
{
  "type": "error",
  "session_id": "urn:uuid:8b1a4570-8d59-4d87-9bb3-7848f2c69d80",
  "turn_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "generation_id": null,
  "code": "INVALID_STATE_TRANSITION",
  "message": "Cannot start utterance while state is THINKING."
}
```
