"""
Unit tests for Feature F5: Explainability Panel and Redacted Diagnostics.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bolkhata.api.app import create_app
from bolkhata.common.base import Base
from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.explainability import get_entry_explanation


@pytest.fixture
async def seeded_explain_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_factory() as session:
        c1 = Customer(
            id="cust-exp-01",
            name="Ramesh Sharma",
            normalized_name="ramesh sharma",
            phone="9876543210",
        )
        session.add(c1)
        await session.commit()

        e1 = LedgerEvent(
            id="ev-exp-01",
            customer_id="cust-exp-01",
            event_type="add_credit_sale",
            amount=2500.0,
            currency="INR",
            items=["atta", "ghee"],
            date_str="aaj",
            idempotency_key="idemp-exp-01",
            is_compensated=False,
            provenance={
                "intent": "rules",
                "amount": "rules",
                "customer": "rules_vocabulary_bias",
                "raw_transcript": "Ramesh Sharma 9876543210 ko 2500 udhaar",
                "normalized_transcript": "ramesh sharma 9876543210 ko 2500 udhaar",
                "timings_ms": {"asr_ms": 110.0, "extraction_ms": 12.0, "total_ms": 122.0},
            },
            created_at=now,
        )
        session.add(e1)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_entry_explanation(seeded_explain_session: AsyncSession) -> None:
    exp = await get_entry_explanation(seeded_explain_session, "ev-exp-01")
    assert exp.entry_id == "ev-exp-01"
    assert exp.customer_name == "Ramesh Sharma"
    assert exp.amount == 2500.0
    assert exp.provenance["intent"] == "rules"
    assert exp.provenance["customer"] == "rules_vocabulary_bias"
    # Over 2000 INR triggers high-risk stricter confirmation
    assert exp.risk_assessment["is_high_risk"] is True
    assert "amount_above_threshold_2000" in exp.risk_assessment["reasons"]


@pytest.mark.asyncio
async def test_redacted_export_zero_pii(seeded_explain_session: AsyncSession) -> None:
    exp = await get_entry_explanation(seeded_explain_session, "ev-exp-01")
    redacted = exp.to_redacted_dict()

    # Customer name must be completely redacted
    assert redacted["customer_name"] == "[REDACTED_CUSTOMER]"
    assert "Ramesh" not in redacted["raw_transcript"]
    assert "Sharma" not in redacted["raw_transcript"]
    assert "[REDACTED_CUSTOMER]" in redacted["raw_transcript"]

    # Phone number must be completely redacted
    assert "9876543210" not in redacted["raw_transcript"]
    assert "[REDACTED_PHONE]" in redacted["raw_transcript"]

    # ID is pseudonymized
    assert redacted["customer_id"].startswith("anon_")


@pytest.mark.asyncio
async def test_explainability_api_endpoints(seeded_explain_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_explain_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Full explain
        r1 = await client.get("/api/v1/ledger/entries/ev-exp-01/explain")
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["customer_name"] == "Ramesh Sharma"
        assert data1["amount"] == 2500.0

        # Redacted explain
        r2 = await client.get("/api/v1/ledger/entries/ev-exp-01/explain/redacted")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["customer_name"] == "[REDACTED_CUSTOMER]"
        assert "9876543210" not in data2["raw_transcript"]
        assert "[REDACTED_PHONE]" in data2["raw_transcript"]
