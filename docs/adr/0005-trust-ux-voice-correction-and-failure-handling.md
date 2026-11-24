# 5. Trust UX, Voice Correction Patches, and Circuit-Breaker Graceful Degradation

Date: 2026-11-23
Status: Accepted

## Context

In an Indian retail (Kirana) environment, the merchant is frequently occupied weighing commodities, packing goods, or tending to customers. They cannot be expected to look down at a mobile phone screen to verify every transcription. Furthermore:
1. **Silent Errors Destroy Trust:** If a voice system mishears ₹300 as ₹350 (or vice versa) and silently records it, the financial discrepancy will cause immediate merchant distrust and loss of business.
2. **Interactive Verbal Corrections:** In real dialogue, users do not start over from scratch when an assistant makes an error. They correct the specific mistaken entity (*"nahi, teen sau nahi, teen sau pachaas"* or *"Sharma ji nahi, Verma ji"*).
3. **High-Risk Thresholds:** Large transaction amounts (e.g. $\ge ₹5,000$), low ASR acoustic confidence ($< 0.80$), phonetic ambiguity, or unverified customers demand heightened scrutiny.
4. **Provider Fragility:** Neural models, cloud APIs, audio hardware, and SQLite database locks are prone to transient dropouts. The application must not crash or leave the merchant hanging.

## Decision

1. **Hard Confirmation Safety Invariant:**
   - No ledger entry is ever committed to persistent storage without explicit merchant confirmation (`is_confirmed=True`).
   - Any attempt to commit an unconfirmed pending entry raises an unbypassable exception (`ValueError`).
   - The confirmation grammar recognizes explicit positive cues (`haan`, `sahi hai`, `theek hai`, `likh do`, `yes`, `हाँ`, `सही है`, `ठीक है`), negative rejections (`nahi`, `galat`, `no`, `गलत`), and stops (`ruko`, `cancel`, `रद्द करो`). Any ambiguous utterance resolves strictly to `UNCLEAR` (triggering a verbal re-ask), never defaulting to 'yes'.

2. **Deterministic Mathematical Spoken Read-Back:**
   - Read-back strings are generated strictly from deterministic Python templates (`number_to_hindi_words`, `number_to_english_words`), never by an LLM.
   - Amounts are expanded into spoken words in both Romanized Hindi (*"Sharma ji, teen sau pachaas rupaye udhaar. Sahi hai?"*) and Devanagari.

3. **High-Risk Thresholds & Digit-by-Digit Verbal Read-Back:**
   - If an amount exceeds ₹5,000, ASR confidence is $< 0.80$, intent is ambiguous, or customer is in a gray zone, the system transitions to `risk_level="high"`.
   - High-risk read-backs pronounce the amount both as compound words and digit-by-digit:
     *"Chetavni: Bada amount hai — barah hazaar panch sau rupaye (ek do panch shunya shunya). Sharma ji ke khate me likhein? Haan ya nahi bolein."*

4. **In-Flight Voice Correction Patching (`PendingEntry`):**
   - Uncommitted transactions are maintained in a mutable `PendingEntry` state.
   - When a correction is spoken (*"nahi teen sau nahi, teen sau pachaas"*), the parser extracts the replacement entity, updates the target field, logs the modification in `patch_history`, and regenerates the read-back.
   - Bounded rounds: After 3 consecutive corrections, the system transitions to manual screen review fallback to avoid dialogue loops.

5. **Graceful Degradation & Chaos Resilience:**
   - **ASR Failure:** Prompts the merchant with a clear typed-input fallback notice.
   - **LLM Failure:** Gracefully degrades to the deterministic rules-only parser with `provenance={"llm_fallback": "rules_only"}`.
   - **TTS Failure:** Omits audio playback while preserving visual on-screen read-back.
   - **Database Write Failure:** Buffers transaction payloads in a `LocalRetryQueue` preserving exact SHA-256 idempotency keys. Re-executing retries upon reconnect commits records without duplicate posting.

## Consequences

- Zero risk of silent financial balance corruption.
- Merchants can use the voice interface hands-free with complete auditory confidence.
- System remains resilient to intermittent provider and connectivity outages.
