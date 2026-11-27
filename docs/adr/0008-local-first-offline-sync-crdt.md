# ADR 0008: Local-First Offline Event Synchronization & Append-Only Convergence

- **Status:** Accepted
- **Date:** 2026-11-27
- **Feature:** F9 (Local-First Sync Engine)
- **Author:** BolKhata Core Team

## Context

Kirana retail environments in semi-urban and rural India frequently experience severe cellular connectivity loss or Wi-Fi dropouts during peak evening store hours. When a shopkeeper attempts to record transactions or undo a misheard entry while the counter terminal or mobile device is disconnected:
1. The app must never freeze, reject speech input, or drop transactions.
2. Entries recorded while offline must be durably staged on-device (e.g., IndexedDB on web/PWA or SQLite on mobile).
3. When network connectivity restores, all offline transactions must synchronize automatically to the server without creating duplicates or distorting financial balances.

## Decision

We adopt an **Append-Only Event Synchronization Architecture** governed by commutative event semantics and deterministic idempotency deduplication:

1. **Ordering & Timestamps Policy:**
   - **Client Timestamp (`client_timestamp`):** The exact local UTC time when the shopkeeper verbally confirmed the entry on-device. Used for merchant business dates (`aaj`, `kal`), chronological customer statements, and debt ageing calculations.
   - **Logical Clock (`logical_clock`):** A monotonically increasing 64-bit integer maintained by the local device for each terminal session, providing total causal ordering of events originating from the same device.
   - **Server Timestamp (`server_timestamp`):** Recorded upon physical insertion into the server's database for replication and audit compliance.

2. **Why Append-Only Event Design Makes Sync Conflict-Free:**
   - In traditional CRUD databases, synchronizing offline rows leads to *Update-Write Conflicts* (e.g. device A updates customer balance to ₹400 while server has ₹500).
   - In BolKhata's append-only ledger, balances are pure mathematical projections over an immutable sequence of events:
     $$B(c) = \sum_{e \in E_c, \neg e.\text{is\_compensated}} \text{signed\_amount}(e)$$
   - Because addition is associative and commutative ($A + B = B + A$), events recorded in arbitrary order or across network partitions converge to the **exact same final customer balance** once all events are delivered.

3. **What Can Still Conflict & How We Solve It:**
   - **Duplicate Delivery / Replays:** Caused by mobile HTTP retries. Solved deterministically: every event carries a globally unique `idempotency_key` (UUID v4 + SHA-256 payload digest). The sync endpoint checks `ledger_events.idempotency_key`. Existing keys return `ALREADY_SYNCED` without double-crediting.
   - **Causal Inversion on Undo:** If an `undo_last` event arrives before its target transaction due to network reordering, the sync engine resolves causality via the event's `target_idempotency_key` using a causal barrier: if the target is in the same batch or present in the database, compensation links immediately; if the target is not yet present, the compensation is staged as pending until the target arrives.
   - **Interleaved Customer Creations:** If an offline transaction introduces a new customer name, the server uses the deterministic RapidFuzz resolver. If an existing customer matches above the 0.85 threshold, the event links to the existing ID; otherwise, a new customer record is atomically created within the sync transaction.

## Consequences

### Positive
- Zero data loss during network blackouts.
- Commutative event replay guarantees identical mathematical balances across multiple terminals.
- Idempotent API makes network retries, exponential backoff, and packet duplicates completely benign.

### Negative / Limitations
- Clock skew on client devices (e.g., incorrectly configured system clock) could produce anomalous `client_timestamp` values. Mitigated by bounding client timestamps to $[T_{\text{server}} - 30\text{ days}, T_{\text{server}} + 1\text{ hour}]$.
- Out-of-order undos across disparate batches require causal dependency checks.
