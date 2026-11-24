"""
Unit and integration tests for F2 Spoken Balance & Business Queries.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bolkhata.api.app import create_app
from bolkhata.common.base import Base
from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.parser import parse_ledger_rules
from bolkhata.domains.ledger.queries import (
    query_customer_balance,
    query_last_payment,
    query_today_collection,
    query_today_udhaar,
    query_top_debtors,
)


def test_parse_query_intents() -> None:
    # 1. Customer balance
    i1 = parse_ledger_rules("Sharma ji ka kitna baaki hai")
    assert i1 is not None
    assert i1.name == "query_balance"
    assert i1.customer == "Sharma"

    # 2. Today udhaar
    i2 = parse_ledger_rules("aaj kitna udhaar diya")
    assert i2 is not None
    assert i2.name == "query_today_udhaar"

    # 3. Today collection
    i3 = parse_ledger_rules("aaj kitna jama hua")
    assert i3 is not None
    assert i3.name == "query_today_collection"

    # 4. Top debtors
    i4 = parse_ledger_rules("kisko sabse zyada dena hai")
    assert i4 is not None
    assert i4.name == "query_top_debtors"

    # 5. Last payment
    i5 = parse_ledger_rules("Verma ji ka last payment kab aaya")
    assert i5 is not None
    assert i5.name == "query_last_payment"
    assert i5.customer == "Verma"


@pytest.fixture
async def seeded_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Seed customers
        c1 = Customer(
            id="c1", name="Ramesh Sharma", normalized_name="ramesh sharma", phone="9876543210"
        )
        c2 = Customer(
            id="c2", name="Suresh Verma", normalized_name="suresh verma", phone="9876543211"
        )
        session.add_all([c1, c2])
        await session.commit()

        # Seed events
        # Ramesh: 500 udhaar, 200 payment -> balance 300
        e1 = LedgerEvent(
            id="e1",
            customer_id="c1",
            event_type="add_credit_sale",
            amount=500.0,
            idempotency_key="ik1",
            is_compensated=False,
        )
        e2 = LedgerEvent(
            id="e2",
            customer_id="c1",
            event_type="payment_received",
            amount=200.0,
            idempotency_key="ik2",
            is_compensated=False,
        )
        # Suresh: 1000 udhaar -> balance 1000
        e3 = LedgerEvent(
            id="e3",
            customer_id="c2",
            event_type="add_credit_sale",
            amount=1000.0,
            idempotency_key="ik3",
            is_compensated=False,
        )
        session.add_all([e1, e2, e3])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_query_customer_balance(seeded_session: AsyncSession) -> None:
    res = await query_customer_balance(seeded_session, "Ramesh", quiet_mode=False)
    assert res["status"] == "success"
    assert res["balance"] == 300.0
    assert "teen sau" in res["spoken_text"]
    assert "₹300.00" in res["display_text"]


@pytest.mark.asyncio
async def test_query_customer_balance_quiet_mode(seeded_session: AsyncSession) -> None:
    res = await query_customer_balance(seeded_session, "Ramesh", quiet_mode=True)
    assert res["status"] == "success"
    assert res["spoken_text"] is None
    assert "₹300.00" in res["display_text"]


@pytest.mark.asyncio
async def test_query_customer_not_found(seeded_session: AsyncSession) -> None:
    res = await query_customer_balance(seeded_session, "UnknownPerson", quiet_mode=False)
    assert res["status"] == "not_found"
    assert res["found"] is False


@pytest.mark.asyncio
async def test_query_today_udhaar(seeded_session: AsyncSession) -> None:
    res = await query_today_udhaar(seeded_session)
    assert res["total_amount"] == 1500.0
    assert "hazaar" in res["spoken_text"]
    assert "₹1500.00" in res["display_text"]


@pytest.mark.asyncio
async def test_query_today_collection(seeded_session: AsyncSession) -> None:
    res = await query_today_collection(seeded_session)
    assert res["total_amount"] == 200.0
    assert "do sau" in res["spoken_text"]


@pytest.mark.asyncio
async def test_query_top_debtors(seeded_session: AsyncSession) -> None:
    res = await query_top_debtors(seeded_session, limit=2)
    assert len(res["top_debtors"]) == 2
    # Suresh (1000) > Ramesh (300)
    assert res["top_debtors"][0]["customer_name"] == "Suresh Verma"
    assert res["top_debtors"][0]["balance"] == 1000.0
    assert "Suresh Verma" in res["spoken_text"]


@pytest.mark.asyncio
async def test_query_last_payment(seeded_session: AsyncSession) -> None:
    res = await query_last_payment(seeded_session, "Ramesh")
    assert res["found"] is True
    assert res["has_payment"] is True
    assert res["amount"] == 200.0
    assert "do sau" in res["spoken_text"]


@pytest.mark.asyncio
async def test_query_api_endpoint(seeded_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Test today's collection via API
        resp = await client.post(
            "/api/v1/ledger/query",
            json={"text": "aaj kitna jama hua", "quiet_mode": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query_type"] == "today_collection"
        assert data["total_amount"] == 200.0
        assert "do sau" in data["spoken_text"]
