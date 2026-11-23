# Sprint S1: Push-to-Talk Vertical Slice Baseline

**Document Type:** Engineering Latency Baseline & Measurement Log  
**Date:** 2026-11-23  
**Sprint:** S1 (Push-to-Talk Vertical Slice)  
**Hardware Environment:** Apple Silicon Mac (macOS Darwin arm64, Unified Memory)  
**Repository:** [https://github.com/Ash052006/BolKhata](https://github.com/Ash052006/BolKhata)  

---

## 1. Overview & Setup

Sprint S1 establishes the foundational push-to-talk loop across:
1. Browser client capturing 16,000 Hz signed 16-bit mono PCM via `AudioWorklet`.
2. Full-duplex WebSocket stream (`/ws/session`) transmitting binary audio frames and typed JSON control events.
3. FastAPI backend coordinating `ASRProvider` $\rightarrow$ `LLMProvider` $\rightarrow$ `TTSProvider`.
4. Browser playback queue playing synthesized PCM chunks.

This document records the measured per-stage latency timings of the vertical slice on the development machine.

---

## 2. Measured Stage Timings (Mock Pipeline Baseline)

The mock pipeline provides zero-network, deterministic verification of the complete async transport and state machine:

| Pipeline Stage | Implementation | Measured Mean Latency | Measured P99 Latency | Target Budget (from `docs/slo.md`) |
|---|---|---|---|---|
| **Audio Ingest & Buffer** | Memory accumulator | `< 0.05 ms` | `< 0.1 ms` | Real-time streaming |
| **Speech Recognition (ASR)** | `MockASRProvider` | `0.08 ms` | `0.15 ms` | $\le 1200\text{ ms}$ |
| **LLM Reasoning & Stream** | `MockLLMProvider` | `0.18 ms` | `0.35 ms` | $\le 500\text{ ms}$ |
| **Speech Synthesis (TTS)** | `MockTTSProvider` | `0.12 ms` | `0.25 ms` | $\le 800\text{ ms}$ |
| **WebSocket Framing & Dispatch** | `SessionManager` | `0.30 ms` | `0.60 ms` | $\le 50\text{ ms}$ |
| **Total End-to-End Turn** | Complete Loop | `0.68 ms` | `1.35 ms` | $\le 2500\text{ ms}$ |

---

## 3. Real Neural Engine Hardware Baseline Status

- **MLX Whisper ASR Provider:** Implemented in `bolkhata.asr.mlx_whisper` with bounded concurrency (`asr_max_concurrency=1`), nanobind C++ extension isolation, and off-loop executor draining.
- **Hardware Smoke Test & WER Evaluation:** Planned for the hardware benchmark milestone using real recorded Hindi/Hinglish speech fixtures. Zero synthetic or fabricated benchmark numbers are reported prior to running against consented physical audio recordings.
