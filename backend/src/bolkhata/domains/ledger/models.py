"""
Pydantic data models and schemas for the Kirana Ledger domain.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bolkhata.domains.base import DomainIntent

LedgerIntentName = Literal[
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
]


class LedgerIntent(DomainIntent):
    """Structured intent representation for Kirana ledger transactions."""

    name: LedgerIntentName
    customer: str | None = None
    amount: float | None = None
    currency: str = "INR"
    items: list[str] = Field(default_factory=list)
    quantity: float | None = None
    unit: str | None = None
    date: str | None = "aaj"
    payment_mode: str | None = "cash"
