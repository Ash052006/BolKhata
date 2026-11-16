# Bolkhata: Agent Prompt Playbook

Copy-paste prompts for building **Bolkhata** (working title; check name availability), a voice-first ledger for Indian kirana shopkeepers, for the Scaler x Wispr Flow "India Runs on Voice" hackathon. Use them with an AI coding agent (Claude Code, Cursor, Codex, etc.).

> Hold a button and say: "Sharma ji ko dhai sau udhaar, aur do kilo chawal."
> The app reads back: "Sharma ji, do sau pachaas rupaye udhaar, do kilo chawal. Sahi hai?"
> Say "haan", and it is saved. It keeps working when the network does not.

## Contents

| Part | Contents |
|---|---|
| 0 | Hackathon facts, schedule, tiers, and ground rules |
| 1 | Master Context (put in CLAUDE.md / AGENTS.md) |
| 2 | Sprint prompts S0 to S6 (the core build) |
| 3 | Feature prompts F1 to F10 |
| 4 | Round prompts: R1 (real-user evidence), R2 (Round 2 adaptation), R3 (finale) |
| 5 | Recurring prompts (review, debug, security, ADR, etc.) |
| 6 | Final readiness checklist |
| 7 | Tips for working with the agent and Wispr Flow |

---

## Part 0: Facts, schedule, and ground rules

### Hackathon facts (from the official page, as of 15 Nov 2026)

- **Theme:** build voice-first tools for India, by voice, using Wispr Flow. Five tracks: Civic services, Healthcare, Education, Small business, Everyday access. Bolkhata is a Small business entry.
- **Eligibility:** students and working professionals in India, 18 or over. Free to enter.
- **Registration closes 27 Nov 2026, 11:59 pm IST.** Register with the same email you use to sign in to Wispr Flow.
- **Round 1 (online):** three short activities, Idea (opened 5 Nov), Prompt (opened 13 Nov), Impact (opens 20 Nov). Closes **26 Nov**. Every Round 1 builder gets 1 month of Flow Pro.
- **Round 2 (online):** one problem statement for everyone, live **27 Nov**. Build by voice, solo or a team of up to 3. Submit by **29 Nov**. Shortlist **2 Dec**. Includes an online master class with Wispr.
- **Round 3 (on campus):** **13 Dec**. Shortlisted teams build and demo in person in front of Wispr leadership, AI founders and investors.
- **Teams lock at the first submission, including the Round 1 idea.** Decide solo or team before submitting anything.
- **Prizes:** Rs 30 lakh across 15 teams: 1st Rs 7 L, 2nd Rs 5 L, 3rd Rs 3 L, 4th to 15th Rs 1.25 L each. The page also lists a sponsored trip to Singapore and an interview for a role at Wispr, without saying who gets them.
- **Not stated on the page:** submission rules and judging criteria (each round publishes its own when it goes live), whether pre-existing code is allowed in Round 2, whether Wispr Flow use is required or verified, the Round 2 deadline hour, and the finale campus. Check the dashboard when each round opens, and ask on Discord or at wispr.support@scaler.com.

### Ground rules for the whole build

- **Check the rules first.** Before Round 2, confirm whether pre-existing code is allowed. If it is, make the repo public with its commit history before 27 Nov and disclose it in your submission. If it is not, treat the repo as private practice and rebuild during the round.
- **Do not fabricate data.** Recordings, user-study results, and benchmark numbers must come from real runs. The agent writes the tooling; you collect the data.
- **Push-to-talk only.** No barge-in, WebRTC, Kubernetes, or multi-tenant auth.
- **Money safety.** Amounts are parsed by deterministic code, never decided by the LLM. Every amount is read back and confirmed before saving. The ledger is append-only.
- **Use Wispr Flow** to dictate prompts, notes, and documentation, and keep light evidence of that (a short screen recording and a line in the README).
- **Never claim without a measurement.**

### Feature tiers and the cut line

A solo build in 12 days cannot safely hold every feature plus a real-user pilot. Work in tiers.

| Tier | Features | Rule |
|---|---|---|
| Must | Core loop (S0 to S4), F1 vocabulary biasing, F2 balance queries, F6 data ownership, F7 pilot instrumentation | Do these first; all acceptance criteria must pass |
| Should | F3 ageing and daily digest, F4 WhatsApp reminder drafts, F5 explainability panel | Start only when every Must passes |
| Could | F8 second language, F9 local-first sync, F10 open spoken-amount benchmark | Start only if Musts and Shoulds are done by 24 Nov; otherwise defer to after the hackathon |

**Cut order if you fall behind:** (1) the RTX remote-inference node, (2) offline local-LLM fallback, (3) frontend polish, (4) spoken TTS read-back (keep on-screen read-back), then Coulds, then Shoulds. **Never cut:** number parser tests, evaluation numbers, read-back confirmation, failure handling.

### Day-by-day schedule (2026)

| Dates | Build | In parallel (only you can do this) |
|---|---|---|
| 15-16 Nov | S0: foundation | Register, install Flow, record the first 30 to 40 test utterances |
| 16-18 Nov | S1: push-to-talk slice | Line up 3 to 5 shopkeepers (with consent) |
| 18-20 Nov | S2: number parser and evaluation harness; F7 pilot instrumentation; F1 biasing | Finish recordings (5+ speakers). Impact activity opens on the 20th |
| 20-22 Nov | S3: domain pack and ledger extraction; F2 balance queries | Draft Round 1 submissions |
| 22-24 Nov | S4: read-back, correction, failures; F6 data ownership | Run pilot sessions |
| 24-25 Nov | S5: UI, offline mode, hardware benchmarks; Shoulds only if every Must passes | Analyze pilot data |
| 25-26 Nov | S6: README, demo, tag and freeze | Submit Round 1 by 26 Nov |
| 27-29 Nov | R2: adapt to the revealed problem | Read the rules and judging criteria first |
| 2-13 Dec | R3: finale drill and pitch (if shortlisted) | Rehearse the offline fallback |

### Updated 90-second demo flow

1. A normal entry with read-back and confirmation.
2. A misheard amount caught by read-back, fixed by voice.
3. Wi-Fi turned off; another entry still works in offline mode.
4. A spoken balance query, then the quiet-mode toggle.
5. A WhatsApp reminder draft opening with the right text.
6. The explainability panel on the earlier mistake, then the closing 'aaj ka hisaab'.

If time is short, cut steps 5 and 6 first and keep steps 1 to 4.

---

## How to use the prompts

1. Create the repo, then add the Master Context (Part 1) as `CLAUDE.md` (Claude Code) or `AGENTS.md` / `.cursorrules` (other tools).
2. **One prompt = one session.** Paste it, and tell the agent: *plan first, wait for my approval, then implement.*
3. **Gates are real.** Do not start the next sprint until the acceptance criteria pass and you have run them yourself.
4. **Verify, don't trust.** Run the tests, listen to the audio, read the diff.
5. **Commit per task**, and record decisions in short ADRs (architecture decision records).
6. Replace anything in [BRACKETS] with your own values.

---

## Part 1: Master Context (put this in CLAUDE.md / AGENTS.md)

```
# Project: Bolkhata
A voice-first ledger for Indian kirana shopkeepers (Hindi, English, Hinglish), built for the Scaler x Wispr Flow "India Runs on Voice" hackathon. Reliable, measured, and honest about its limits. Team: [solo / N people].

## Hard constraints
- Hardware: a MacBook (Apple Silicon, 16 GB unified memory) is the primary dev and demo machine. A Windows laptop (RTX 3050 6 GB VRAM, 8 GB RAM) is an optional inference and benchmark node: run only one heavy service at a time there. Prefer small, quantized, or CPU-friendly models and measure memory before loading models together.
- Every model sits behind a provider interface (ASRProvider, TTSProvider, LLMProvider, VADProvider). Swapping a model must not require changes outside its provider module. Hosted providers are optional and always have a local fallback. Prefer open-source and local models; check the hackathon rules on tools and APIs when they are published.
- Must run locally with one command (docker compose up). No Kubernetes, no multi-tenant auth, no WebRTC, no barge-in.
- Interaction is push-to-talk.

## Stack
Python 3.11+, FastAPI, asyncio, Pydantic v2, SQLAlchemy 2 + Alembic (SQLite by default, PostgreSQL via a docker compose profile), faster-whisper plus a Metal/MLX-based option on the Mac, optional Silero VAD, a local TTS (evaluate), React + TypeScript + Vite as a PWA, AudioWorklet, WebSockets, Docker, pytest, Ruff, mypy, Playwright.

## Package layout
backend/src/bolkhata/{config,api,common,asr,tts,llm,realtime,domains}. Ledger-specific code goes ONLY in backend/src/bolkhata/domains/ledger and frontend/src/apps/ledger. Nothing outside domains/ may import from domains/ledger. Every domain implements the DomainPack interface (schema, prompts, normalizers, entity resolver, actions, read-back templates, eval set) so a new problem statement can be built by adding a pack, not changing the pipeline.

## Money safety
- Amounts are parsed by deterministic code, never computed or decided by the LLM.
- Every amount is read back and explicitly confirmed before it is saved.
- The ledger is append-only. Corrections and undo are new compensating entries.
- Actions use idempotency keys so a retry cannot double-record.

## Engineering rules
1. Plan before coding. For any non-trivial task, write a short plan and wait for approval.
2. Type hints everywhere; mypy strict on new code; Ruff clean.
3. Every external call has a timeout. No unbounded queues. No bare except. No blocking calls inside async code.
4. All config via environment variables validated by Pydantic settings. No secrets in the repo. Provide .env.example.
5. Structured JSON logging with session_id, turn_id, generation_id on every line in a session. Never log raw transcripts, audio, customer names, phone numbers, or secrets at INFO level.
6. Every feature ships with tests. Audio tests use deterministic fixtures in tests/fixtures, never a live microphone.
7. Sessions follow an explicit state machine: IDLE, LISTENING, THINKING, SPEAKING. Illegal transitions are rejected.
8. Every response has a generation_id, so stale output can be dropped later. Build this in now because it is expensive to retrofit.
9. Capture audio with AudioWorklet at 16 kHz mono PCM, and keep playback flushable.
10. Measure before claiming. Performance and accuracy claims need numbers, hardware, dataset, and method recorded in docs/benchmarks.
11. When you make a design decision, add a short ADR in docs/adr/NNNN-title.md (context, decision, alternatives, consequences).
12. Never claim something works unless you ran it. Report exactly what you ran and what the output was. If you could not verify something, say so.
13. Never fabricate recordings, transcripts, user data, quotes, or benchmark numbers.
14. Time-box everything. If a task will take more than its sprint budget, stop, say so, and propose the smallest cut.

## Definition of done for any task
Code + tests passing + lint/type clean + docs updated + ADR if a decision was made + a short summary of what changed and how it was verified.

## Working style
Small commits with clear messages. Ask me when requirements are ambiguous rather than guessing. Point out risks and tradeoffs honestly, including when my idea is a bad one.
```

---

## Part 2: Sprint prompts (the core build)

### Sprint S0: Foundation (15-16 Nov)

```
GOAL
Bootstrap the bolkhata monorepo in one day: tooling, CI, config, and a written definition of success, before any feature code.

TASKS
1. Propose the layout first and wait for approval: backend/src/bolkhata/{config,api,common,asr,tts,llm,realtime,domains}, frontend/, docs/{adr,benchmarks}, tests/{unit,integration,fixtures}, scripts/. Create only folders that have content now.
2. Backend: FastAPI app factory, /health and /ready, Pydantic settings from env, structured JSON logging with session_id/turn_id/generation_id context fields (empty for now), and a redaction filter that strips transcripts, names, phone numbers and secrets from INFO logs (test it).
3. Persistence: SQLAlchemy 2 + Alembic with SQLite by default and PostgreSQL available through a docker compose profile named pg. No Redis.
4. Tooling: pyproject.toml (use uv), Ruff, mypy, pytest, pre-commit with a secret scanner.
5. Frontend: Vite + React + TypeScript, ESLint, one placeholder page calling /health.
6. docker-compose.yml with backend and frontend, healthchecks, and a .env.example. Pin all versions.
7. GitHub Actions: lint, type-check, tests, build.
8. docs/slo.md with a table of metrics and an empty 'target' column. Targets are filled in after the S1 baseline (do not invent numbers now).
9. ADRs: 0001 tooling choices, 0002 hackathon scope and domain-pack isolation.

CONSTRAINTS
No model code yet. No auth.

ACCEPTANCE CRITERIA
- docker compose up gives healthy services; /ready fails when the DB is unavailable (show it).
- CI is green on a fresh clone.
- A new person can follow the README and run it in under 10 minutes.

REPORT BACK
Commands run and their output, plus anything unverified.
```

### Sprint S1: Push-to-talk vertical slice (16-18 Nov)

```
GOAL
Build a crude but working push-to-talk loop: browser mic to ASR to LLM to TTS to browser speaker, with per-stage timings. Quality does not matter yet. Working end to end and measured does.

TASKS
1. Provider interfaces (base.py in each package): ASRProvider (transcribe, stream), TTSProvider (synthesize, stream), LLMProvider (stream_chat, structured output), VADProvider (optional, used for silence trimming). Add a config-driven registry.
2. Research and report FIRST, then implement: the best local ASR options per machine. On the Apple Silicon MacBook, compare faster-whisper on CPU with a Metal/MLX-based option (for example whisper.cpp or MLX-Whisper). On the RTX 3050 Windows laptop, faster-whisper with CUDA. Implement at least two ASR providers so the same audio can run on both machines, and verify each model fits the memory available. Cite where you checked licences and maintenance status.
3. TTS: pick the best locally runnable option for Hindi and English that you can verify, behind TTSProvider. LLM: an optional hosted provider (such as Groq) plus a local fallback, behind LLMProvider.
4. WebSocket /ws/session with a versioned message protocol documented in docs/protocol.md: start_utterance, audio frames (binary), end_utterance, transcript, assistant_text, audio_chunk, error, timings.
5. Minimal session state machine: IDLE, LISTENING, THINKING, SPEAKING. One transition table, illegal transitions rejected and logged, tests for every transition.
6. generation_id: created when a turn enters THINKING and attached to every event and audio chunk.
7. Frontend: AudioWorklet capture (16 kHz mono PCM, with echoCancellation, noiseSuppression, autoGainControl requested), hold-to-talk button, live transcript, flushable playback queue, and a timing readout per turn.
8. Load models once at startup and warm them up. Every external call has a timeout. Every queue is bounded.

ACCEPTANCE CRITERIA
- I can say a Hindi and an English sentence and hear a spoken reply.
- An integration test runs one full turn from a WAV fixture with no microphone.
- docs/benchmarks/slice-baseline.md has measured latency per stage on the MacBook (and on the RTX laptop if available), with exact setup.
- docs/known-issues.md lists honestly what is crude.

REPORT BACK
Baseline numbers and the three biggest problems you saw.
```

### Sprint S2: Hinglish normalization and evaluation harness (18-20 Nov)

```
GOAL
Build the part that decides whether Indian speech can be trusted: deterministic spoken-number and unit parsing, plus a reproducible evaluation harness.

TASKS
1. Spoken number parser (backend/src/bolkhata/domains/common/numbers.py, reusable by every domain): Hindi, English, Hinglish, and Devanagari spellings. Cover 0-100 including the irregular Hindi forms and common spelling variants, sau, hazaar, lakh, crore, and mixed forms like 'teen hazaar paanch sau'. Cover fraction words: dhai (2.5), derh (1.5), sawa (1.25), sadhe (plus 0.5), paune (minus 0.25). Examples that must pass: 'dhai sau' = 250, 'derh hazaar' = 1500, 'sawa sau' = 125, 'sadhe teen sau' = 350, 'paune do sau' = 175.
2. Units and currency: kilo, gram, litre, dozen/darjan, packet, rupaye, rs, paise. Table-driven rules with at least 100 tricky test cases. Ambiguity must be reported, not guessed (return candidates plus a confidence flag).
3. ASR text normalization policy (docs/asr-normalization.md): casing, punctuation, numerals, whitespace, and a script policy for Devanagari vs Roman. Provide a strict mode and a transliteration-tolerant mode. Apply the same normalization to references and hypotheses.
4. Metrics: WER, CER, RTF, processing time, peak memory. Implement WER yourself and cross-check against jiwer in tests.
5. Evaluation dataset tooling: a structure under tests/data/eval/ (audio, reference transcript, metadata: language, speaker, noise level, category). Categories: plain Hindi, English, Hinglish, number-heavy, noisy shop, and correction utterances ('nahi, teen sau nahi, teen sau pachaas'). Write a validation script and a recording and annotation guide for me. Do NOT generate or fabricate recordings or transcripts. I will record them.
6. Benchmark runner: python -m bolkhata.eval run --models a,b --dataset eval-v1 produces JSON and a markdown report with per-category breakdowns, model versions, quantization, hardware, dataset hash, and git commit.
7. Compare at least two ASR configurations, and run the same dataset on both machines when possible.

ACCEPTANCE CRITERIA
- Number parser tests pass, including every example above.
- One command reproduces the benchmark report.
- docs/benchmarks/asr-v0.md reports results with the dataset's limits stated (size, speakers).
- CI runs a tiny regression subset.

REPORT BACK
The results table and the three number or unit patterns that failed most.
```

### Sprint S3: Domain pack framework and ledger extraction (20-22 Nov)

```
GOAL
Create the DomainPack abstraction, then implement the shopkeeper ledger as the first pack. This is the piece that must be reusable when Round 2's problem is revealed.

TASKS
1. Define DomainPack in backend/src/bolkhata/domains/base.py: Pydantic schema for extracted intents and entities, versioned system prompt, normalizers, entity resolver, a list of actions (each with name, argument schema, whether it needs confirmation, and an idempotency key), read-back templates, and an eval set reference. Write the interface doc and ADR before coding.
2. Ledger pack (domains/ledger): intents add_credit_sale (udhaar), payment_received, cash_sale, expense, query_balance, undo_last. Entities: customer, items, quantity and unit, amount, date words (aaj, kal, parso), payment mode.
3. Extraction pipeline, in this order: (a) deterministic rule-based parser for common patterns using the S2 number parser; (b) LLM structured extraction ONLY for what the rules cannot resolve, with JSON-schema validation, bounded retry, and a safe fallback; (c) merge with provenance, so every field records whether it came from rules or the LLM. The LLM never does arithmetic or decides money amounts.
4. Customer resolution: fuzzy matching across Devanagari and Roman spellings, honorifics and suffixes (ji, bhai, uncle, aunty, sahab), and phonetic similarity. Above a threshold, resolve; in a gray zone, return candidates so the UI can ask; below it, propose a new customer. Never silently merge two different customers.
5. Storage: append-only ledger events with an Alembic migration. Undo and corrections are compensating events, never deletions. Actions use idempotency keys so a retried request cannot double-record.
6. API endpoints for the pack: submit utterance text, list entries, list customers, balances.
7. Tests: unit tests for the rules parser, resolver, and idempotency; property tests for the number parser integration; the extraction evaluation on the S2 dataset (field-level accuracy, exact-match on amounts, entity-resolution accuracy, end-to-end task success), reported by category.

CONSTRAINTS
Nothing outside domains/ may import from domains/ledger. The pipeline must work with a different pack by changing config only.

ACCEPTANCE CRITERIA
- Create a second tiny dummy pack in tests to prove the pipeline is domain-agnostic.
- Amount exact-match accuracy is reported honestly on my recorded set.
- docs/benchmarks/extraction-v0.md lists failure examples.

REPORT BACK
Accuracy numbers by category and which fields the LLM had to rescue.
```

### Sprint S4: Trust UX, correction, and failure handling (22-24 Nov)

```
GOAL
Make the ledger safe to use by someone who cannot easily check the screen: read-back, confirmation, voice correction, and graceful degradation.

TASKS
1. Read-back: after extraction, generate a spoken and on-screen confirmation from deterministic templates (not the LLM), so amounts and names are spoken exactly as stored. Example: 'Sharma ji, teen sau pachaas rupaye udhaar. Sahi hai?'. Produce the number words with a number-to-Hindi/English words function and test it.
2. Confirmation grammar: recognize yes/no and stop in Hindi, English, and Hinglish (haan, ji, sahi, theek hai, nahi, galat, ruko, cancel) in both scripts. Anything unclear leads to a re-ask, never a default 'yes'.
3. Voice correction: handle patches to the pending entry ('nahi, teen sau nahi, teen sau pachaas', 'customer Verma ji hai', 'kal ka likho'). Keep a pending-entry object that corrections modify, with a bounded number of correction rounds before falling back to manual edit.
4. Risk thresholds: low ASR confidence, ambiguous numbers, an unresolved customer, or an amount above a configurable limit triggers a stricter confirmation (repeat the amount digit by digit if needed).
5. Undo and 'aaj ka hisaab': undo last entry by voice, and a spoken daily summary generated from stored data by template.
6. Failure handling, each with a defined user-visible behavior and a test: ASR down leads to a typed-input prompt; LLM down leads to the rules-only parser with a notice; TTS down leads to on-screen read-back; DB write failure leads to a local retry queue that preserves idempotency keys; network drop leads to reconnect with the pending entry preserved.
7. Use the session state machine and generation_id so a new utterance cancels a stale pending response.
8. Chaos tests: kill or disable each provider mid-turn and assert the behavior above. Record metrics for correction rate and confirmation rate.

ACCEPTANCE CRITERIA
- No entry is ever saved without an explicit confirmation (prove with a test that tries to bypass it).
- Every failure scenario has an automated test.
- A scripted conversation with a correction passes end to end.

REPORT BACK
How often corrections were needed on my recorded set, and what the confirmation flow cannot handle yet.
```

### Sprint S5: Frontend, offline fallback, and hardware benchmarks (24-25 Nov)

```
GOAL
Ship an interface a shopkeeper could actually use, a credible offline mode, and a hardware benchmark that shows engineering judgement.

TASKS
1. Ledger UI (frontend/src/apps/ledger): a PWA with a very large hold-to-talk button, a ledger list, customer balances, a clear pending-entry confirmation card, a Devanagari/Roman display toggle, a language preference, large type, high contrast, and keyboard accessibility. A collapsible developer panel shows per-turn timings and the models used.
2. Consent screen before the mic is first used, with a plain-language note that raw audio is not stored by default. Add docs/privacy.md.
3. Offline mode: if the hosted LLM or network is unavailable, automatically fall back (circuit breaker with a cooldown) to local ASR plus the rules-only parser plus on-screen read-back. Show a visible 'offline mode' indicator.
4. Optional remote inference node: run the ASR provider as a small HTTP or WebSocket worker on the RTX 3050 Windows laptop over the local network, selectable by config, with health checks and timeouts. Only one heavy service on that machine at a time (8 GB RAM).
5. Hardware benchmark report: same dataset, same normalization, run on (a) MacBook CPU, (b) MacBook Metal/MLX-based option, (c) RTX 3050 CUDA. Report RTF, latency, peak memory, and WER. State which configuration is best for the demo and why.
6. Playwright end-to-end test of a full turn with a fake audio device.

ACCEPTANCE CRITERIA
- Pulling the network cable (or disabling Wi-Fi) mid-session degrades gracefully and the demo path still works.
- The hardware benchmark is reproducible with one command per machine.
- Playwright passes in CI.

REPORT BACK
The benchmark table and the configuration you recommend for the finale.
```

### Sprint S6: Evidence, demo, and freeze (25-26 Nov)

```
GOAL
Turn the working build into a credible, presentable engineering artifact, then freeze it before Round 2 opens.

TASKS
1. README: what it is, a 5-minute quick start, an architecture diagram (Mermaid) including the DomainPack boundary, a sequence diagram of one turn, and links to every benchmark report. Every claim in the README links to evidence.
2. docs/benchmarks index, model cards with measured limitations (for example, amount accuracy on noisy audio), docs/known-issues.md, and docs/licences.md listing licences of every model, dataset, and dependency used.
3. docs/future-work.md: an honest register of every shortcut taken (push-to-talk only, SQLite, no auth, no barge-in) and what would fix each.
4. Demo assets: a 90-second demo script (see the demo flow in Part 0) including a voice correction, a read-back catching a mistake, and one deliberately induced failure with graceful recovery. Add scripts/demo_reset.sh with seed data so the demo is repeatable.
5. A short note on how Wispr Flow was used during the build (with a link to a screen recording if one exists).
6. Release: tag v0.1.0 with a changelog. Make the repo ready to be public (no secrets, no private recordings, licence file present).
7. Feature freeze at the end of 26 Nov: only bug fixes after this point.

ACCEPTANCE CRITERIA
- A fresh clone runs the demo following the README only.
- The demo script runs three times in a row without manual repair.
- No secrets in git history (run the scanner over the full history).

REPORT BACK
What the docs claim that you could not back with evidence (remove those claims).
```

---

## Part 3: Feature prompts

Each assumes the earlier sprints exist. Follow the tiers in Part 0.

### Prompt F1: Vocabulary biasing (Must)

```
GOAL
Improve recognition of this shop's own customer and item names by biasing speech recognition with its vocabulary, and prove the effect with a before/after measurement.

TASKS
1. Add a VocabularyProvider to the ledger pack that returns the shop's top customer names and item names, weighted by recency and frequency, with a hard size cap.
2. Extend ASRProvider.transcribe with an optional vocabulary hint. Implement it per provider where the underlying engine supports a prompt or hotword mechanism. Where an engine does not support it, say so explicitly and rely on step 3.
3. Post-ASR correction: use the fuzzy customer resolver and the item list to correct near-miss tokens, only above a similarity threshold. Record every correction in the entry's provenance.
4. Safety: a switch to disable biasing, a bound on hint size, and tests proving that hints do not cause invented names on audio that contains no names.
5. Measurement on the S2 dataset: run with and without biasing and report name accuracy, amount accuracy, overall WER, and added latency. Also test on utterances containing names NOT in the vocabulary list, which must not get worse.

ACCEPTANCE CRITERIA
- A before/after table with the dataset size stated.
- No regression on utterances without names beyond a stated tolerance.
- docs/benchmarks/biasing-v0.md describes method and limits.

REPORT BACK
The measured gain, and the cases where biasing hurt.
```

### Prompt F2: Balance queries by voice (Must)

```
GOAL
Let the shopkeeper ask questions of the ledger by voice and get a correct spoken and on-screen answer.

TASKS
1. Add query intents to the ledger pack: balance for a customer ('Sharma ji ka kitna baaki hai'), today's udhaar given, today's collections, top debtors ('kisko sabse zyada dena hai'), and last payment date for a customer.
2. Answers come from deterministic database queries. The LLM never does arithmetic and never states a balance.
3. Spoken output uses the read-back template system and the number-to-words function. Also show an on-screen table.
4. Ambiguity: several matching customers lead to a spoken question; an unknown customer gets a clear 'not found'.
5. Privacy: spoken balances can be overheard. Add a quiet mode setting that shows the answer on screen instead of speaking it, and make it the easy default for sensitive queries.
6. Tests on seeded data, plus a query-accuracy evaluation set added to the S2 dataset tooling.

ACCEPTANCE CRITERIA
- Every query type has automated tests, including partial payments and reversed entries.
- Query intent accuracy is reported on my recorded set.

REPORT BACK
Intent accuracy and the query phrasings that were misunderstood.
```

### Prompt F3: Ageing and daily digest (Should)

```
GOAL
Surface who owes what and for how long, and give a spoken end-of-day summary.

TASKS
1. Decide and document in an ADR how payments are allocated against old dues (oldest-first versus a simple net balance), including how reversed entries are handled.
2. Compute ageing buckets (0-7, 8-30, 31-60, 60+ days) from the append-only events, using IST dates and correct month and day boundaries.
3. Voice queries such as 'Verma ji ka kitne din se baaki hai' and 'kaun 30 din se zyada se baaki hai'.
4. A daily digest, 'aaj ka hisaab': total sales, collections, new udhaar, and the top overdue customers, spoken from templates in Hindi and English and shown on screen. An optional closing-time reminder as an in-app prompt (do not promise push notification reliability).
5. Tests on seeded data covering partial payments, corrections, undo, boundary dates, and zero-activity days.

ACCEPTANCE CRITERIA
- Ageing results match a hand-computed spreadsheet for a seeded example (include it in the repo).
- The digest never states a figure that the database does not support.

REPORT BACK
The allocation decision and the edge cases that surprised you.
```

### Prompt F4: WhatsApp reminder drafts (Should)

```
GOAL
Help the shopkeeper send a polite payment reminder, without the app ever sending anything itself.

TASKS
1. Add an optional phone number per customer, entered by the shopkeeper, validated and normalized to +91 format, never required.
2. Generate the reminder from deterministic templates in Hindi, English, and Hinglish with two or three tone levels (gentle, neutral, firm but polite). Amounts and dates come from the database. The LLM is not used to produce amounts, and any optional LLM polish must keep numbers unchanged (verify by test).
3. Produce a prefilled WhatsApp click-to-chat link with the message URL-encoded (including Devanagari). The shopkeeper reviews the text and taps send in WhatsApp. The app never sends automatically.
4. Guardrails: a per-customer 'do not remind' flag (set by voice with 'isko mat bhejo'), a warning when another reminder was drafted within a configurable number of days, and a rule that a message never contains information about other customers.
5. Record only that a reminder was drafted (timestamp, customer id), not the message text.
6. Tests: URL encoding, phone normalization, template correctness, and no cross-customer leakage.

CONSTRAINTS
Add a short note in docs/privacy.md that the shopkeeper is responsible for contacting customers appropriately, and that this feature is only a drafting aid.

ACCEPTANCE CRITERIA
- A draft opens correctly in WhatsApp on my phone with the right text.
- All guardrails have tests.

REPORT BACK
Anything about the link format that behaved differently across devices.
```

### Prompt F5: Explainability panel (Should)

```
GOAL
Make every mistake debuggable by showing exactly how an entry was understood.

TASKS
1. For each turn, store and expose: the raw transcript, the normalized text, any ASR alternatives the provider returns, each extracted field with its provenance (rule, LLM, vocabulary correction, user correction), confidence values, the reason a stricter confirmation was requested, and the timings.
2. UI: a collapsible panel on each ledger entry and each turn, readable by a non-engineer, with a button that exports the turn as redacted JSON.
3. Tests proving that every saved field has complete provenance, and that the redacted export contains no customer names or phone numbers unless explicitly included.
4. Add two annotated screenshots of real mistakes to the README, with the explanation of what the panel revealed.

ACCEPTANCE CRITERIA
- I can take any wrong entry and see which stage caused the error in under a minute.

REPORT BACK
The most common error source the panel revealed.
```

### Prompt F6: Data ownership (Must)

```
GOAL
Give shopkeepers control over their data and make the privacy claims true.

TASKS
1. Exports: a per-customer statement as PDF (verify that Devanagari renders correctly by embedding a suitable font), the full ledger as CSV, and a complete JSON export.
2. Deletion: delete one customer's personal data, and delete everything, with an explicit confirmation step. Write an ADR on how deletion interacts with the append-only ledger design (for example erasing personal fields while keeping the minimum needed for aggregate integrity, or removing records entirely), and implement the decision.
3. Audio: raw audio is not stored by default. If a debug audio capture exists, it is opt-in, short-lived, and automatically expires.
4. Consent record: store when and what the user consented to; show a plain-language in-app notice.
5. Tests: deletion completeness across the database, caches, queues, exports, and logs; PDF generation with Devanagari text; consent flow.
6. docs/privacy.md: data flows, what is stored, retention, and user controls, in plain language. List items I should confirm with a lawyer.

ACCEPTANCE CRITERIA
- After deletion, a search of the whole data directory and logs finds none of the deleted personal data (demonstrate it).
- The statement PDF opens correctly on a phone.

REPORT BACK
The deletion design chosen and its tradeoffs.
```

### Prompt F7: Pilot instrumentation (Must)

```
GOAL
Capture honest, privacy-respecting usage evidence from real pilot users, to support the Round 1 Impact activity.

TASKS
1. A pilot mode, off by default, enabled per device. It records locally: time from button press to confirmed save, number of voice corrections, retries, failure types, offline events, and the language used. It never records audio, customer names, or phone numbers. Participants are identified only by a participant code.
2. A one-tap export of the pilot log as CSV for me to review before sharing anything.
3. A stopwatch template for timing the same transactions in the participant's usual method (notebook or app), so the comparison is like for like.
4. An analysis script producing tables and simple charts. With very small samples, report ranges and individual sessions, not significance tests, and state the sample size in every chart title.
5. A short in-app way to capture a one-line comment from the participant, stored locally.

ACCEPTANCE CRITERIA
- Tests confirm that pilot logs contain no audio, names, or phone numbers.
- I can run a ten-transaction session and produce a summary table in under five minutes.

REPORT BACK
What the analysis cannot conclude with this sample size.
```

### Prompt F8: Second language (Could; only if the Must and Should tiers are complete)

```
GOAL
Add support for [LANGUAGE], used by my pilot users, but only claim it if it is measured.

TASKS
1. First, evaluate the available ASR options for [LANGUAGE] on my own recordings and report the accuracy honestly before building anything. Stop and tell me if quality is too low to support the use case.
2. Introduce a NumberParser interface per language and implement the [LANGUAGE] number words, fractions, units, and currency words, with at least 100 tests.
3. Read-back templates, confirmation words (yes, no, stop), and date words in [LANGUAGE]. Handle that script in the customer-name resolver.
4. UI strings via an i18n layer, and font coverage for the script.
5. Add [LANGUAGE] categories to the evaluation dataset and report accuracy by category.

CONSTRAINTS
Do not describe [LANGUAGE] as supported in the README unless the measured accuracy meets a threshold that I will set after seeing the baseline.

REPORT BACK
The measured accuracy and the failure patterns.
```

### Prompt F9: Local-first sync (Could)

```
GOAL
Let the app keep recording entries on the device while offline, then sync them safely when the network returns.

TASKS
1. Write an ADR first: ordering and conflict policy (device time, server receive time, and a logical clock), why the append-only event design helps, and what can still conflict.
2. Client-side durable event queue (IndexedDB) with idempotency keys on every event.
3. Idempotent sync endpoint with retry, exponential backoff and jitter, and a visible sync status in the UI.
4. Tests with simulated network partitions, duplicate deliveries, and out-of-order delivery.

ACCEPTANCE CRITERIA
- Entries made offline appear exactly once after reconnecting, in a demonstrated test.
- Killing the app mid-sync loses no entries and duplicates none.

REPORT BACK
The conflict cases you could not fully solve.
```

### Prompt F10: Open spoken-amount benchmark (Could)

```
GOAL
Prepare, but do not publish, a small benchmark of spoken Indian amounts with reference values, built only from consented recordings.

TASKS
1. A dataset card: purpose, schema, collection method, speaker coding, languages, noise conditions, limitations, and intended use.
2. A separate, explicit consent form for public release of recordings, distinct from the pilot consent. Voice recordings can identify people, so describe that risk in plain language.
3. Anonymization checks: remove or exclude utterances that contain names or phone numbers, and code speakers without personal identifiers.
4. A packaging script and an evaluation script that scores any ASR provider on amount exact-match.
5. A list of licensing options and questions for legal review.

CONSTRAINTS
Do not upload or release any recording. Releasing is my decision, only with explicit consent for each speaker.

REPORT BACK
The risks you see in releasing the data.
```

---

## Part 4: Round prompts

### Prompt R1: Real-user evidence for Round 1 (start now, in parallel)

```
GOAL
Help me gather real evidence from real users for the Round 1 Idea and Impact activities. You build the tooling and templates. I collect the real data. Never invent quotes, numbers, or users.

TASKS
1. Write a short consent script in Hindi and English for recording a shopkeeper (what is recorded, why, how long it is kept, that they can stop or ask for deletion). Make it plain and respectful.
2. Write an interview guide of 8 or fewer open questions about how they currently keep accounts, what goes wrong, how they feel about speaking to a phone, and which language they use for numbers and names.
3. Design a simple task protocol: the user records 10 standard transactions by voice, and we compare time-to-record and error rate against their usual method (notebook or app). Define exactly what is measured.
4. Create a CSV schema and a log template for sessions (participant code, date, noise level, device, task results, corrections, quotes). No real names in the data files.
5. Write a script that summarizes the CSV into tables and charts.
6. Draft the Round 1 submission outline with clearly marked placeholders: problem, who the user is, what I observed, the solution, why voice is the right interface, how impact will be measured, and what is unproven. I have not seen the actual form fields yet; adapt the outline when the Round 1 forms open.

CONSTRAINTS
All participant data stays local, anonymized, and out of git.

REPORT BACK
The list of what I must collect myself before the draft can be completed.
```

### Prompt R2: Round 2 adaptation (27-29 Nov)

```
CONTEXT
This repo is Bolkhata (tag v0.1.0). Round 2 has a single shared problem statement and about 48 hours. Adjust every time-box below to the real deadline shown on the hackathon dashboard.

PROBLEM STATEMENT
[PASTE THE FULL PROBLEM STATEMENT AND THE ROUND 2 RULES AND JUDGING CRITERIA HERE]

TASKS (plan first, wait for my approval)
1. Restate the problem, the user, the success metric, and the judging criteria in your own words. List assumptions and questions.
2. Decide what the repo already covers and what is new. Map the work onto a new DomainPack (domains/[name]) and name every file you will touch outside domains/ (there should be very few).
3. Propose a time-boxed plan. Suggested split: hours 0-2 planning and schema; 2-20 core build; 20-30 trust UX, failure handling, and evaluation; 30-40 polish and frontend; 40-46 demo, README, submission; remainder as buffer.
4. Build order: schema and eval set first, then deterministic logic, then the LLM only where rules cannot reach, then read-back and correction, then UI.
5. Evidence: produce at least one measured accuracy table and one latency table for this problem, with dataset size stated honestly.
6. Run the checks: tests, lint, types, Playwright, demo script three times. Then freeze.

CONSTRAINTS
Disclose the pre-built code in the submission if the rules allow it. If the rules disallow pre-existing code, stop and tell me before writing anything.
```

### Prompt R3: Finale preparation (2-13 Dec)

```
GOAL
Prepare me for the on-campus finale, where shortlisted teams build and demo live in front of Wispr leadership, AI founders and investors. I do not yet know the finale brief; build readiness, not guesses.

TASKS
1. Create a timed drill: scripts and a checklist to build a brand-new DomainPack from scratch in three hours, from a made-up problem statement I paste in. Record where I lose time and fix those friction points in the repo.
2. Failure plan: a written plan for no Wi-Fi (offline mode), a broken or noisy microphone (typed fallback and a pre-recorded audio demo), a dead model server (provider fallback), and power or laptop problems. Verify each with a rehearsal.
3. Pitch structure for investors, 5 minutes: the problem and the user (with real evidence), the insight, a live demo, measured results, why this is hard, why it matters in India, the roadmap beyond the hackathon, and the ask. Draft speaker notes with placeholders for my real numbers.
4. Likely questions and honest answers: accuracy, privacy, hallucination and money safety, cost per user, languages beyond Hindi, what breaks, competitors, and what I would build next.
5. A one-page technical summary a judge can skim in two minutes.

CONSTRAINTS
No claim in the pitch without evidence in the repo.
```

---

## Part 5: Recurring prompts (use anytime)

### Plan-first wrapper (prepend to any task)

```
Before writing code: restate the goal in your own words, list assumptions, list the files you will touch, propose the plan in numbered steps with risks, and suggest how you will verify each step. Wait for my approval.
```

### Code review

```
Review the changes in [branch or diff] as a skeptical senior engineer on a speech-driven financial-records app. Look for: any path that saves an amount without explicit confirmation, amounts computed or altered by the LLM, race conditions, event-loop blocking, unbounded queues or memory growth, missing timeouts, missing idempotency keys, state machine violations, customer names, phone numbers or transcripts in logs, and missing tests. Rank findings by severity with file and line references. Do not rewrite code; report issues and suggested fixes.
```

### Debugging

```
Problem: [describe symptom, expected vs actual, and how to reproduce].
Do not guess. First, gather evidence: read the relevant code, check logs, and write a minimal reproduction or failing test. List 3 hypotheses ranked by likelihood with a way to confirm each. Then fix the confirmed cause, add a regression test, and explain why the bug happened.
```

### Misrecognized utterance investigation

```
This utterance was understood wrongly: [audio file or transcript, what I said, what the app did].
Trace it through every stage: ASR output, normalization, rule parser, LLM extraction (if used), customer resolution, and read-back. Identify which stage caused the error, explain why, and propose the smallest fix. Add the utterance to the evaluation set (with my approval) and a regression test. Do not change thresholds without showing before/after numbers on the full evaluation set.
```

### Security and privacy audit

```
Audit [module or the whole repo] for: customer personal data (names, phone numbers) leaking into logs, exports, or error messages; incomplete deletion; unvalidated input; injection; unsafe deserialization; secrets in code or history; dependency vulnerabilities; and any place raw audio is stored without opt-in. Provide findings with severity, a proof-of-concept test where possible, and fixes.
```

### Benchmark report writer

```
Turn the raw results in [path] into a benchmark report using this structure: purpose, methodology, hardware and software versions, dataset description and limitations, results tables, analysis of failures with examples, threats to validity, and conclusions. Do not state any number that is not in the raw data. Flag anything that looks inconsistent.
```

### ADR writer

```
Write an ADR for the decision we just made about [topic]: context, options considered, decision, consequences (positive and negative), and what would make us revisit it. Keep it under one page.
```

### Refactor safely

```
Refactor [module] to [goal] without changing behavior. First ensure tests cover the current behavior (add characterization tests if missing). Refactor in small commits, run the full test suite after each, and report any behavior you were unsure about.
```

### Agent is going off the rails

```
Stop. Summarize what you have changed so far, what is working, what is failing, and what you are unsure about. Do not make further edits. Propose the smallest next step.
```

---

## Part 6: Final readiness checklist

- [ ] Registered, Wispr Flow installed with the same email, team decision made before the first submission
- [ ] Round 1 rules read; Round 1 submissions sent by 26 Nov
- [ ] Round 2 rules read, including whether pre-existing code and Flow usage are required or verified
- [ ] Number parser tests pass, including dhai, derh, sawa, sadhe, and paune forms
- [ ] Evaluation dataset recorded by me (5+ speakers) and a published report with its limits stated
- [ ] No entry can be saved without explicit confirmation (bypass test passes)
- [ ] Amounts never come from the LLM (verified by test)
- [ ] Every failure scenario has a passing automated test (ASR, LLM, TTS, DB, network)
- [ ] Offline mode works with Wi-Fi off
- [ ] Hardware benchmark table produced on the MacBook (and the RTX laptop if used)
- [ ] Pilot with real shopkeepers completed, with consent and anonymized data
- [ ] Data export and deletion work; deletion proven by search of data and logs
- [ ] Customer names and phone numbers proven absent from INFO logs
- [ ] README links every claim to evidence; known issues listed honestly
- [ ] Demo script runs three times in a row without repair
- [ ] Tag v0.1.0 created, repo scanned for secrets, licences listed
- [ ] Feature freeze held at the end of 26 Nov

---

## Part 7: Tips for working with the agent and Wispr Flow

- **Keep sessions focused.** If a session gets long and confused, summarize progress into docs/progress.md, start a new session, and point it at that file.
- **Make the agent prove it.** Ask for the exact commands run and their output, and run the key ones yourself.
- **Review audio and number-handling code by hand.** Off-by-one errors in buffers and sample rates, and edge cases in number words, are where agents slip, and tests may not catch them.
- **Do not let it invent data.** Evaluation recordings, benchmark numbers, and user quotes must come from real sources. If it cannot run something, it should say so.
- **Check model facts yourself.** Licences, maintenance status, and Hindi support for ASR and TTS models change; ask the agent to cite where it checked, then verify.
- **Protect your hardware.** Ask for a memory estimate before loading any new model, and watch memory use during runs. Keep one heavy service at a time on the 8 GB RAM laptop.
- **Resist scope creep.** If a sprint slips, cut features, not tests or measurements. A smaller product with real evidence beats a larger one without it.
- **Dictate with Wispr Flow.** Speak prompts, notes, and documentation, read the transcription before sending, and type code identifiers yourself when that is faster. Save a short screen recording as evidence of your process.
- **Rehearse the demo early.** Run the 90-second demo every day from 24 Nov so surprises show up before the finale.
- **Ask when rules are unclear.** Use Discord or wispr.support@scaler.com for anything the page does not state.
