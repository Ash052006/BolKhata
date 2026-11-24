"""
Concrete implementation of the Kirana Shopkeeper Ledger DomainPack.
"""

from __future__ import annotations

import hashlib
from typing import Any

from bolkhata.domains.base import DomainAction, DomainIntent, DomainPack
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.parser import parse_ledger_rules
from bolkhata.domains.ledger.resolver import CustomerRecord, CustomerResolver

LEDGER_SYSTEM_PROMPT_V1 = """You are BolKhata's Kirana Ledger semantic extractor.
Extract intent and entities from Indian shopkeeper speech (Hindi, English, Hinglish).
Return a JSON object conforming strictly to the requested schema.
Intents:
- add_credit_sale (udhaar / credit purchase)
- payment_received (jama / payment collected)
- cash_sale (nagad / immediate cash purchase)
- expense (dukan ka kharcha / store operating cost)
- query_balance (baaki / hisaab enquiry)
- undo_last (cancel or undo previous entry)

IMPORTANT:
- Never compute or alter monetary amounts. Copy exact number strings.
- Dates should be normalized to 'aaj', 'kal', or 'parso'.
"""


class LedgerDomainPack(DomainPack):
    """Domain pack for Kirana shopkeeper credit/debit ledger."""

    name = "ledger"
    version = "1.0.0"
    system_prompt = LEDGER_SYSTEM_PROMPT_V1

    def __init__(self, customers: list[CustomerRecord] | None = None) -> None:
        self.resolver = CustomerResolver(customers or [])

    async def parse_rules(self, text: str) -> LedgerIntent | None:
        """Execute deterministic rule parser."""
        return parse_ledger_rules(text)

    def format_read_back(self, action: DomainAction) -> str:
        """
        Generate deterministic spoken confirmation phrase.
        Ensures amount and customer name are spoken clearly before persistence.
        """
        params = action.parameters
        act_type = action.action_type
        cust = params.get("customer") or params.get("customer_name") or "Grahak"
        amt = params.get("amount")
        amt_str = f"{int(amt) if amt and amt.is_integer() else amt}" if amt is not None else ""

        if act_type == "add_credit_sale":
            return f"{cust}, {amt_str} rupaye udhaar. Sahi hai?"
        elif act_type == "payment_received":
            return f"{cust} se {amt_str} rupaye jama hue. Sahi hai?"
        elif act_type == "cash_sale":
            return f"{amt_str} rupaye nagad bikri. Sahi hai?"
        elif act_type == "expense":
            items_str = ", ".join(params.get("items", [])) or "kharcha"
            return f"{items_str} {amt_str} rupaye. Likhein?"
        elif act_type == "query_balance":
            bal = params.get("balance", amt_str)
            return f"{cust} ka hisaab {bal} rupaye baaki hai."
        elif act_type == "query_today_udhaar":
            return "Aaj ka kul udhaar hisaab."
        elif act_type == "query_today_collection":
            return "Aaj ki kul vasooli hisaab."
        elif act_type == "query_top_debtors":
            return "Sabse zyada udhaar kiska hai."
        elif act_type == "query_last_payment":
            return f"{cust} ka aakhiri payment hisaab."
        elif act_type == "undo_last":
            return "Pichla hisaab cancel kiya gaya."
        return f"{act_type} confirm karein?"

    def create_action(self, intent: DomainIntent, **context: Any) -> DomainAction | None:
        """
        Instantiate executable DomainAction with deterministic idempotency key.
        """
        if not isinstance(intent, LedgerIntent):
            return None

        client_turn_id = context.get("client_turn_id", "default_turn")
        customer_id = context.get("customer_id", intent.customer or "unknown_cust")

        # Deterministic idempotency hash
        key_raw = f"{intent.name}:{customer_id}:{intent.amount}:{intent.date}:{client_turn_id}"
        idempotency_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]

        params: dict[str, Any] = {
            "customer": intent.customer,
            "customer_id": context.get("customer_id"),
            "amount": intent.amount,
            "currency": intent.currency,
            "items": intent.items,
            "quantity": intent.quantity,
            "unit": intent.unit,
            "date": intent.date,
            "payment_mode": intent.payment_mode,
            "provenance": intent.provenance,
        }

        # Query intents do not mutate ledger and do not strictly require confirmation
        requires_conf = not intent.name.startswith("query_")

        return DomainAction(
            action_type=intent.name,
            parameters=params,
            requires_confirmation=requires_conf,
            idempotency_key=idempotency_key,
        )
