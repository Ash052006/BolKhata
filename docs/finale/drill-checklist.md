# BolKhata Finale Readiness Drill & Failure Contingency Plan

> **Objective:** Ensure 100% operational readiness for the on-campus finale live demonstration in front of Wispr leadership, AI founders, and investors.

---

## 1. 3-Hour Rapid DomainPack Build Drill

When the final round brief or domain adaptation is revealed, follow this 3-hour timed sequence:

```
[00:00 - 00:30] Phase 1: Schema & Contracts
  1. Define Pydantic models in domains/<name>/models.py.
  2. Implement DomainIntent and action parameter schemas.
  3. Write 10 unit tests for schema validation.

[00:30 - 01:30] Phase 2: Deterministic Rules & Resolver
  1. Write regex & grammatical extraction rules in domains/<name>/parser.py.
  2. Wire S2 number parser & unit normalizer.
  3. Wire RapidFuzz entity resolver for domain nouns.
  4. Implement DomainPack interface in domains/<name>/pack.py.

[01:30 - 02:15] Phase 3: Read-Back & Trust Confirmation
  1. Write deterministic read-back templates in Hindi & English.
  2. Wire confirmation grammar and pending entry patching.
  3. Add domain REST routes and WebSocket session integration.

[02:15 - 03:00] Phase 4: Verification & Demo Assets
  1. Run full test suite: pytest ../tests/ -v.
  2. Seed deterministic demo data via scripts/demo_reset.sh.
  3. Rehearse 90-second live presentation twice.
```

---

## 2. Live Demo Failure Contingency Plan

| Failure Scenario | Live Symptom | Root Cause | Immediate Action & Contingency |
|---|---|---|---|
| **No Wi-Fi / Severed Internet** | Offline banner appears | Venue network congestion / captive portal | **Feature, not a bug:** BolKhata's circuit-breaker automatically routes to local MLX-Whisper and deterministic rules. Transaction commits locally to SQLite WAL. Point this out as proof of edge resilience! |
| **Microphone Mute / Dead Audio** | Red mic icon or browser permission error | OS permission revoked or hardware mute | Tap the **"Keyboard Fallback"** input field on screen; type *"Sharma ji 250 udhaar"*. The system extracts and speaks read-back normally. |
| **Severe Acoustic Screech / Feedback** | Audio distortion | Speaker volume echoing into mic | Toggle **Quiet Mode** toggle switch on screen. All confirmations render as high-contrast visual cards without speaker audio. |
| **Model Server Crash / OOM** | HTTP 503 / WebSocket close | Low memory | Run `./scripts/demo_reset.sh` in terminal (takes < 2 seconds). Restart `uvicorn bolkhata.api.app:app`. |
| **Venue Power Outage** | External monitors disconnect | Power strip trip | Switch seamlessly to MacBook Air M5 battery power; system consumes < 15W under full local MLX inference. |
