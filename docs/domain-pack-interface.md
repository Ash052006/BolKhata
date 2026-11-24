# BolKhata DomainPack Interface Specification

## 1. Overview

A `DomainPack` is a self-contained domain module that plugs into the BolKhata real-time conversation and reasoning pipeline. It translates raw speech transcripts into verified business actions while maintaining complete separation between domain business rules and the core voice/ASR/TTS transport.

---

## 2. Core Abstractions (`bolkhata.domains.base`)

Every domain pack defines:

### 2.1 Intent & Entity Schemas
All domain intents inherit from `DomainIntent`:
- `name`: String identifier of the intent (e.g. `add_credit_sale`, `payment_received`, `query_balance`).
- `confidence`: Confidence score in $[0.0, 1.0]$.
- `provenance`: Provenance dictionary mapping each extracted entity field to its extraction source (`"rules"` or `"llm"`).

### 2.2 DomainAction
Represents an actionable mutation or query requested by the user:
- `action_type`: Name of the action.
- `parameters`: Pydantic payload representing verified action arguments.
- `requires_confirmation`: Boolean indicating whether verbal or on-screen confirmation is required before execution.
- `idempotency_key`: Deterministic token preventing duplicate execution during retries.

### 2.3 Read-Back Template
Deterministic verbal and textual template formatting the action for human confirmation:
```python
def format_read_back(action: DomainAction) -> str:
    """Format action into a natural, deterministic confirmation phrase."""
```

### 2.4 EntityResolver Protocol
Protocol defining entity disambiguation against stored entities (e.g. customer name matching):
```python
class EntityResolver(Protocol):
    async def resolve(
        self, query: str, context: ResolutionContext
    ) -> ResolutionResult: ...
```

---

## 3. Pipeline Invariants

1. **Isolation:** Code outside `backend/src/bolkhata/domains/` MUST NOT import anything from `bolkhata.domains.ledger`.
2. **Deterministic Precedence:** All monetary amounts, units, and dates are normalized by deterministic Python grammars. The LLM is restricted to semantic role extraction.
3. **No Silent Merging:** In entity resolution, similarity scores in the gray zone $[0.65, 0.85)$ MUST return candidates and prompt the user rather than guessing.
4. **Append-Only Immutability:** Ledger actions produce immutable event records. Compensating transactions are recorded for cancellations and corrections.
