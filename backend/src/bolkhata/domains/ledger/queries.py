"""
Deterministic ledger query engine for voice and screen answers.

Implements Prompt F2:
- Customer balance ("Sharma ji ka kitna baaki hai")
- Today's udhaar given ("aaj kitna udhaar diya")
- Today's collections ("aaj kitna jama hua")
- Top debtors ("kisko sabse zyada dena hai")
- Last payment date ("Sharma ji ne aakhiri baar kab diya")
- Spoken templates using number-to-words generator.
- Quiet mode toggle for overhearing privacy.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bolkhata.domains.common.number_words import number_to_hindi_words
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.resolver import CustomerRecord, CustomerResolver


async def query_customer_balance(
    session: AsyncSession,
    customer_name: str,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """
    Deterministic balance lookup for a named customer.
    LLM is never used for arithmetic.
    """
    # 1. Fetch all customers to resolve name
    all_cust_q = await session.execute(select(Customer))
    db_customers = all_cust_q.scalars().all()
    records = [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in db_customers]

    resolver = CustomerResolver(records)
    res = await resolver.resolve(customer_name)

    if not res.is_resolved:
        if res.is_ambiguous:
            cand_names = [c.name for c in res.candidates[:2]]
            return {
                "query_type": "customer_balance",
                "found": False,
                "status": "ambiguous",
                "message": f"Did you mean {' or '.join(cand_names)}?",
                "candidates": [c.name for c in res.candidates],
                "spoken_text": None
                if quiet_mode
                else f"Kya aapka matlab {' ya '.join(cand_names)} hai?",
                "data": None,
            }
        return {
            "query_type": "customer_balance",
            "found": False,
            "status": "not_found",
            "message": f"Customer '{customer_name}' nahi mila.",
            "spoken_text": None
            if quiet_mode
            else f"Maaf kijiye, {customer_name} naam ka koi customer nahi mila.",
            "data": None,
        }

    # High-confidence or exact match
    target_cust = next(c for c in db_customers if c.id == res.resolved_id)
    evt_q = await session.execute(
        select(LedgerEvent).where(
            LedgerEvent.customer_id == target_cust.id,
            LedgerEvent.is_compensated.is_(False),
        )
    )
    events = evt_q.scalars().all()

    balance = 0.0
    for e in events:
        if e.event_type in ("add_credit_sale", "credit_sale"):
            balance += e.amount
        elif e.event_type == "payment_received":
            balance -= e.amount
        elif e.event_type == "compensation_undo":
            balance += e.amount

    abs_bal = abs(round(balance, 2))
    amt_words = number_to_hindi_words(int(abs_bal))

    if balance > 0:
        display_text = f"{target_cust.name}: ₹{balance:.2f} udhaar baaki hai."
        spoken_text = f"{target_cust.name} ka {amt_words} rupaye baaki hai."
    elif balance < 0:
        display_text = f"{target_cust.name}: ₹{abs_bal:.2f} advance jama hai."
        spoken_text = f"{target_cust.name} ka {amt_words} rupaye advance jama hai."
    else:
        display_text = f"{target_cust.name}: hisaab barabar hai (₹0.00)."
        spoken_text = f"{target_cust.name} ka hisaab barabar hai."

    return {
        "query_type": "customer_balance",
        "found": True,
        "status": "success",
        "customer_id": target_cust.id,
        "customer_name": target_cust.name,
        "balance": balance,
        "display_text": display_text,
        "spoken_text": None if quiet_mode else spoken_text,
        "quiet_mode": quiet_mode,
        "data": {
            "customer_name": target_cust.name,
            "balance": balance,
            "event_count": len(events),
        },
    }


async def query_today_udhaar(
    session: AsyncSession,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """Compute total udhaar given today."""
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    evt_q = await session.execute(
        select(LedgerEvent).where(
            LedgerEvent.created_at >= today_start,
            LedgerEvent.event_type.in_(["add_credit_sale", "credit_sale"]),
            LedgerEvent.is_compensated.is_(False),
        )
    )
    events = evt_q.scalars().all()
    total = sum(e.amount for e in events)
    amt_words = number_to_hindi_words(int(total))

    display = f"Aaj ka kul udhaar: ₹{total:.2f}"
    spoken = (
        f"Aaj kul {amt_words} rupaye ka udhaar diya gaya."
        if total > 0
        else "Aaj koi naya udhaar nahi diya gaya."
    )

    return {
        "query_type": "today_udhaar",
        "total_amount": total,
        "count": len(events),
        "display_text": display,
        "spoken_text": None if quiet_mode else spoken,
        "quiet_mode": quiet_mode,
    }


async def query_today_collection(
    session: AsyncSession,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """Compute total payment collected / jama today."""
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    evt_q = await session.execute(
        select(LedgerEvent).where(
            LedgerEvent.created_at >= today_start,
            LedgerEvent.event_type == "payment_received",
            LedgerEvent.is_compensated.is_(False),
        )
    )
    events = evt_q.scalars().all()
    total = sum(e.amount for e in events)
    amt_words = number_to_hindi_words(int(total))

    display = f"Aaj ki kul vasooli: ₹{total:.2f}"
    spoken = (
        f"Aaj kul {amt_words} rupaye jama huye."
        if total > 0
        else "Aaj koi vasooli ya payment nahi aayi."
    )

    return {
        "query_type": "today_collection",
        "total_amount": total,
        "count": len(events),
        "display_text": display,
        "spoken_text": None if quiet_mode else spoken,
        "quiet_mode": quiet_mode,
    }


async def query_top_debtors(
    session: AsyncSession,
    limit: int = 5,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """List top debtors by outstanding balance."""
    all_cust_q = await session.execute(select(Customer))
    customers = all_cust_q.scalars().all()

    cust_balances: list[tuple[str, str, float]] = []
    for c in customers:
        evt_q = await session.execute(
            select(LedgerEvent).where(
                LedgerEvent.customer_id == c.id,
                LedgerEvent.is_compensated.is_(False),
            )
        )
        evts = evt_q.scalars().all()
        bal = 0.0
        for e in evts:
            if e.event_type in ("add_credit_sale", "credit_sale"):
                bal += e.amount
            elif e.event_type == "payment_received":
                bal -= e.amount
            elif e.event_type == "compensation_undo":
                bal += e.amount
        if bal > 0:
            cust_balances.append((c.id, c.name, bal))

    cust_balances.sort(key=lambda x: x[2], reverse=True)
    top_list = cust_balances[:limit]

    if not top_list:
        return {
            "query_type": "top_debtors",
            "top_debtors": [],
            "display_text": "Kisi customer ka udhaar baaki nahi hai.",
            "spoken_text": None if quiet_mode else "Kisi customer ka koi udhaar baaki nahi hai.",
            "quiet_mode": quiet_mode,
        }

    leader_name = top_list[0][1]
    leader_amt = top_list[0][2]
    leader_words = number_to_hindi_words(int(leader_amt))

    display = f"Sabse zyada udhaar {leader_name} ka hai: ₹{leader_amt:.2f}."
    spoken = f"Sabse zyada baaki {leader_name} ka hai, {leader_words} rupaye."

    return {
        "query_type": "top_debtors",
        "top_debtors": [
            {"customer_id": cid, "customer_name": name, "balance": bal}
            for cid, name, bal in top_list
        ],
        "display_text": display,
        "spoken_text": None if quiet_mode else spoken,
        "quiet_mode": quiet_mode,
    }


async def query_last_payment(
    session: AsyncSession,
    customer_name: str,
    quiet_mode: bool = False,
) -> dict[str, Any]:
    """Look up last payment date and amount for a customer."""
    all_cust_q = await session.execute(select(Customer))
    db_customers = all_cust_q.scalars().all()
    records = [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in db_customers]

    resolver = CustomerResolver(records)
    res = await resolver.resolve(customer_name)

    if not res.is_resolved or not res.resolved_id:
        return {
            "query_type": "last_payment",
            "found": False,
            "display_text": f"Customer '{customer_name}' nahi mila.",
            "spoken_text": None if quiet_mode else f"{customer_name} naam ka customer nahi mila.",
            "quiet_mode": quiet_mode,
        }

    target_cust = next(c for c in db_customers if c.id == res.resolved_id)
    last_pmt_q = await session.execute(
        select(LedgerEvent)
        .where(
            LedgerEvent.customer_id == target_cust.id,
            LedgerEvent.event_type == "payment_received",
            LedgerEvent.is_compensated.is_(False),
        )
        .order_by(desc(LedgerEvent.created_at))
        .limit(1)
    )
    last_pmt = last_pmt_q.scalar_one_or_none()

    if not last_pmt:
        return {
            "query_type": "last_payment",
            "found": True,
            "has_payment": False,
            "customer_name": target_cust.name,
            "display_text": f"{target_cust.name} ka abhi tak koi payment record nahi hai.",
            "spoken_text": None
            if quiet_mode
            else f"{target_cust.name} ka abhi tak koi payment jama nahi hua hai.",
            "quiet_mode": quiet_mode,
        }

    amt_words = number_to_hindi_words(int(last_pmt.amount))
    date_str = last_pmt.created_at.strftime("%d %b")
    display = (
        f"{target_cust.name} ne aakhiri baar ₹{last_pmt.amount:.2f} jama kiye the ({date_str})."
    )
    spoken = f"{target_cust.name} ne aakhiri baar {amt_words} rupaye jama kiye the."

    return {
        "query_type": "last_payment",
        "found": True,
        "has_payment": True,
        "customer_name": target_cust.name,
        "amount": last_pmt.amount,
        "date": date_str,
        "created_at": last_pmt.created_at.isoformat(),
        "display_text": display,
        "spoken_text": None if quiet_mode else spoken,
        "quiet_mode": quiet_mode,
    }
