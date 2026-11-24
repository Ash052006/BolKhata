"""
Hierarchical extraction pipeline for the Kirana Ledger domain.

Execution Order:
1. Deterministic rule-based parser using S2 spoken numbers and units.
2. LLM structured extraction ONLY for unstructured syntax rules cannot resolve,
   with JSON-schema validation, bounded retries, and safe fallback.
3. Merge with field-level provenance tracking ('rules' vs 'llm').
4. Invariant: LLM never computes or decides money amounts; numbers are always
   normalized through deterministic Python grammars.
"""

from __future__ import annotations

from typing import Any

from bolkhata.common.logging import get_logger
from bolkhata.domains.common.numbers import extract_numbers, parse_spoken_number
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.parser import parse_ledger_rules
from bolkhata.llm.base import ChatMessage, LLMProvider

logger = get_logger(__name__)


async def extract_ledger_intent(
    text: str,
    llm_provider: LLMProvider | None = None,
) -> LedgerIntent:
    """
    Extract structured ledger intent and entities from speech transcript.

    Rules run first. If rules produce a complete intent, returns immediately with 100% provenance.
    If rules are partial or unresolved and LLM provider is provided, invokes LLM with bounded retry.
    """
    cleaned = text.strip()
    if not cleaned:
        return LedgerIntent(
            name="query_balance",
            confidence=0.0,
            provenance={"intent": "default"},
        )

    # 1. Deterministic Rule-Based Parser
    rule_intent = parse_ledger_rules(cleaned)

    # Check rule numbers independently for hard safety
    extracted_nums = extract_numbers(cleaned)
    rule_amount: float | None = extracted_nums[0].value if extracted_nums else None

    # If rules resolved both intent and essential entities, return immediately
    if rule_intent is not None:
        if rule_intent.name in ("undo_last", "query_balance") or (
            rule_intent.amount is not None
            and rule_intent.name in ("add_credit_sale", "payment_received", "cash_sale", "expense")
        ):
            return rule_intent

    # If no LLM provider or rules are complete enough, return rule intent
    if llm_provider is None:
        if rule_intent is not None:
            return rule_intent
        # Safe fallback if rules cannot parse and no LLM is wired
        return LedgerIntent(
            name="add_credit_sale" if rule_amount else "query_balance",
            amount=rule_amount,
            confidence=0.5 if rule_amount else 0.0,
            provenance={"amount": "rules"} if rule_amount else {"intent": "default"},
        )

    # 2. LLM Structured Extraction (Bounded Retry = 2)
    llm_result_data: dict[str, Any] | None = None
    messages = [
        ChatMessage(
            role="system", content="Extract structured ledger intent from shopkeeper speech."
        ),
        ChatMessage(role="user", content=cleaned),
    ]

    for attempt in range(2):
        try:
            llm_res = await llm_provider.complete_structured(messages, LedgerIntent)
            if llm_res:
                llm_result_data = llm_res.model_dump()
                break
        except Exception as e:
            logger.warning("llm_extraction_attempt_failed", attempt=attempt, error=str(e))

    if llm_result_data is None:
        # LLM failed -> Fall back to rule_intent or default
        if rule_intent is not None:
            return rule_intent
        return LedgerIntent(
            name="add_credit_sale" if rule_amount else "query_balance",
            amount=rule_amount,
            confidence=0.4 if rule_amount else 0.0,
            provenance={"amount": "rules"} if rule_amount else {"intent": "default"},
        )

    # 3. Merge with Provenance and Enforce Money Safety
    provenance: dict[str, str] = {}

    # Intent name
    intent_name = llm_result_data.get("name")
    if rule_intent and rule_intent.name:
        intent_name = rule_intent.name
        provenance["intent"] = "rules"
    elif intent_name in (
        "add_credit_sale",
        "payment_received",
        "cash_sale",
        "expense",
        "query_balance",
        "query_today_udhaar",
        "query_today_collection",
        "query_top_debtors",
        "query_last_payment",
        "undo_last",
    ):
        provenance["intent"] = "llm"
    else:
        intent_name = "add_credit_sale" if rule_amount else "query_balance"
        provenance["intent"] = "default"

    # Amount: Money Safety Invariant:
    # Rule amount ALWAYS takes precedence. If rules didn't find one, verify LLM value against deterministic parser
    final_amount: float | None = None
    if rule_amount is not None:
        final_amount = rule_amount
        provenance["amount"] = "rules"
    elif "amount" in llm_result_data and llm_result_data["amount"] is not None:
        # Re-parse LLM amount via deterministic parser
        raw_amt_str = str(llm_result_data["amount"])
        parsed_val = parse_spoken_number(raw_amt_str)
        if parsed_val is not None:
            final_amount = parsed_val
            provenance["amount"] = "llm_parsed"

    # Customer
    customer = (
        rule_intent.customer
        if (rule_intent and rule_intent.customer)
        else llm_result_data.get("customer")
    )
    if customer:
        provenance["customer"] = "rules" if (rule_intent and rule_intent.customer) else "llm"

    # Items
    items = (
        rule_intent.items
        if (rule_intent and rule_intent.items)
        else llm_result_data.get("items", [])
    )
    if items:
        provenance["items"] = "rules" if (rule_intent and rule_intent.items) else "llm"

    # Date
    date_val = (
        rule_intent.date
        if (rule_intent and rule_intent.date)
        else llm_result_data.get("date", "aaj")
    )
    provenance["date"] = "rules" if (rule_intent and rule_intent.date) else "llm"

    # Payment mode
    payment_mode = (
        rule_intent.payment_mode
        if (rule_intent and rule_intent.payment_mode)
        else llm_result_data.get("payment_mode", "cash")
    )

    return LedgerIntent(
        name=intent_name,
        customer=customer,
        amount=final_amount,
        items=items,
        quantity=rule_intent.quantity if rule_intent else None,
        unit=rule_intent.unit if rule_intent else None,
        date=date_val,
        payment_mode=payment_mode,
        confidence=0.9,
        provenance=provenance,
    )
