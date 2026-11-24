# 4. DomainPack Framework and Ledger Extraction Architecture

Date: 2026-11-20
Status: Accepted

## Context

BolKhata is designed as an extensible voice-first platform for Indian commerce. While the primary production vertical in Round 1 is the Kirana Shopkeeper Ledger (`domains/ledger`), the core speech-and-reasoning engine must remain domain-agnostic. In subsequent rounds or adjacent domains (e.g., pharmacy prescription logging, distributor orders, or agricultural mandi transactions), the system must support new domain verticals by configuring a new domain pack without modifying the core pipeline.

Furthermore, within financial ledger operations:
1. **Financial Precision:** Large Language Models (LLMs) are probabilistic and cannot be trusted to perform arithmetic or extract numerical amounts reliably from spoken Indian expressions (*dhai sau*, *paune do sau*).
2. **Entity Ambiguity:** Customer names in Indian retail feature widespread phonetic variations, Roman vs. Devanagari spellings, and cultural honorifics (*ji*, *bhai*, *uncle*, *sahab*). Merging two different customers silently is catastrophic.
3. **Auditability & Double-Posting:** Retried voice commands or spotty connectivity must never create duplicate ledger entries. Deletions must not erase audit history.

## Decision

1. **DomainPack Protocol (`bolkhata.domains.base`):**
   - Define an abstract `DomainPack` specification encapsulating:
     - `intents`: Typed Pydantic models for extracted intents and entities.
     - `system_prompt`: Versioned extraction prompt used by the LLM stage.
     - `actions`: Declared executable actions, each specifying schema, confirmation requirements, and idempotency key generator.
     - `read_back`: Deterministic verbal templates mapping confirmed actions to spoken and visual text.
     - `entity_resolver`: Pluggable resolver protocol for customer/entity resolution.
   - Enforce the architectural invariant: **Nothing outside `domains/` may import from `domains/ledger`**.

2. **Hierarchical Extraction Pipeline (Rules-First, LLM-Assisted, Deterministic Provenance):**
   - The extraction pipeline runs in strict sequence:
     1. **Deterministic Rule Parser:** Uses the Sprint S2 spoken number parser and unit normalizer to extract exact amounts, units, dates, and common keywords (`udhaar`, `jama`, `kharcha`, `baaki`).
     2. **LLM Extraction Fallback:** Invoked *only* for unstructured context or complex syntax that rules cannot resolve. The LLM output is strictly JSON-schema validated with bounded retries.
     3. **Field Provenance Merging:** Every extracted field tracks its provenance (`"rules"` or `"llm"`).
     4. **Money Safety Invariant:** Numerical amounts and currencies are *never* computed or decided by the LLM. If the LLM identifies an amount phrase, it is parsed through the deterministic Python grammar.

3. **Customer Resolution with Explicit Gray-Zone Reporting:**
   - Implements normalized phonetic similarity, honorific stripping, and cross-script transliteration matching.
   - Thresholds:
     - $\ge 0.85$: Resolved automatically.
     - $0.65 \le \text{score} < 0.85$: Gray zone $\rightarrow$ returns candidates with `is_ambiguous=True` for shopkeeper confirmation.
     - $< 0.65$: Unrecognized $\rightarrow$ proposes creating a new customer.
   - **Invariant:** Never silently merge two distinct customers.

4. **Append-Only Event Store with Idempotency:**
   - Ledger storage is strictly append-only.
   - Actions provide deterministic idempotency keys (`idempotency_key = hash(customer_id, action_type, amount, date, client_turn_id)`).
   - Reversals and edits are recorded as explicit compensating events (`compensation_undo`), never hard deletions or in-place mutations.

## Consequences

- The voice pipeline can plug in any new business domain (demonstrated via a hermetic `DummyTaskPack` in tests).
- Financial ledger entries are 100% mathematically deterministic and auditable.
- Double-posting during client retries is physically prevented at the database unique constraint level.
