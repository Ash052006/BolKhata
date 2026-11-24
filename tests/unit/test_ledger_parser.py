"""
Unit tests for deterministic rule-based Kirana ledger parsing.
"""

import pytest

from bolkhata.domains.ledger.parser import parse_ledger_rules


@pytest.mark.parametrize(
    ("input_text", "expected_intent", "expected_customer", "expected_amount"),
    [
        # 1. Credit Sales (udhaar)
        ("Ramesh ji ko dhai sau rupaye udhaar likho", "add_credit_sale", "Ramesh", 250.0),
        ("Sharma ji ko do sau pachaas rupaye udhaar", "add_credit_sale", "Sharma", 250.0),
        ("Verma ji ke khate me teen sau rupaye likh do", "add_credit_sale", "Verma", 300.0),
        ("Gupta ji ko paune do sau rupaye udhaar", "add_credit_sale", "Gupta", 175.0),
        ("Suresh ko derh hazaar rupaye udhaar", "add_credit_sale", "Suresh", 1500.0),
        # 2. Payment Received (jama)
        ("Ramesh ji ne paanch sau rupaye jama kiye", "payment_received", "Ramesh", 500.0),
        ("Sharma ji se do sau rupaye cash mila", "payment_received", "Sharma", 200.0),
        ("Verma ji ne ek hazaar rupaye diye", "payment_received", "Verma", 1000.0),
        # 3. Cash Sale (nagad)
        ("dhai sau rupaye nagad bikri hui", "cash_sale", None, 250.0),
        ("teen sau rupaye cash sale", "cash_sale", None, 300.0),
        # 4. Store Expense (kharcha)
        ("chai aur samosa pachaas rupaye kharcha", "expense", None, 50.0),
        ("bijli bill do hazaar rupaye expense", "expense", None, 2000.0),
        ("dukan ka kharcha ek sau rupaye", "expense", None, 100.0),
        # 5. Query Balance (baaki / hisaab)
        ("Ramesh ji ka kitna baaki hai", "query_balance", "Ramesh", None),
        ("Sharma ji ka balance batao", "query_balance", "Sharma", None),
        ("Verma ji ka kitna hisaab hua", "query_balance", "Verma", None),
        # 6. Undo Intent
        ("undo karo", "undo_last", None, None),
        ("galat likh diya cancel karo", "undo_last", None, None),
        ("pichla wala hisaab hatao", "undo_last", None, None),
    ],
)
def test_parse_ledger_rules_intents(
    input_text: str,
    expected_intent: str,
    expected_customer: str | None,
    expected_amount: float | None,
) -> None:
    intent = parse_ledger_rules(input_text)
    assert intent is not None, f"Failed to parse rule intent for '{input_text}'"
    assert intent.name == expected_intent
    if expected_customer is not None:
        assert intent.customer == expected_customer
    if expected_amount is not None:
        assert intent.amount == pytest.approx(expected_amount)


def test_parse_ledger_rules_date_and_payment_mode() -> None:
    text = "Kal Ramesh ji ne paanch sau rupaye online upi se jama kiye"
    intent = parse_ledger_rules(text)
    assert intent is not None
    assert intent.name == "payment_received"
    assert intent.date == "kal"
    assert intent.payment_mode == "upi"
    assert intent.amount == 500.0
