# BolKhata Data Protection & Privacy Policy

> **Commitment:** BolKhata is built for Indian retail shopkeepers (Kirana merchants). Data privacy and customer trust are non-negotiable core invariants of our architecture.

---

## 1. Executive Summary

BolKhata complies with India's **Digital Personal Data Protection (DPDP) Act, 2023** and adheres to strict local-first data protection principles:
1. **Zero Raw Audio Retention**: Spoken audio is never permanently stored on disk, logged, or uploaded to external third-party servers.
2. **Ephemeral In-Memory Processing**: Audio bytes exist strictly in volatile memory during the active push-to-talk turn and are immediately purged.
3. **Fail-Closed PII Log Scrubbing**: Customer names, Indian phone numbers (`\b[6-9]\d{9}\b`), bearer tokens, and credentials are automatically redacted across all log levels.
4. **Complete Merchant Ownership**: All ledger data resides in the shopkeeper's local database (SQLite/PostgreSQL) with zero vendor lock-in and complete offline data portability.

---

## 2. Audio Processing & Microphone Consent

### 2.1 Explicit Microphone Consent
Before the browser microphone is activated for the first time, BolKhata presents an accessible, plain-language consent dialog:
- **Hindi (Devanagari):** *"बोलखाता आपकी आवाज़ को केवल लेन-देन समझने के लिए इस्तेमाल करता है। आपका ऑडियो कभी भी स्थायी रूप से स्टोर या किसी बाहरी सर्वर पर नहीं भेजा जाता। क्या आप माइक्रोफ़ोन चालू करना चाहते हैं?"*
- **English:** *"BolKhata strictly protects your privacy: Your voice is processed solely to extract ledger entries. Raw audio is never permanently stored or shared with external parties."*

Consent is required before audio worklets capture microphone input, and preference is stored locally on the device.

### 2.2 Ephemeral In-Memory Lifecycle
```
Microphone Capture (AudioWorklet)
          │
          ▼ 16kHz 16-bit Mono PCM
Volatile Stream Buffer (backend/src/bolkhata/realtime/session.py)
          │
          ▼ Automatic Speech Recognition (MLX-Whisper on Apple Silicon)
Text Transcription Produced
          │
          ▼ IMMEDIATELY PURGED FROM MEMORY
Audio Buffer Cleared (0 bytes remaining on disk or RAM)
```

If a user cancels a turn or interrupts playback, all buffers are flushed instantaneously.

---

## 3. PII Redaction & Log Security (DEC-0006)

To prevent customer data leakage into developer tools or log aggregators:
- All logs use `StructuredJsonFormatter` (`bolkhata.common.logging`).
- Customer names (`customer_name`, `customer`), phone numbers, tokens, and passwords are recursively scrubbed across log payloads and exception tracebacks.
- Indian mobile phone number patterns (`\b[6-9]\d{9}\b`) are replaced with `[REDACTED_PHONE]`.
- If serialization or redaction encounters an unexpected error, the formatter **fails closed**, emitting a safe sentinel rather than leaking raw data.

---

## 4. Financial Ledger Immutability & Audit Safety

- **No Destructive Deletions**: Financial records are append-only. Undo actions create compensating offset transactions (`compensation_undo`), guaranteeing complete auditability.
- **Idempotency Protection**: Every transaction carries a SHA-256 idempotency key (`hash(customer_id, action_type, amount, date, client_turn_id)`). Network retries return existing transactions without double-posting.
- **Local Database Ownership**: The ledger is stored on the merchant's machine. The merchant can backup, inspect, or export their data at any time without external dependency.

---

## 5. WhatsApp Payment Reminders & Drafting Aid Disclaimer (Feature F4)

- **Merchant Responsibility & Drafting Aid**: The WhatsApp reminder feature is strictly an interactive drafting aid. BolKhata **never** sends messages or communicates with customers automatically. All generated reminder links (`https://wa.me/...`) require the shopkeeper to review the pre-filled text and manually press send inside their own WhatsApp application. The merchant is solely responsible for ensuring communication complies with local norms and regulations.
- **Privacy-First Audit Logging**: When a reminder is drafted, BolKhata records only minimal audit metadata (`timestamp`, `customer_id`, `tone`) in `reminder_audits`. The message text itself is **never stored** in the database or logs.
- **Opt-Out Respect (`do_not_remind`)**: If a customer requests not to receive reminders (*"isko mat bhejo"*), the `do_not_remind` flag is set on their record, permanently preventing future reminder generation for that customer.

---

## 6. Contact & Questions

For privacy audits, compliance questions, or technical security reports, refer to `docs/interview-guide.md` or contact the repository maintainers.
