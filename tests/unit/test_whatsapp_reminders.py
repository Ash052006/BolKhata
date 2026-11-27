"""
Unit tests for Feature F4: WhatsApp Payment Reminder Drafts & Guardrails.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bolkhata.api.app import create_app
from bolkhata.common.base import Base
from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.parser import parse_ledger_rules
from bolkhata.domains.ledger.reminders import (
    draft_customer_reminder,
    generate_reminder_text,
    generate_whatsapp_url,
    normalize_phone_number,
)


def test_phone_number_normalization() -> None:
    # Bare 10 digits starting with 6-9
    assert normalize_phone_number("9876543210") == "+919876543210"
    # With 0 prefix
    assert normalize_phone_number("09876543210") == "+919876543210"
    # With 91 prefix
    assert normalize_phone_number("919876543210") == "+919876543210"
    # With +91 prefix
    assert normalize_phone_number("+919876543210") == "+919876543210"
    # With spaces and hyphens
    assert normalize_phone_number("+91 98765-43210") == "+919876543210"
    # Invalid numbers
    assert normalize_phone_number("12345") is None
    assert normalize_phone_number("5555555555") is None  # Doesn't start with 6-9
    assert normalize_phone_number(None) is None


def test_reminder_template_generation() -> None:
    # Hindi gentle
    t1 = generate_reminder_text("Ramesh", 350.0, tone="gentle", language="hi")
    assert "Ramesh ji" in t1
    assert "₹350.00" in t1
    assert "Suvidhanusar" in t1

    # Hindi firm
    t2 = generate_reminder_text("Ramesh", 350.0, tone="firm", language="hi", days_overdue=45)
    assert "45 din" in t2
    assert "aaj hi jama karein" in t2

    # English neutral
    t3 = generate_reminder_text("Ramesh", 350.0, tone="neutral", language="en")
    assert "Hello Ramesh" in t3
    assert "₹350.00" in t3


def test_whatsapp_url_encoding() -> None:
    url = generate_whatsapp_url("+919876543210", "Namaste Ramesh ji, ₹350.00 baaki hai")
    assert url.startswith("https://wa.me/919876543210?text=")
    assert "%E2%82%B9350.00" in url or "%20" in url


def test_parse_do_not_remind_intent() -> None:
    i1 = parse_ledger_rules("Sharma ji ko isko mat bhejo")
    assert i1 is not None
    assert i1.name == "set_do_not_remind"
    assert i1.customer == "Sharma"

    i2 = parse_ledger_rules("remind mat karna Verma ko")
    assert i2 is not None
    assert i2.name == "set_do_not_remind"


@pytest.fixture
async def seeded_reminder_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_factory() as session:
        # Customer 1: Normal with balance
        c1 = Customer(
            id="c1",
            name="Ramesh Sharma",
            normalized_name="ramesh sharma",
            phone="9876543210",
            do_not_remind=False,
        )
        # Customer 2: Opted out of reminders
        c2 = Customer(
            id="c2",
            name="Suresh Verma",
            normalized_name="suresh verma",
            phone="9876543211",
            do_not_remind=True,
        )
        # Customer 3: No balance
        c3 = Customer(
            id="c3",
            name="Sunita Gupta",
            normalized_name="sunita gupta",
            phone="9876543212",
            do_not_remind=False,
        )
        session.add_all([c1, c2, c3])
        await session.commit()

        # Add debt for c1 and c2
        e1 = LedgerEvent(
            id="e1",
            customer_id="c1",
            event_type="add_credit_sale",
            amount=500.0,
            idempotency_key="k1",
            is_compensated=False,
            created_at=now - timedelta(days=20),
        )
        e2 = LedgerEvent(
            id="e2",
            customer_id="c2",
            event_type="add_credit_sale",
            amount=300.0,
            idempotency_key="k2",
            is_compensated=False,
            created_at=now - timedelta(days=10),
        )
        session.add_all([e1, e2])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_draft_reminder_success(seeded_reminder_session: AsyncSession) -> None:
    res = await draft_customer_reminder(seeded_reminder_session, "c1", tone="gentle")
    assert res["status"] == "success"
    assert res["balance"] == 500.0
    assert "https://wa.me/919876543210?text=" in res["whatsapp_url"]
    assert res["recent_reminder_warning"] is False


@pytest.mark.asyncio
async def test_draft_reminder_opted_out_guardrail(seeded_reminder_session: AsyncSession) -> None:
    res = await draft_customer_reminder(seeded_reminder_session, "c2")
    assert res["status"] == "blocked"
    assert res["reason"] == "opted_out"
    assert res["whatsapp_url"] is None


@pytest.mark.asyncio
async def test_draft_reminder_zero_balance_guardrail(seeded_reminder_session: AsyncSession) -> None:
    res = await draft_customer_reminder(seeded_reminder_session, "c3")
    assert res["status"] == "blocked"
    assert res["reason"] == "zero_balance"


@pytest.mark.asyncio
async def test_draft_reminder_cooldown_warning(seeded_reminder_session: AsyncSession) -> None:
    # First draft
    res1 = await draft_customer_reminder(seeded_reminder_session, "c1")
    assert res1["status"] == "success"
    assert res1["recent_reminder_warning"] is False

    # Immediate second draft -> cooldown warning triggered
    res2 = await draft_customer_reminder(seeded_reminder_session, "c1")
    assert res2["status"] == "success"
    assert res2["recent_reminder_warning"] is True
    assert "Warning" in res2["warning_note"]


@pytest.mark.asyncio
async def test_reminder_api_endpoints(seeded_reminder_session: AsyncSession) -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: seeded_reminder_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # POST /customers/c1/reminder
        resp = await client.post(
            "/api/v1/ledger/customers/c1/reminder",
            json={"tone": "neutral", "language": "hi"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "wa.me" in data["whatsapp_url"]

        # POST /customers/c1/do-not-remind
        opt_resp = await client.post("/api/v1/ledger/customers/c1/do-not-remind?enabled=true")
        assert opt_resp.status_code == 200
        assert opt_resp.json()["do_not_remind"] is True

        # Now reminder should be blocked
        blocked_resp = await client.post(
            "/api/v1/ledger/customers/c1/reminder",
            json={"tone": "neutral", "language": "hi"},
        )
        assert blocked_resp.status_code == 200
        assert blocked_resp.json()["status"] == "blocked"
