"""
Unit and integration tests for F6 Data Ownership, Export, and Privacy Deletion.
"""

from __future__ import annotations

import csv
import io

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bolkhata.api.app import create_app
from bolkhata.common.base import Base
from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent


@pytest.fixture
async def seeded_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        c1 = Customer(
            id="cust-123",
            name="Ramesh Gupta",
            normalized_name="ramesh gupta",
            phone="+919876543210",
        )
        session.add(c1)
        await session.commit()

        e1 = LedgerEvent(
            id="ev-001",
            customer_id="cust-123",
            event_type="add_credit_sale",
            amount=450.0,
            items=["chawal", "cheeni"],
            notes="Morning purchase by Ramesh",
            idempotency_key="idemp-001",
            is_compensated=False,
        )
        e2 = LedgerEvent(
            id="ev-002",
            customer_id="cust-123",
            event_type="payment_received",
            amount=200.0,
            notes="Partial payment",
            idempotency_key="idemp-002",
            is_compensated=False,
        )
        session.add_all([e1, e2])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_export_ledger_csv(seeded_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ledger/export/csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert 'attachment; filename="bolkhata_ledger.csv"' in resp.headers["content-disposition"]

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 events
        assert rows[0] == [
            "Event ID",
            "Date",
            "Event Type",
            "Customer Name",
            "Amount (INR)",
            "Items",
            "Notes",
            "Is Compensated",
            "Idempotency Key",
        ]
        assert "Ramesh Gupta" in rows[1]
        assert "450.00" in rows[1]


@pytest.mark.asyncio
async def test_export_ledger_json(seeded_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ledger/export/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "1.0"
        assert len(data["customers"]) == 1
        assert data["customers"][0]["name"] == "Ramesh Gupta"
        assert len(data["events"]) == 2
        assert data["events"][0]["amount"] == 450.0


@pytest.mark.asyncio
async def test_customer_statement(seeded_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ledger/customers/cust-123/statement")
        assert resp.status_code == 200
        data = resp.json()
        assert "Ramesh Gupta" in data["statement_title"]
        assert data["total_outstanding_balance"] == 250.0  # 450 - 200
        assert len(data["transactions"]) == 2
        assert data["transactions"][0]["running_balance"] == 450.0
        assert data["transactions"][1]["running_balance"] == 250.0


@pytest.mark.asyncio
async def test_delete_customer_pii_anonymization(seeded_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Delete customer
        del_resp = await client.delete("/api/v1/ledger/customers/cust-123")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "anonymized"

        # Verify in DB: No PII remains
        cust_q = await seeded_session.execute(select(Customer).where(Customer.id == "cust-123"))
        cust = cust_q.scalar_one()
        assert cust.name == "Deleted Customer"
        assert cust.phone is None
        assert "ramesh" not in cust.normalized_name

        # Verify associated event notes were scrubbed
        evt_q = await seeded_session.execute(
            select(LedgerEvent).where(LedgerEvent.customer_id == "cust-123")
        )
        events = evt_q.scalars().all()
        for ev in events:
            assert "Ramesh" not in (ev.notes or "")
            assert ev.notes == "[Customer PII erased per DPDP Act]"


@pytest.mark.asyncio
async def test_wipe_all_data_requires_confirm(seeded_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without confirm -> 400 Bad Request
        resp1 = await client.delete("/api/v1/ledger/data")
        assert resp1.status_code == 400

        # With confirm=true -> 200 OK
        resp2 = await client.delete("/api/v1/ledger/data?confirm=true")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "wiped"

        # Check DB is empty
        c_count = await seeded_session.execute(select(Customer))
        assert len(c_count.scalars().all()) == 0
        e_count = await seeded_session.execute(select(LedgerEvent))
        assert len(e_count.scalars().all()) == 0
