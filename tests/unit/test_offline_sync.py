"""
Unit tests for Feature F9: Local-First Event Synchronization Engine.
Verifies ADR 0008:
- Batch ingestion of offline transactions
- Idempotency deduplication across duplicate deliveries / retries
- Commutative convergence across out-of-order deliveries
- Offline compensation / undo event linking
- Simulated network partitions and multi-event batches
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bolkhata.common.base import Base
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.queries import query_customer_balance
from bolkhata.domains.ledger.sync import (
    SyncBatchRequest,
    SyncEventItem,
    process_sync_batch,
)


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_offline_sync_single_batch(db_session: AsyncSession) -> None:
    """Test standard offline batch ingestion creating new customers and ledger events."""
    event1_key = str(uuid.uuid4())
    event2_key = str(uuid.uuid4())

    batch = SyncBatchRequest(
        client_id="counter-tablet-01",
        events=[
            SyncEventItem(
                idempotency_key=event1_key,
                event_type="add_credit_sale",
                customer_name="Pooja Sharma",
                amount=350.0,
                items=["sugar", "tea"],
                client_timestamp=datetime.now(UTC),
                logical_clock=1,
            ),
            SyncEventItem(
                idempotency_key=event2_key,
                event_type="payment_received",
                customer_name="Pooja Sharma",
                amount=100.0,
                client_timestamp=datetime.now(UTC),
                logical_clock=2,
            ),
        ],
    )

    res = await process_sync_batch(db_session, batch)
    assert res.synced_count == 2
    assert res.duplicate_count == 0
    assert res.failed_count == 0
    assert len(res.events) == 2
    assert res.events[0].status == "COMMITTED"
    assert res.events[1].status == "COMMITTED"

    # Verify balance in database
    bal = await query_customer_balance(db_session, "Pooja Sharma")
    assert bal["balance"] == 250.0  # 350 - 100


@pytest.mark.asyncio
async def test_offline_sync_duplicate_idempotency(db_session: AsyncSession) -> None:
    """Resubmitting the same batch must be 100% idempotent without duplicating balances."""
    key = str(uuid.uuid4())
    batch = SyncBatchRequest(
        client_id="counter-tablet-01",
        events=[
            SyncEventItem(
                idempotency_key=key,
                event_type="add_credit_sale",
                customer_name="Karan Verma",
                amount=500.0,
                client_timestamp=datetime.now(UTC),
                logical_clock=1,
            )
        ],
    )

    # First sync
    res1 = await process_sync_batch(db_session, batch)
    assert res1.synced_count == 1
    assert res1.duplicate_count == 0

    # Second sync (network retry simulation)
    res2 = await process_sync_batch(db_session, batch)
    assert res2.synced_count == 0
    assert res2.duplicate_count == 1
    assert res2.events[0].status == "ALREADY_SYNCED"

    # Balance must remain exactly 500.0, NOT 1000.0
    bal = await query_customer_balance(db_session, "Karan Verma")
    assert bal["balance"] == 500.0


@pytest.mark.asyncio
async def test_offline_sync_commutative_convergence(db_session: AsyncSession) -> None:
    """Out-of-order delivery must converge to the exact same customer balance."""
    # Scenario:
    # 1: Credit 400
    # 2: Credit 200
    # 3: Payment 150
    # Final expected = 450
    key1, key2, key3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

    e1 = SyncEventItem(
        idempotency_key=key1,
        event_type="add_credit_sale",
        customer_name="Manoj Gupta",
        amount=400.0,
        client_timestamp=datetime(2026, 11, 27, 10, 0, tzinfo=UTC),
        logical_clock=1,
    )
    e2 = SyncEventItem(
        idempotency_key=key2,
        event_type="add_credit_sale",
        customer_name="Manoj Gupta",
        amount=200.0,
        client_timestamp=datetime(2026, 11, 27, 10, 5, tzinfo=UTC),
        logical_clock=2,
    )
    e3 = SyncEventItem(
        idempotency_key=key3,
        event_type="payment_received",
        customer_name="Manoj Gupta",
        amount=150.0,
        client_timestamp=datetime(2026, 11, 27, 10, 10, tzinfo=UTC),
        logical_clock=3,
    )

    # Ingest in scrambled order: [e3, e1, e2]
    scrambled_batch = SyncBatchRequest(
        client_id="counter-tablet-01",
        events=[e3, e1, e2],
    )
    res = await process_sync_batch(db_session, scrambled_batch)
    assert res.synced_count == 3

    bal = await query_customer_balance(db_session, "Manoj Gupta")
    assert bal["balance"] == 450.0  # 400 + 200 - 150


@pytest.mark.asyncio
async def test_offline_sync_compensation_undo(db_session: AsyncSession) -> None:
    """Offline undo event should mark target event as compensated."""
    target_key = str(uuid.uuid4())
    undo_key = str(uuid.uuid4())

    batch = SyncBatchRequest(
        client_id="counter-tablet-01",
        events=[
            SyncEventItem(
                idempotency_key=target_key,
                event_type="add_credit_sale",
                customer_name="Anil Kumar",
                amount=600.0,
                client_timestamp=datetime.now(UTC),
                logical_clock=1,
            ),
            SyncEventItem(
                idempotency_key=undo_key,
                event_type="compensation_undo",
                customer_name="Anil Kumar",
                amount=600.0,
                target_idempotency_key=target_key,
                client_timestamp=datetime.now(UTC),
                logical_clock=2,
            ),
        ],
    )

    res = await process_sync_batch(db_session, batch)
    assert res.synced_count == 2

    # Target event should have is_compensated = True
    ev = await db_session.scalar(
        select(LedgerEvent).where(LedgerEvent.idempotency_key == target_key)
    )
    assert ev is not None
    assert ev.is_compensated is True

    # Customer balance should be 0.0
    bal = await query_customer_balance(db_session, "Anil Kumar")
    assert bal["balance"] == 0.0
