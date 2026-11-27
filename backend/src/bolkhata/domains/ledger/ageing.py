"""
Debt ageing calculation engine using First-In-First-Out (FIFO) payment allocation.

Implements Feature F3 (Prompt F3) and ADR 0007:
- FIFO allocation of repayments against historical credit sales.
- IST calendar day boundaries.
- Ageing buckets: 0-7 days (Current), 8-30 days (Due), 31-60 days (Overdue), 60+ days (Critical).
- Spoken responses and voice query handlers for overdue credit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bolkhata.domains.common.number_words import number_to_hindi_words
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.resolver import CustomerRecord, CustomerResolver

# Indian Standard Time (UTC+05:30)
IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class CustomerAgeing:
    customer_id: str
    customer_name: str
    total_balance: float
    bucket_0_7: float
    bucket_8_30: float
    bucket_31_60: float
    bucket_60_plus: float
    oldest_due_days: int


def calculate_events_fifo_ageing(
    events: list[LedgerEvent],
    customer_id: str,
    customer_name: str,
    ref_date: datetime | None = None,
) -> CustomerAgeing:
    """
    Perform FIFO debt allocation on uncompensated events for a single customer.
    """
    if ref_date is None:
        ref_date = datetime.now(IST)
    elif ref_date.tzinfo is None:
        ref_date = ref_date.replace(tzinfo=UTC).astimezone(IST)
    else:
        ref_date = ref_date.astimezone(IST)

    # Filter compensated events
    active_events = [e for e in events if not e.is_compensated]

    # Chronological sort
    active_events.sort(key=lambda x: x.created_at)

    # Track credit obligations: [(amount, created_at_ist)]
    credits: list[list[Any]] = []
    total_payments = 0.0

    for ev in active_events:
        dt = ev.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC).astimezone(IST)
        else:
            dt = dt.astimezone(IST)

        if ev.event_type in ("add_credit_sale", "credit_sale"):
            credits.append([ev.amount, dt])
        elif ev.event_type == "payment_received":
            total_payments += ev.amount
        elif ev.event_type == "compensation_undo":
            # If undo was recorded as negative credit
            if ev.amount < 0:
                total_payments += abs(ev.amount)
            else:
                credits.append([ev.amount, dt])

    # Apply total payments against oldest credits first (FIFO)
    rem_payment = total_payments
    for cred in credits:
        if rem_payment <= 0:
            break
        cred_amt = cred[0]
        if rem_payment >= cred_amt:
            rem_payment -= cred_amt
            cred[0] = 0.0
        else:
            cred[0] -= rem_payment
            rem_payment = 0.0

    # Bucket remaining unpaid credit amounts
    b_0_7 = 0.0
    b_8_30 = 0.0
    b_31_60 = 0.0
    b_60_plus = 0.0
    oldest_days = 0

    for amt, dt in credits:
        if amt <= 0.001:
            continue
        days = max((ref_date.date() - dt.date()).days, 0)
        oldest_days = max(oldest_days, days)

        if days <= 7:
            b_0_7 += amt
        elif days <= 30:
            b_8_30 += amt
        elif days <= 60:
            b_31_60 += amt
        else:
            b_60_plus += amt

    total_due = round(b_0_7 + b_8_30 + b_31_60 + b_60_plus, 2)
    # If customer has net credit advance (payments > credits)
    if not credits and total_payments > 0:
        total_due = -round(total_payments, 2)

    return CustomerAgeing(
        customer_id=customer_id,
        customer_name=customer_name,
        total_balance=total_due,
        bucket_0_7=round(b_0_7, 2),
        bucket_8_30=round(b_8_30, 2),
        bucket_31_60=round(b_31_60, 2),
        bucket_60_plus=round(b_60_plus, 2),
        oldest_due_days=oldest_days,
    )


async def get_all_customers_ageing(
    session: AsyncSession,
    ref_date: datetime | None = None,
) -> list[CustomerAgeing]:
    """Calculate FIFO ageing for every customer in the ledger."""
    cust_q = await session.execute(select(Customer).order_by(Customer.name))
    customers = cust_q.scalars().all()

    results: list[CustomerAgeing] = []
    for c in customers:
        evt_q = await session.execute(select(LedgerEvent).where(LedgerEvent.customer_id == c.id))
        evts = evt_q.scalars().all()
        ageing = calculate_events_fifo_ageing(list(evts), c.id, c.name, ref_date)
        results.append(ageing)

    return results


async def query_customer_debt_age(
    session: AsyncSession,
    customer_name: str,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """Voice query: Verma ji ka kitne din se baaki hai."""
    cust_q = await session.execute(select(Customer))
    db_customers = cust_q.scalars().all()
    records = [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in db_customers]

    resolver = CustomerResolver(records)
    res = await resolver.resolve(customer_name)

    if not res.is_resolved or not res.resolved_id:
        return {
            "query_type": "debt_age",
            "found": False,
            "display_text": f"Customer '{customer_name}' nahi mila.",
            "spoken_text": None if quiet_mode else f"{customer_name} naam ka customer nahi mila.",
            "quiet_mode": quiet_mode,
        }

    target_cust = next(c for c in db_customers if c.id == res.resolved_id)
    evt_q = await session.execute(
        select(LedgerEvent).where(LedgerEvent.customer_id == target_cust.id)
    )
    events = evt_q.scalars().all()

    ageing = calculate_events_fifo_ageing(list(events), target_cust.id, target_cust.name)

    if ageing.total_balance <= 0:
        return {
            "query_type": "debt_age",
            "found": True,
            "customer_name": target_cust.name,
            "balance": ageing.total_balance,
            "oldest_days": 0,
            "display_text": f"{target_cust.name} ka hisaab barabar hai.",
            "spoken_text": None
            if quiet_mode
            else f"{target_cust.name} ka koi udhaar baaki nahi hai.",
            "quiet_mode": quiet_mode,
        }

    days_words = (
        number_to_hindi_words(ageing.oldest_due_days) if ageing.oldest_due_days > 0 else "kuch"
    )
    amt_words = number_to_hindi_words(int(ageing.total_balance))

    display = (
        f"{target_cust.name}: ₹{ageing.total_balance:.2f} baaki hai. "
        f"Sabse purana hisaab {ageing.oldest_due_days} din purana hai."
    )
    spoken = (
        f"{target_cust.name} ka {amt_words} rupaye baaki hai, "
        f"jo lagbhag {days_words} din se chala aa raha hai."
    )

    return {
        "query_type": "debt_age",
        "found": True,
        "customer_id": target_cust.id,
        "customer_name": target_cust.name,
        "balance": ageing.total_balance,
        "oldest_days": ageing.oldest_due_days,
        "buckets": {
            "0_7": ageing.bucket_0_7,
            "8_30": ageing.bucket_8_30,
            "31_60": ageing.bucket_31_60,
            "60_plus": ageing.bucket_60_plus,
        },
        "display_text": display,
        "spoken_text": None if quiet_mode else spoken,
        "quiet_mode": quiet_mode,
    }


async def query_overdue_customers(
    session: AsyncSession,
    min_days: int = 30,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """Voice query: Kaun 30 din se zyada se baaki hai."""
    all_ageing = await get_all_customers_ageing(session)

    overdue = [a for a in all_ageing if a.oldest_due_days >= min_days and a.total_balance > 0]
    overdue.sort(key=lambda x: x.total_balance, reverse=True)

    if not overdue:
        return {
            "query_type": "overdue_list",
            "count": 0,
            "min_days": min_days,
            "customers": [],
            "display_text": f"Koi bhi customer {min_days} din se zyada purana baaki nahi hai.",
            "spoken_text": None
            if quiet_mode
            else f"{min_days} din se zyada kisi ka bhi udhaar nahi hai.",
            "quiet_mode": quiet_mode,
        }

    top_names = [f"{c.customer_name} (₹{c.total_balance:.2f})" for c in overdue[:3]]
    display = f"{len(overdue)} customer {min_days}+ din se baaki hain: {', '.join(top_names)}."
    spoken = (
        f"Kul {len(overdue)} customer hain jinka hisaab {min_days} din se zyada purana hai, "
        f"jaise {overdue[0].customer_name}."
    )

    return {
        "query_type": "overdue_list",
        "count": len(overdue),
        "min_days": min_days,
        "customers": [
            {
                "customer_id": c.customer_id,
                "customer_name": c.customer_name,
                "balance": c.total_balance,
                "oldest_days": c.oldest_due_days,
            }
            for c in overdue
        ],
        "display_text": display,
        "spoken_text": None if quiet_mode else spoken,
        "quiet_mode": quiet_mode,
    }
