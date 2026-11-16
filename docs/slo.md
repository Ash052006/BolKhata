# Service Level Objectives (SLOs) & Latency Budget

> Note: Targets are deliberately unpopulated at Sprint S0.
> Targets must be measured on hardware (MacBook Apple Silicon & Windows RTX 3050)
> with real recorded audio and benchmarks, never fabricated.

| Metric | Measurement Unit | Description | Target | Measured Value (M1/M2/M3) | Measured Value (RTX 3050) | Status |
|---|---|---|---|---|---|---|
| PTT-to-first-token | ms | Time from push-to-talk button release to first streaming token | | | | TBD |
| PTT-to-complete-transcript | ms | Time from button release to final ASR transcript | | | | TBD |
| Intent & Entity Extraction Latency | ms | Time taken by deterministic parser / LLM to extract ledger entry | | | | TBD |
| TTS First Audio Chunk (TTFB) | ms | Time from read-back text generated to first audio chunk played | | | | TBD |
| Total Turn-Around Latency | ms | End-to-end time from PTT release to confirmation prompt playback | | | | TBD |
| Amount Extraction Accuracy | % | Accuracy of numeric amounts extracted against ground truth | | | | TBD |
| Customer Name Resolution | % | Top-1 match rate against existing shop customer database | | | | TBD |
| Offline Availability | % | Percentage of core ledger recording flows operational without internet | | | | TBD |
| API /health P99 Latency | ms | P99 response time for GET /health | | | | TBD |
| API /ready P99 Latency | ms | P99 response time for GET /ready under healthy DB | | | | TBD |
