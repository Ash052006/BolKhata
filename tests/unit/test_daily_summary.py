"""
Unit tests for 'Aaj ka hisaab' daily summary generation from append-only ledger events.
"""

from __future__ import annotations

import uuid

from bolkhata.domains.ledger.db_models import LedgerEvent
from bolkhata.domains.ledger.trust import generate_daily_summary


def test_daily_summary_aggregation() -> None:
    events = [
        LedgerEvent(
            id=str(uuid.uuid4()),
            event_type="add_credit_sale",
            amount=500.0,
            idempotency_key="k1",
            is_compensated=False,
        ),
        LedgerEvent(
            id=str(uuid.uuid4()),
            event_type="cash_sale",
            amount=1200.0,
            idempotency_key="k2",
            is_compensated=False,
        ),
        LedgerEvent(
            id=str(uuid.uuid4()),
            event_type="payment_received",
            amount=300.0,
            idempotency_key="k3",
            is_compensated=False,
        ),
        LedgerEvent(
            id=str(uuid.uuid4()),
            event_type="expense",
            amount=150.0,
            idempotency_key="k4",
            is_compensated=False,
        ),
        # Compensated event (must be excluded from summary)
        LedgerEvent(
            id=str(uuid.uuid4()),
            event_type="add_credit_sale",
            amount=1000.0,
            idempotency_key="k5",
            is_compensated=True,
        ),
    ]

    summary = generate_daily_summary(events, devanagari=False)
    assert summary["transaction_count"] == 5
    assert summary["total_credit"] == 500.0
    assert summary["total_cash_sales"] == 1200.0
    assert summary["total_payments_received"] == 300.0
    assert summary["total_expenses"] == 150.0
    assert "panch sau rupaye" in summary["spoken_summary"]
    assert "ek hazaar do sau rupaye" in summary["spoken_summary"]

    # Devanagari test
    summary_dev = generate_daily_summary(events, devanagari=True)
    assert "पाँच सौ" in summary_dev["spoken_summary"] or "पांच सौ" in summary_dev["spoken_summary"]
