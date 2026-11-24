"""
Deterministic rule-based parser for Kirana ledger utterances.

Extracts:
- Intents: add_credit_sale (udhaar), payment_received (jama), cash_sale (nagad),
  expense (kharcha), query_balance (baaki/balance), undo_last.
- Entities: customer, amount, currency, items, quantity, unit, date, payment_mode.
- Uses S2 numbers.py and units.py for mathematical safety.
"""

from __future__ import annotations

import re

from bolkhata.domains.common.numbers import extract_numbers
from bolkhata.domains.common.units import parse_money_amount, parse_quantity
from bolkhata.domains.ledger.models import LedgerIntent


def _extract_date_word(text: str) -> tuple[str, str]:
    """Extract date word (aaj, kal, parso) and return (cleaned_text, date)."""
    text_lower = text.lower()
    if re.search(r"\bparso\b|\bपरसों\b", text_lower):
        cleaned = re.sub(r"\bparso\b|\bपरसों\b", "", text, flags=re.IGNORECASE)
        return cleaned.strip(), "parso"
    if re.search(r"\bkal\b|\bकल\b", text_lower):
        cleaned = re.sub(r"\bkal\b|\bकल\b", "", text, flags=re.IGNORECASE)
        return cleaned.strip(), "kal"
    if re.search(r"\baaj\b|\bआज\b", text_lower):
        cleaned = re.sub(r"\baaj\b|\bआज\b", "", text, flags=re.IGNORECASE)
        return cleaned.strip(), "aaj"
    return text, "aaj"


def _extract_payment_mode(text: str) -> str:
    """Extract payment mode (cash, upi, online)."""
    t = text.lower()
    if "upi" in t or "gpay" in t or "phonepe" in t or "paytm" in t or "online" in t:
        return "upi"
    return "cash"


def _extract_customer_name(text: str) -> str | None:
    """Extract customer name from subject positions before postpositions."""
    # Matches patterns like:
    # "Ramesh ji ko", "Sharma ji ke khate me", "Verma ji ne", "Gupta se"
    m = re.search(
        r"^(?:arre\s+|sunno\s+)?(?P<name>[a-zA-Z\u0900-\u097f\s]+?)\s+(?:ji\s+|bhai\s+|uncle\s+|aunty\s+|sahab\s+)?(?:ko|ke\s+khate|ke\s+account|ne|se|ka)\b",
        text.strip(),
        re.IGNORECASE,
    )
    if m:
        candidate = m.group("name").strip()
        # Clean filler words
        tokens = candidate.split()
        if tokens and tokens[0].lower() in ("arre", "suno", "hey", "please", "bhai"):
            tokens = tokens[1:]
        name = " ".join(tokens)
        if name and not any(w in name.lower() for w in ("kitna", "baaki", "kharcha", "nagad")):
            return name
    return None


def parse_ledger_rules(text: str) -> LedgerIntent | None:
    """
    Attempt deterministic rule-based extraction on utterance text.

    Returns LedgerIntent if a recognized pattern matches, or None for LLM fallback.
    """
    cleaned_input = text.strip()
    if not cleaned_input:
        return None

    orig_lower = cleaned_input.lower()
    cleaned_text, date_val = _extract_date_word(cleaned_input)
    t_lower = cleaned_text.lower()
    payment_mode = _extract_payment_mode(cleaned_text)

    # 1. Undo Intent
    if re.search(r"\b(?:undo|cancel|galat\s+(?:hai|likh|ho)|hatao|pichla\s+wala)\b", t_lower):
        return LedgerIntent(
            name="undo_last",
            confidence=1.0,
            provenance={"intent": "rules"},
            date=date_val,
        )

    # 2. Query Intents
    if re.search(r"\b(?:(?:aaj\s+)?kitna\s+udhaar|aaj\s+ka\s+udhaar|kitna\s+diya)\b", orig_lower):
        return LedgerIntent(
            name="query_today_udhaar",
            confidence=0.95,
            provenance={"intent": "rules"},
            date=date_val,
        )

    if re.search(
        r"\b(?:(?:aaj\s+)?kitna\s+jama|(?:aaj\s+)?kitna\s+aaya|(?:aaj\s+ki\s+)?vasooli|(?:aaj\s+)?kitna\s+collection)\b",
        orig_lower,
    ):
        return LedgerIntent(
            name="query_today_collection",
            confidence=0.95,
            provenance={"intent": "rules"},
            date=date_val,
        )

    if re.search(
        r"\b(?:kisko\s+sabse\s+zyada|sabse\s+zyada\s+udhaar|sabse\s+zyada\s+baaki|top\s+debtor)\b",
        orig_lower,
    ):
        return LedgerIntent(
            name="query_top_debtors",
            confidence=0.95,
            provenance={"intent": "rules"},
            date=date_val,
        )

    if re.search(r"\b(?:last\s+payment|aakhiri\s+baar\s+kab|pichla\s+payment)\b", orig_lower):
        customer = _extract_customer_name(cleaned_text)
        return LedgerIntent(
            name="query_last_payment",
            customer=customer,
            confidence=0.95 if customer else 0.8,
            provenance={"intent": "rules", "customer": "rules"}
            if customer
            else {"intent": "rules"},
            date=date_val,
        )

    if re.search(
        r"\b(?:kitna\s+baaki|balance|hisaab\s+batao|kitna\s+hisaab|kitna\s+hua)\b", t_lower
    ):
        customer = _extract_customer_name(cleaned_text)
        return LedgerIntent(
            name="query_balance",
            customer=customer,
            confidence=0.95 if customer else 0.8,
            provenance={"intent": "rules", "customer": "rules"}
            if customer
            else {"intent": "rules"},
            date=date_val,
        )

    # 3. Extract numbers/amounts
    found_numbers = extract_numbers(cleaned_text)
    amount: float | None = None
    if found_numbers:
        amount = found_numbers[0].value

    # Check for direct money phrase
    money_res = parse_money_amount(cleaned_text)
    if money_res is not None:
        amount = money_res.amount

    # 4. Expense Intent (kharcha)
    if re.search(r"\b(?:kharcha|expense|chai|bijli\s+bill|samosa|kiraya)\b", t_lower):
        # Items / notes
        items: list[str] = []
        for word in ("chai", "samosa", "bijli bill", "kiraya", "nashta"):
            if word in t_lower:
                items.append(word)

        return LedgerIntent(
            name="expense",
            amount=amount,
            items=items,
            confidence=0.95 if amount is not None else 0.7,
            provenance={
                "intent": "rules",
                **({"amount": "rules"} if amount is not None else {}),
            },
            date=date_val,
            payment_mode=payment_mode,
        )

    # 5. Payment Received (jama / payment mila)
    if re.search(
        r"\b(?:jama|diye|mila|aaye|aaya|paid|payment|pay\s+kiya)\b", t_lower
    ) and not re.search(r"\budhaar\b|\blikh\b", t_lower):
        customer = _extract_customer_name(cleaned_text)
        return LedgerIntent(
            name="payment_received",
            customer=customer,
            amount=amount,
            confidence=0.95 if (customer and amount) else 0.8,
            provenance={
                "intent": "rules",
                **({"customer": "rules"} if customer else {}),
                **({"amount": "rules"} if amount is not None else {}),
            },
            date=date_val,
            payment_mode=payment_mode,
        )

    # 6. Cash Sale (nagad)
    if re.search(r"\b(?:nagad|cash\s+sale|bikri)\b", t_lower):
        qty_res = parse_quantity(cleaned_text)
        return LedgerIntent(
            name="cash_sale",
            amount=amount,
            quantity=qty_res.value if qty_res else None,
            unit=qty_res.unit if qty_res else None,
            confidence=0.95 if amount is not None else 0.75,
            provenance={
                "intent": "rules",
                **({"amount": "rules"} if amount is not None else {}),
            },
            date=date_val,
            payment_mode="cash",
        )

    # 7. Add Credit Sale (udhaar / likho)
    if re.search(r"\b(?:udhaar|likho|likh\s+do|likh\s+lo|khate\s+me|credit)\b", t_lower) or (
        amount is not None and re.search(r"\b(?:ko|ke\s+khate)\b", t_lower)
    ):
        customer = _extract_customer_name(cleaned_text)
        qty_res = parse_quantity(cleaned_text)
        credit_items: list[str] = []
        for itm in (
            "chini",
            "namak",
            "chawal",
            "atta",
            "tel",
            "dal",
            "milk",
            "doodh",
            "biscuit",
            "soap",
        ):
            if itm in t_lower:
                credit_items.append(itm)

        return LedgerIntent(
            name="add_credit_sale",
            customer=customer,
            amount=amount,
            items=credit_items,
            quantity=qty_res.value if qty_res else None,
            unit=qty_res.unit if qty_res else None,
            confidence=0.95 if (customer and amount) else 0.8,
            provenance={
                "intent": "rules",
                **({"customer": "rules"} if customer else {}),
                **({"amount": "rules"} if amount is not None else {}),
            },
            date=date_val,
            payment_mode="credit",
        )

    # Unrecognized by rule-based parser -> Return None for LLM extraction
    return None
