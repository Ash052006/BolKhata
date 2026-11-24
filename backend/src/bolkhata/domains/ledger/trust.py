"""
Trust UX, Voice Correction, Risk Evaluation, and Daily Summary for Kirana Ledger.

Enforces:
1. Hard confirmation safety: No entry is ever committed without an explicit confirmation.
2. High-risk thresholds: Strict verbal read-back (including digit-by-digit) on large amounts,
   low ASR confidence, ambiguous numbers, or unresolved customers.
3. Voice correction patching: Modifies pending entries with bounded retry counts.
4. Deterministic read-back: Spoken text uses mathematical number-to-words conversion.
5. 'Aaj ka hisaab' daily digest generation from append-only events.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from bolkhata.domains.base import DomainAction
from bolkhata.domains.common.number_words import (
    number_to_digits_spoken,
    number_to_hindi_words,
)
from bolkhata.domains.common.numbers import extract_numbers
from bolkhata.domains.ledger.db_models import LedgerEvent
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.pack import LedgerDomainPack

# Configurable high-risk amount threshold (₹5,000)
HIGH_RISK_AMOUNT_THRESHOLD = 5000.0


class PendingEntry(BaseModel):
    """Mutable pending ledger transaction awaiting merchant verbal confirmation."""

    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    intent: LedgerIntent
    customer_id: str | None = None
    customer_resolved: bool = True
    action: DomainAction | None = None
    risk_level: Literal["standard", "high"] = "standard"
    risk_reasons: list[str] = Field(default_factory=list)
    read_back_spoken: str = ""
    read_back_display: str = ""
    is_confirmed: bool = False
    is_cancelled: bool = False
    correction_count: int = 0
    max_corrections: int = 3
    requires_manual_edit: bool = False
    patch_history: list[dict[str, Any]] = Field(default_factory=list)


def evaluate_risk(
    intent: LedgerIntent,
    asr_confidence: float | None = None,
    customer_resolved: bool = True,
    amount_threshold: float = HIGH_RISK_AMOUNT_THRESHOLD,
) -> tuple[Literal["standard", "high"], list[str]]:
    """Evaluate whether an extracted intent exceeds risk safety thresholds."""
    reasons: list[str] = []

    if intent.amount is not None and intent.amount >= amount_threshold:
        reasons.append(f"Amount ₹{intent.amount:,.2f} exceeds risk limit ₹{amount_threshold:,.2f}")

    if asr_confidence is not None and asr_confidence < 0.80:
        reasons.append(f"Low ASR acoustic confidence ({asr_confidence:.2f} < 0.80)")

    if intent.is_ambiguous:
        reasons.append(f"Ambiguous intent or number range detected: {intent.ambiguity_details}")

    if intent.customer and not customer_resolved:
        reasons.append(f"Customer '{intent.customer}' is unrecognized or in gray-zone")

    risk_level: Literal["standard", "high"] = "high" if reasons else "standard"
    return risk_level, reasons


def generate_read_back(
    intent: LedgerIntent,
    risk_level: Literal["standard", "high"] = "standard",
    devanagari: bool = False,
) -> tuple[str, str]:
    """
    Generate deterministic spoken and display confirmation templates.

    Uses number_to_hindi_words so amounts are spoken exactly as stored.
    """
    cust_name = intent.customer or ("Grahak" if not devanagari else "ग्राहक")
    amount_val = intent.amount or 0.0
    amount_spoken = number_to_hindi_words(amount_val, devanagari=devanagari)

    action_label_map = {
        "add_credit_sale": ("udhaar", "उधार"),
        "payment_received": ("jama", "जमा"),
        "cash_sale": ("nagad bikri", "नकद बिक्री"),
        "expense": ("kharcha", "खर्चा"),
        "query_balance": ("hisaab jaanch", "हिसाब जाँच"),
        "undo_last": ("undo", "रद्द"),
    }
    action_words = action_label_map.get(
        intent.name,
        ("entry", "प्रविष्टि"),
    )
    action_word = action_words[1] if devanagari else action_words[0]

    items_str = ""
    if intent.items:
        items_str = f", {', '.join(intent.items)}"

    if risk_level == "high":
        # Strict high-risk confirmation: includes digit-by-digit pronunciation
        digits_spoken = number_to_digits_spoken(amount_val, devanagari=devanagari)
        if devanagari:
            spoken = (
                f"चेतावनी: बड़ा लेन-देन है — {cust_name} जी, {amount_spoken} रुपये ({digits_spoken}) {action_word}{items_str}। "
                f"क्या यह सही है? हाँ या नहीं बोलें।"
            )
            display = (
                f"⚠️ बड़ा अमाउंट: {cust_name} — ₹{amount_val:,.2f} {action_word}{items_str}। पुष्टि करें।"
            )
        else:
            spoken = (
                f"Chetavni: Bada amount hai — {cust_name} ji, {amount_spoken} rupaye ({digits_spoken}) {action_word}{items_str}. "
                f"Kya yeh sahi hai? Haan ya nahi bolein."
            )
            display = f"⚠️ Bada Amount: {cust_name} — ₹{amount_val:,.2f} {action_word}{items_str}. Confirm karein."
    else:
        # Standard confirmation
        if devanagari:
            spoken = f"{cust_name} जी, {amount_spoken} रुपये {action_word}{items_str}। सही है?"
            display = f"{cust_name}: ₹{amount_val:,.2f} {action_word}{items_str}. सही है?"
        else:
            spoken = f"{cust_name} ji, {amount_spoken} rupaye {action_word}{items_str}. Sahi hai?"
            display = f"{cust_name}: ₹{amount_val:,.2f} {action_word}{items_str}. Sahi hai?"

    return spoken, display


def create_pending_entry(
    intent: LedgerIntent,
    customer_id: str | None = None,
    asr_confidence: float | None = None,
    customer_resolved: bool = True,
    client_turn_id: str = "t1",
) -> PendingEntry:
    """Initialize a new PendingEntry with evaluated risk and deterministic read-back."""
    risk_level, reasons = evaluate_risk(
        intent,
        asr_confidence=asr_confidence,
        customer_resolved=customer_resolved,
    )
    pack = LedgerDomainPack()
    action = pack.create_action(intent, customer_id=customer_id, client_turn_id=client_turn_id)
    spoken, display = generate_read_back(intent, risk_level=risk_level)

    return PendingEntry(
        intent=intent,
        customer_id=customer_id,
        customer_resolved=customer_resolved,
        action=action,
        risk_level=risk_level,
        risk_reasons=reasons,
        read_back_spoken=spoken,
        read_back_display=display,
    )


def apply_voice_correction(
    pending: PendingEntry,
    correction_text: str,
) -> PendingEntry:
    """
    Apply a voice patch to an uncommitted pending entry.

    Handles:
    - Amount patch: "nahi teen sau nahi, teen sau pachaas" / "nahi 500"
    - Customer patch: "customer Verma ji hai" / "Sharma nahi Verma"
    - Date patch: "kal ka likho"
    - Item patch: "chini nahi chawal"
    """
    clean_text = correction_text.strip().lower()

    if pending.correction_count >= pending.max_corrections:
        pending.requires_manual_edit = True
        pending.read_back_spoken = "Bahut baar badlaav ho chuka hai. Kripya screen par dekh kar manually theek karein ya cancel bolein."
        pending.read_back_display = "Adhik badlaav. Manual edit karein ya Cancel."
        return pending

    patch_details: dict[str, Any] = {"raw": correction_text}

    # 1. Check Amount patch
    # Look for spoken numbers or digits in correction
    numbers = extract_numbers(clean_text)
    if numbers:
        # If phrase is "nahi X nahi Y", pick Y (the last number)
        new_amt = numbers[-1].value
        patch_details["field"] = "amount"
        patch_details["old"] = pending.intent.amount
        patch_details["new"] = new_amt
        pending.intent.amount = new_amt
        pending.intent.provenance["amount"] = "voice_correction"

    # 2. Check Customer patch ("customer Verma ji", "Sharma nahi Verma")
    cust_match = re.search(
        r"\b(?:customer|naam|ko|seth|ji|bhai)\s+([a-zA-Z\u0900-\u097F]+)", clean_text
    )
    if not cust_match and "nahi" in clean_text:
        # e.g., "Sharma nahi Verma"
        sub_match = re.search(r"nahi\s*,?\s*([a-zA-Z\u0900-\u097F]+)\s*(?:ji|bhai)?", clean_text)
        if sub_match and not extract_numbers(sub_match.group(1)):
            cust_match = sub_match

    if cust_match:
        cand_name = cust_match.group(1).capitalize()
        # Ensure it's not a number word or keyword
        if cand_name.lower() not in ("teen", "sau", "hazaar", "kal", "parso", "aaj", "rupaye"):
            patch_details["field"] = "customer"
            patch_details["old"] = pending.intent.customer
            patch_details["new"] = cand_name
            pending.intent.customer = cand_name
            pending.intent.provenance["customer"] = "voice_correction"

    # 3. Check Date patch ("kal ka", "parso ka", "aaj ka")
    date_m = re.search(r"\b(kal|parso|aaj)\b", clean_text)
    if date_m:
        new_date = date_m.group(1)
        patch_details["field"] = "date"
        patch_details["old"] = pending.intent.date
        patch_details["new"] = new_date
        pending.intent.date = new_date
        pending.intent.provenance["date"] = "voice_correction"

    # 4. Check Item patch ("chini nahi chawal")
    for itm in ("chawal", "chini", "atta", "dal", "tel", "namak", "doodh"):
        if itm in clean_text:
            patch_details["field"] = "items"
            patch_details["new"] = [itm]
            pending.intent.items = [itm]
            pending.intent.provenance["items"] = "voice_correction"

    # Update state
    pending.correction_count += 1
    pending.patch_history.append(patch_details)

    # Re-evaluate risk & re-generate read-back
    risk_level, reasons = evaluate_risk(
        pending.intent,
        customer_resolved=pending.customer_resolved,
    )
    pending.risk_level = risk_level
    pending.risk_reasons = reasons

    pack = LedgerDomainPack()
    pending.action = pack.create_action(
        pending.intent,
        customer_id=pending.customer_id,
        client_turn_id=pending.entry_id,
    )
    spoken, display = generate_read_back(pending.intent, risk_level=risk_level)
    pending.read_back_spoken = f"Theek hai, badal diya. {spoken}"
    pending.read_back_display = f"Updated: {display}"

    return pending


def confirm_pending_entry(pending: PendingEntry) -> DomainAction:
    """
    Commit confirmation of a pending entry.

    STRICT INVARIANT:
    No entry is ever saved without an explicit confirmation.
    Raises ValueError if is_confirmed is False.
    """
    if not pending.is_confirmed:
        raise ValueError(
            "Cannot commit entry: entry has not been explicitly confirmed by merchant."
        )
    if pending.is_cancelled:
        raise ValueError("Cannot commit entry: entry was cancelled.")
    if pending.action is None:
        raise ValueError("Cannot commit entry: no action generated for pending entry.")

    return pending.action


def generate_daily_summary(events: list[LedgerEvent], devanagari: bool = False) -> dict[str, Any]:
    """
    Generate spoken and display daily summary ('Aaj ka hisaab') from stored events.

    Pure template-based from persisted data.
    """
    total_tx_count = len(events)
    total_credit = 0.0
    total_cash_sales = 0.0
    total_payments_received = 0.0
    total_expenses = 0.0

    for e in events:
        if e.is_compensated:
            continue
        if e.event_type == "add_credit_sale":
            total_credit += e.amount
        elif e.event_type == "cash_sale":
            total_cash_sales += e.amount
        elif e.event_type == "payment_received":
            total_payments_received += e.amount
        elif e.event_type == "expense":
            total_expenses += e.amount

    if devanagari:
        spoken = (
            f"आज कुल {total_tx_count} लेन-देन हुए। "
            f"उधार {number_to_hindi_words(total_credit, devanagari=True)} रुपये, "
            f"नकद बिक्री {number_to_hindi_words(total_cash_sales, devanagari=True)} रुपये, "
            f"जमा {number_to_hindi_words(total_payments_received, devanagari=True)} रुपये, "
            f"खर्चा {number_to_hindi_words(total_expenses, devanagari=True)} रुपये।"
        )
        display = (
            f"आज का हिसाब: कुल {total_tx_count} लेन-देन | "
            f"उधार: ₹{total_credit:,.2f} | नकद: ₹{total_cash_sales:,.2f} | "
            f"जमा: ₹{total_payments_received:,.2f} | खर्चा: ₹{total_expenses:,.2f}"
        )
    else:
        spoken = (
            f"Aaj kul {total_tx_count} hisaab hue. "
            f"Udhaar {number_to_hindi_words(total_credit)} rupaye, "
            f"nagad bikri {number_to_hindi_words(total_cash_sales)} rupaye, "
            f"jama {number_to_hindi_words(total_payments_received)} rupaye, "
            f"kharcha {number_to_hindi_words(total_expenses)} rupaye."
        )
        display = (
            f"Aaj Ka Hisaab: Kul {total_tx_count} entries | "
            f"Udhaar: ₹{total_credit:,.2f} | Nagad: ₹{total_cash_sales:,.2f} | "
            f"Jama: ₹{total_payments_received:,.2f} | Kharcha: ₹{total_expenses:,.2f}"
        )

    return {
        "transaction_count": total_tx_count,
        "total_credit": total_credit,
        "total_cash_sales": total_cash_sales,
        "total_payments_received": total_payments_received,
        "total_expenses": total_expenses,
        "spoken_summary": spoken,
        "display_summary": display,
    }
