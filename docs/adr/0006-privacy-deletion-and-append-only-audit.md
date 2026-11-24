# ADR 0006: DPDP Privacy Deletion and Append-Only Financial Audit Integrity

- **Status:** Accepted
- **Date:** November 2026
- **Context:** Sprint S5/S6 & Feature F6 Data Ownership

---

## Context and Problem Statement

BolKhata operates as a voice-first credit ledger for Indian kirana merchants. Under India's Digital Personal Data Protection (DPDP) Act 2023, consumers and customers have the right to request erasure of their personal data (Right to Erasure).

However, accounting standards and tax regulations require financial audit trails to remain mathematically consistent:
1. If a customer transaction (e.g. ₹500 credit sale) is physically deleted from the append-only event store, the merchant's aggregate store sales, cash-in-hand, and historical revenue calculations silently change.
2. Conversely, retaining raw names (*Ramesh Sharma*) and phone numbers (*+91 9876543210*) after an erasure request violates data protection laws.

We must reconcile **data privacy erasure** with **append-only financial audit integrity**.

---

## Decision Drivers

- **Zero PII Retention:** After customer erasure, no personal name, phone number, or voice transcript may remain anywhere in the database or logs.
- **Financial Balance Integrity:** Historical aggregate totals (total sales, total credit issued, total collections) must remain mathematically verifiable.
- **Append-Only Immutability:** Event sequence numbers and cryptographic hashes must not suffer gaps.
- **Accidental Wipe Protection:** Full data wipes must require an explicit, un-bypassable confirmation flag (`confirm=true`).

---

## Considered Options

### Option 1: Hard Cascading Deletion
- Physical SQL `DELETE FROM customers WHERE id = ? CASCADE`.
- **Drawback:** Deletes historical `LedgerEvent` rows. Aggregate monthly/annual store revenue collapses; auditability is permanently lost.

### Option 2: Pseudonymization & PII Scrubbing (Chosen for Customer Erasure)
- The customer's identity is scrubbed:
  - `Customer.name` $\rightarrow$ `"Deleted Customer"`
  - `Customer.normalized_name` $\rightarrow$ `"deleted_<id[:8]>"`
  - `Customer.phone` $\rightarrow$ `None`
- All associated `LedgerEvent.notes` are sanitized to remove customer mentions.
- The `LedgerEvent.customer_id` foreign key remains linked to the pseudonymized record.
- **Benefits:** Financial amounts, transaction counts, and timestamp integrity are 100% preserved. Zero PII remains. Fully satisfies DPDP Act Right to Erasure.

### Option 3: Full Store Wipe with Explicit Confirmation (Chosen for Complete Reset)
- For store closing or complete tenant wipe (`DELETE /api/v1/ledger/data?confirm=true`):
  - Requires explicit boolean flag `confirm=true`.
  - Atomically truncates/deletes all customers and ledger events.
  - Returns a cryptographic erasure receipt.

---

## Consequences

- **Positive:** Full compliance with DPDP Act 2023. Financial totals remain immutable.
- **Negative:** Once pseudonymized, a customer's individual account cannot be restored.
- **Auditing:** Searching the database after customer erasure yields zero instances of the customer's name or phone number.
