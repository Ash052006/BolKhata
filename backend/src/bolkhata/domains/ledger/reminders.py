"""
WhatsApp Payment Reminder Draft Generator (Feature F4).

Implements Prompt F4:
- Phone number validation and normalization to +91 E.164 format.
- Deterministic multi-lingual reminder templates across 3 tone levels (gentle, neutral, firm).
- Pre-filled WhatsApp click-to-chat URL encoding (supports Devanagari and Latin characters).
- Guardrails:
  - 'do_not_remind' opt-out flag check.
  - Non-positive balance check.
  - Recent reminder frequency warning (cooldown guardrail).
  - Cross-customer privacy guarantee (no cross-customer information).
  - Stores only audit metadata (timestamp, customer_id, tone), NEVER message text.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bolkhata.domains.ledger.ageing import calculate_events_fifo_ageing
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent, ReminderAudit


def normalize_phone_number(raw_phone: str | None) -> str | None:
    """
    Validate and normalize Indian phone number to E.164 (+91XXXXXXXXXX).
    Accepts 10-digit mobile numbers with optional +91, 91, or 0 prefixes.
    """
    if not raw_phone:
        return None
    # Strip spaces, hyphens, parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", raw_phone.strip())
    # Match standard Indian mobile patterns (starting with 6, 7, 8, 9)
    m = re.match(r"^(?:\+?91|0)?([6-9]\d{9})$", cleaned)
    if m:
        return f"+91{m.group(1)}"
    return None


def generate_reminder_text(
    customer_name: str,
    amount: float,
    tone: str = "neutral",
    language: str = "hi",
    days_overdue: int | None = None,
) -> str:
    """
    Generate deterministic reminder text without LLM arithmetic.
    """
    amt_str = f"₹{amount:.2f}"
    days = days_overdue if (days_overdue and days_overdue > 0) else 30

    if language == "en":
        if tone == "gentle":
            return (
                f"Hello {customer_name}, greetings from our store. You have a pending balance of "
                f"{amt_str}. Please clear it at your earliest convenience. Thank you!"
            )
        elif tone == "firm":
            return (
                f"Hello {customer_name}, your balance of {amt_str} has been outstanding for "
                f"{days} days. Please arrange to clear it today. Thank you."
            )
        else:  # neutral
            return (
                f"Hello {customer_name}, this is a gentle reminder regarding your pending balance "
                f"of {amt_str}. Kindly settle it when possible. Thank you."
            )
    else:  # Hindi / Hinglish default
        if tone == "gentle":
            return (
                f"Namaste {customer_name} ji, hamari dukaan se namaskar. Aapka {amt_str} ka hisaab baaki hai. "
                f"Suvidhanusar jama kara dein. Dhanyawad!"
            )
        elif tone == "firm":
            return (
                f"Namaste {customer_name} ji, aapka {amt_str} ka hisaab pichle {days} din se baaki hai. "
                f"Kripya aaj hi jama karein. Dhanyawad."
            )
        else:  # neutral
            return (
                f"Namaste {customer_name} ji, aapka {amt_str} ka udhaar hisaab baaki hai. "
                f"Kripya samay par bhej dein. Dhanyawad."
            )


def generate_whatsapp_url(phone: str, message: str) -> str:
    """Produce standard WhatsApp click-to-chat URL."""
    clean_phone = phone.lstrip("+")
    encoded_text = quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_text}"


async def draft_customer_reminder(
    session: AsyncSession,
    customer_id: str,
    tone: str = "neutral",
    language: str = "hi",
    cooldown_days: int = 3,
) -> dict[str, Any]:
    """
    Draft a WhatsApp reminder link with guardrail verifications.
    """
    cust_q = await session.execute(select(Customer).where(Customer.id == customer_id))
    cust = cust_q.scalar_one_or_none()
    if cust is None:
        raise ValueError(f"Customer with ID '{customer_id}' not found.")

    # Guardrail 1: Do Not Remind flag
    if cust.do_not_remind:
        return {
            "status": "blocked",
            "reason": "opted_out",
            "message": f"Customer '{cust.name}' has opted out of reminders ('do_not_remind' is set).",
            "whatsapp_url": None,
            "message_text": None,
        }

    # Guardrail 2: Phone number validation
    norm_phone = normalize_phone_number(cust.phone)
    if not norm_phone:
        return {
            "status": "blocked",
            "reason": "missing_phone",
            "message": f"Customer '{cust.name}' does not have a valid +91 phone number.",
            "whatsapp_url": None,
            "message_text": None,
        }

    # Guardrail 3: Compute actual balance & oldest due date via FIFO ageing
    evt_q = await session.execute(select(LedgerEvent).where(LedgerEvent.customer_id == customer_id))
    events = evt_q.scalars().all()
    ageing = calculate_events_fifo_ageing(list(events), cust.id, cust.name)

    if ageing.total_balance <= 0:
        return {
            "status": "blocked",
            "reason": "zero_balance",
            "message": f"Customer '{cust.name}' has no outstanding balance (₹0.00).",
            "whatsapp_url": None,
            "message_text": None,
        }

    # Guardrail 4: Recent reminder cooldown check
    now = datetime.now(UTC)
    cooldown_threshold = now - timedelta(days=cooldown_days)
    recent_q = await session.execute(
        select(ReminderAudit)
        .where(
            ReminderAudit.customer_id == customer_id,
            ReminderAudit.drafted_at >= cooldown_threshold,
        )
        .order_by(desc(ReminderAudit.drafted_at))
        .limit(1)
    )
    recent_audit = recent_q.scalar_one_or_none()
    recent_warning = False
    warning_note = None
    if recent_audit is not None:
        recent_warning = True
        drafted_dt = recent_audit.drafted_at
        if drafted_dt.tzinfo is None:
            drafted_dt = drafted_dt.replace(tzinfo=UTC)
        days_ago = (now - drafted_dt).days
        warning_note = f"Warning: A reminder was already drafted {days_ago} days ago ({drafted_dt.strftime('%Y-%m-%d')})."

    # Generate message
    msg = generate_reminder_text(
        customer_name=cust.name,
        amount=ageing.total_balance,
        tone=tone,
        language=language,
        days_overdue=ageing.oldest_due_days,
    )
    url = generate_whatsapp_url(norm_phone, msg)

    # Record audit metadata ONLY (never the message text!)
    audit_entry = ReminderAudit(
        customer_id=customer_id,
        tone=tone,
        drafted_at=now,
    )
    session.add(audit_entry)
    await session.commit()

    return {
        "status": "success",
        "customer_id": cust.id,
        "customer_name": cust.name,
        "phone": norm_phone,
        "balance": ageing.total_balance,
        "tone": tone,
        "message_text": msg,
        "whatsapp_url": url,
        "recent_reminder_warning": recent_warning,
        "warning_note": warning_note,
    }
