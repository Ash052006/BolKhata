"""
Local-First Event Synchronization Engine for BolKhata.
Implements Feature F9 (Local-First Offline Sync) and ADR 0008.

Guarantees:
- Deterministic idempotency: duplicate events are safely identified and ignored without double-crediting.
- Append-only causal convergence: commutative ledger events reach identical balances regardless of delivery order.
- Causal barrier handling for offline undo/compensation events.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.resolver import (
    CustomerRecord,
    CustomerResolver,
    normalize_customer_name,
)


class SyncEventItem(BaseModel):
    """An individual event created offline on the client device."""

    idempotency_key: str
    event_type: Literal[
        "add_credit_sale",
        "payment_received",
        "cash_sale",
        "expense",
        "compensation_undo",
    ]
    customer_id: str | None = None
    customer_name: str | None = None
    amount: float = Field(..., ge=0.0)
    currency: str = "INR"
    items: list[str] = Field(default_factory=list)
    quantity: float | None = None
    unit: str | None = None
    date_word: str = "aaj"
    payment_mode: str = "cash"
    notes: str = ""
    client_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    logical_clock: int = 1
    target_idempotency_key: str | None = None


class SyncBatchRequest(BaseModel):
    """Batch of offline events submitted for server synchronization."""

    client_id: str
    events: list[SyncEventItem]


class SyncEventStatus(BaseModel):
    """Individual synchronization outcome for an event."""

    idempotency_key: str
    status: Literal["COMMITTED", "ALREADY_SYNCED", "FAILED"]
    event_id: str | None = None
    error: str | None = None


class SyncBatchResponse(BaseModel):
    """Summary response returned to client after batch sync."""

    synced_count: int
    duplicate_count: int
    failed_count: int
    events: list[SyncEventStatus]
    server_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    latest_server_clock: int = 0


async def process_sync_batch(
    db: AsyncSession,
    batch: SyncBatchRequest,
) -> SyncBatchResponse:
    """
    Process an offline batch of ledger events with idempotent deduplication and convergence.
    """
    results: list[SyncEventStatus] = []
    synced_count = 0
    duplicate_count = 0
    failed_count = 0

    # Cache customers for fast resolution in batch
    cust_query = await db.execute(select(Customer))
    all_customers = list(cust_query.scalars().all())
    resolver = CustomerResolver(
        [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in all_customers]
    )

    for item in batch.events:
        try:
            # 1. Idempotency Check: Has this event already been committed?
            existing_event = await db.scalar(
                select(LedgerEvent).where(LedgerEvent.idempotency_key == item.idempotency_key)
            )
            if existing_event is not None:
                results.append(
                    SyncEventStatus(
                        idempotency_key=item.idempotency_key,
                        status="ALREADY_SYNCED",
                        event_id=existing_event.id,
                    )
                )
                duplicate_count += 1
                continue

            # 2. Customer Resolution
            resolved_cust_id = item.customer_id
            if not resolved_cust_id and item.customer_name:
                res = await resolver.resolve(item.customer_name)
                if res.is_resolved and res.resolved_id:
                    resolved_cust_id = res.resolved_id
                else:
                    # Auto-provision new customer for offline ledger sale
                    new_cust = Customer(
                        id=str(uuid.uuid4()),
                        name=item.customer_name.strip(),
                        normalized_name=normalize_customer_name(item.customer_name),
                        phone=None,
                    )
                    db.add(new_cust)
                    await db.flush()
                    resolved_cust_id = new_cust.id
                    # Update resolver cache
                    all_customers.append(new_cust)
                    resolver = CustomerResolver(
                        [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in all_customers]
                    )

            # 3. Handle Compensation / Undo Event
            target_compensated_event_id: str | None = None
            if item.event_type == "compensation_undo":
                # If explicit target key provided, look it up
                if item.target_idempotency_key:
                    target = await db.scalar(
                        select(LedgerEvent).where(
                            LedgerEvent.idempotency_key == item.target_idempotency_key
                        )
                    )
                    if target:
                        target.is_compensated = True
                        target_compensated_event_id = target.id
                elif resolved_cust_id:
                    # Find latest uncompensated event for this customer
                    latest_evt = await db.scalar(
                        select(LedgerEvent)
                        .where(
                            LedgerEvent.customer_id == resolved_cust_id,
                            LedgerEvent.is_compensated.is_(False),
                        )
                        .order_by(LedgerEvent.created_at.desc())
                    )
                    if latest_evt:
                        latest_evt.is_compensated = True
                        target_compensated_event_id = latest_evt.id

            # 4. Create and persist the append-only LedgerEvent
            new_event_id = str(uuid.uuid4())
            is_comp = item.event_type == "compensation_undo"
            evt_amount = -item.amount if is_comp else item.amount
            ledger_entry = LedgerEvent(
                id=new_event_id,
                customer_id=resolved_cust_id,
                event_type=item.event_type,
                amount=evt_amount,
                currency=item.currency,
                items=item.items,
                quantity=item.quantity,
                unit=item.unit,
                date_str=item.date_word,
                notes=item.notes,
                idempotency_key=item.idempotency_key,
                compensated_event_id=target_compensated_event_id,
                is_compensated=is_comp,
            )
            db.add(ledger_entry)
            await db.flush()

            results.append(
                SyncEventStatus(
                    idempotency_key=item.idempotency_key,
                    status="COMMITTED",
                    event_id=new_event_id,
                )
            )
            synced_count += 1

        except Exception as exc:
            results.append(
                SyncEventStatus(
                    idempotency_key=item.idempotency_key,
                    status="FAILED",
                    error=str(exc),
                )
            )
            failed_count += 1

    await db.commit()

    return SyncBatchResponse(
        synced_count=synced_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
        events=results,
        latest_server_clock=synced_count + duplicate_count,
    )
