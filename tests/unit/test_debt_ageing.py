"""
Unit tests for Feature F3: FIFO Debt Ageing and Voice Age Queries.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bolkhata.api.app import create_app
from bolkhata.common.base import Base
from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.ageing import (
    calculate_events_fifo_ageing,
    query_customer_debt_age,
    query_overdue_customers,
)
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.parser import parse_ledger_rules


def test_parse_ageing_intents() -> None:
    i1 = parse_ledger_rules("Verma ji ka kitne din se baaki hai")
    assert i1 is not None
    assert i1.name == "query_debt_age"
    assert i1.customer == "Verma"

    i2 = parse_ledger_rules("kaun 30 din se zyada se baaki hai")
    assert i2 is not None
    assert i2.name == "query_overdue_list"

    i3 = parse_ledger_rules("purana udhaar kiska hai")
    assert i3 is not None
    assert i3.name == "query_overdue_list"


def test_fifo_ageing_vector_matches_csv() -> None:
    """
    Verify exact match with docs/benchmarks/ageing-example.csv:
    - 2026-08-01: +500
    - 2026-09-15: +300
    - 2026-10-10: -600 (payment) -> clears Aug 1 (500) and 100 of Sep 15. Sep 15 remaining: 200
    - 2026-11-01: +400
    - 2026-11-25: +150
    Ref date: 2026-11-27
    Expected:
    0-7 days (Nov 25): 150.00
    8-30 days (Nov 01): 400.00
    31-60 days: 0.00
    60+ days (Sep 15): 200.00
    Total = 750.00
    """
    ref_date = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)

    e1 = LedgerEvent(
        id="1",
        customer_id="c1",
        event_type="add_credit_sale",
        amount=500.0,
        idempotency_key="k1",
        is_compensated=False,
        created_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
    )
    e2 = LedgerEvent(
        id="2",
        customer_id="c1",
        event_type="add_credit_sale",
        amount=300.0,
        idempotency_key="k2",
        is_compensated=False,
        created_at=datetime(2026, 9, 15, 10, 0, tzinfo=UTC),
    )
    e3 = LedgerEvent(
        id="3",
        customer_id="c1",
        event_type="payment_received",
        amount=600.0,
        idempotency_key="k3",
        is_compensated=False,
        created_at=datetime(2026, 10, 10, 10, 0, tzinfo=UTC),
    )
    e4 = LedgerEvent(
        id="4",
        customer_id="c1",
        event_type="add_credit_sale",
        amount=400.0,
        idempotency_key="k4",
        is_compensated=False,
        created_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
    )
    e5 = LedgerEvent(
        id="5",
        customer_id="c1",
        event_type="add_credit_sale",
        amount=150.0,
        idempotency_key="k5",
        is_compensated=False,
        created_at=datetime(2026, 11, 25, 10, 0, tzinfo=UTC),
    )

    ageing = calculate_events_fifo_ageing([e1, e2, e3, e4, e5], "c1", "Ramesh", ref_date)

    assert ageing.total_balance == 750.0
    assert ageing.bucket_0_7 == 150.0
    assert ageing.bucket_8_30 == 400.0
    assert ageing.bucket_31_60 == 0.0
    assert ageing.bucket_60_plus == 200.0
    assert ageing.oldest_due_days == 73  # days from Sep 15 to Nov 27


@pytest.fixture
async def seeded_ageing_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_factory() as session:
        c1 = Customer(id="c1", name="Ramesh Verma", normalized_name="ramesh verma")
        c2 = Customer(id="c2", name="Suresh Gupta", normalized_name="suresh gupta")
        session.add_all([c1, c2])
        await session.commit()

        # Ramesh has 45-day-old credit of 500
        e1 = LedgerEvent(
            id="e1",
            customer_id="c1",
            event_type="add_credit_sale",
            amount=500.0,
            idempotency_key="k1",
            is_compensated=False,
            created_at=now - timedelta(days=45),
        )
        # Suresh has 3-day-old credit of 200
        e2 = LedgerEvent(
            id="e2",
            customer_id="c2",
            event_type="add_credit_sale",
            amount=200.0,
            idempotency_key="k2",
            is_compensated=False,
            created_at=now - timedelta(days=3),
        )
        session.add_all([e1, e2])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_query_customer_debt_age(seeded_ageing_session: AsyncSession) -> None:
    res = await query_customer_debt_age(seeded_ageing_session, "Verma")
    assert res["found"] is True
    assert res["balance"] == 500.0
    assert res["oldest_days"] >= 44
    assert res["buckets"]["31_60"] == 500.0
    assert "₹500.00 baaki hai" in res["display_text"]


@pytest.mark.asyncio
async def test_query_overdue_customers(seeded_ageing_session: AsyncSession) -> None:
    res = await query_overdue_customers(seeded_ageing_session, min_days=30)
    assert res["count"] == 1
    assert res["customers"][0]["customer_name"] == "Ramesh Verma"
    assert "Ramesh Verma" in res["spoken_text"]


@pytest.mark.asyncio
async def test_ageing_api_endpoint(seeded_ageing_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_ageing_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ledger/ageing")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        verma = next(d for d in data if "Verma" in d["customer_name"])
        assert verma["bucket_31_60"] == 500.0
        assert verma["total_balance"] == 500.0
