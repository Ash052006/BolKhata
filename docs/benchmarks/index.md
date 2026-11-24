# BolKhata Benchmark Catalog & Empirical Evidence Index

> **Target Platform:** Apple Silicon MacBook Air M5 (16 GB Unified Memory, macOS Darwin arm64)
> **Evaluation Date:** November 2026
> **Repository Policy:** Zero data fabrication. All metrics are measured from deterministic fixtures or native hardware runs.

---

## Benchmark Index

| Report | Sprint / Feature | Target Component | Key Finding / Metric | Status |
|---|---|---|---|---|
| [slice-baseline.md](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/docs/benchmarks/slice-baseline.md) | Sprint S1 | End-to-End WebSocket Voice Loop | P50 turnaround **412 ms**, audio capture buffer bounded to 16 kHz mono. | Verified |
| [asr-v0.md](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/docs/benchmarks/asr-v0.md) | Sprint S2 | Spoken Number & Idiom Normalization | 100% exact-match on Indian colloquial numbers (*dhai sau*, *dedh hazaar*, *paune do sau*). | Verified |
| [extraction-v0.md](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/docs/benchmarks/extraction-v0.md) | Sprint S3 | DomainPack Rules-First Extraction | 96.7% field-level accuracy; 0% LLM arithmetic hallucination. | Verified |
| [hardware-v0.md](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/docs/benchmarks/hardware-v0.md) | Sprint S5 | Apple Silicon M5 vs CPU vs RTX 3050 | M5 Metal/MLX achieves **0.18 RTF**, sub-500ms P50 latency, and 0 dB silent fanless operation. | Verified |
| [biasing-v0.md](file:///Users/aishwarysaxena/Desktop/Projects/BolKhata/docs/benchmarks/biasing-v0.md) | Feature F1 | Customer & Commodity Vocabulary Biasing | Customer name recall increased from **73.3% $\rightarrow$ 93.3%** (+20.0%) with 9ms latency delta. | Verified |

---

## Model Cards & Operational Boundaries

### 1. Automatic Speech Recognition (ASR)
- **Primary Engine:** MLX-Whisper (`mlx-community/whisper-large-v3-turbo`)
- **Runtime:** Apple Silicon Metal Performance Shaders (MPS), zero-copy unified memory.
- **Quantization:** 4-bit / 8-bit quantized weights (~800 MB to 1.6 GB VRAM).
- **Known Limitations:**
  - High acoustic noise ($\le 5\text{ dB}$ SNR, loud mixer grinders or continuous traffic horns) degrades transcription accuracy.
  - Mitigated by explicit spoken read-back and confirmation invariant before any ledger commit.

### 2. Large Language Model (Extraction Fallback)
- **Primary Hosted Engine:** Groq Cloud (`llama-3.3-70b-versatile` / `mixtral-8x7b-32768`)
- **Local Fallback Engine:** Deterministic rule parser (`bolkhata.domains.ledger.parser`).
- **Safety Invariant:** Money amounts and mathematical decisions are strictly computed by deterministic Python code, never by the LLM.

### 3. Text-to-Speech (TTS)
- **Primary Engine:** Local edge TTS / deterministic web speech synthesis.
- **Spoken Templates:** Number-to-words generator (`number_words.py`) covering Hindi and English numeric representations up to 1 Crore.
