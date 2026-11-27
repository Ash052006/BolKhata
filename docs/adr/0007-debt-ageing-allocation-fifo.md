# ADR 0007: FIFO Payment Allocation for Debt Ageing Analysis

- **Status:** Accepted
- **Date:** November 2026
- **Context:** Feature F3 Debt Ageing & Daily Digest

---

## Context and Problem Statement

Kirana stores extend credit over weeks and months. When a customer makes a partial repayment (e.g. paying ₹500 against three historical purchases of ₹200, ₹400, and ₹300), how should that payment be allocated across historical dues to determine **debt ageing buckets** (0-7 days, 8-30 days, 31-60 days, 60+ days)?

Furthermore, how must compensating reversals (`compensation_undo`) interact with ageing calculations?

---

## Decision Drivers

- **Simplicity & Predictability:** The allocation rule must match standard Indian retail conventions.
- **Auditability:** Every rupee owed must be attributable to a specific historical transaction date.
- **Append-Only Immutability:** Calculations must run dynamically over the append-only `LedgerEvent` log without requiring mutable pointers.
- **Timezone Precision:** Ageing must use Indian Standard Time (IST, UTC+05:30) calendar day boundaries.

---

## Considered Options

### Option 1: Simple Net Balance with Most-Recent Age
- The net balance is calculated, and its age is set to the date of the most recent credit sale.
- **Flaw:** Masks severely overdue debt. If a customer owes ₹5,000 from 90 days ago and buys a ₹20 biscuit packet today, their entire debt would look 0 days old.

### Option 2: First-In, First-Out (FIFO) Payment Allocation (Chosen)
- Payments received are applied chronologically against the **oldest outstanding credit sales**.
- When an undo (`compensation_undo`) occurs, it reverses the exact target event it references (`compensated_event_id`).
- Any remaining un-allocated credit amounts are assigned to their respective ageing buckets:
  - **Current:** 0–7 days
  - **Due:** 8–30 days
  - **Overdue:** 31–60 days
  - **Critical:** 60+ days
- **Benefits:** Exactly reflects commercial reality. Old debt remains flagged until fully liquidated.

---

## Consequences

- **Positive:** Clear, mathematically defensible debt ageing. The shopkeeper immediately knows who has overdue balances from a month ago.
- **Negative:** Requires chronologically traversing uncompensated events for each customer. With hundreds of events per customer, caching or materialized daily summaries can be introduced if needed.
