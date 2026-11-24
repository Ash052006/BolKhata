"""
Unit tests for the hierarchical extraction pipeline in the Kirana ledger domain.

Verifies:
- Rules run first and provide 100% provenance
- LLM structured extraction fallback for unstructured queries
- Field-level provenance merging ('rules' vs 'llm')
- Money safety invariant: LLM cannot hallucinate or override parsed numbers
"""

from collections.abc import AsyncIterator, Sequence
from typing import TypeVar

import pytest
from pydantic import BaseModel

from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.pipeline import extract_ledger_intent
from bolkhata.llm.base import ChatMessage, LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMExtractionProvider(LLMProvider):
    """Mock LLM providing canned structured extraction responses."""

    def __init__(self, canned_intent: LedgerIntent | None = None) -> None:
        self.canned_intent = canned_intent or LedgerIntent(
            name="add_credit_sale",
            customer="Rakesh",
            amount=450.0,
            items=["dal", "chini"],
            date="aaj",
        )
        self.call_count: int = 0

    async def initialize(self) -> None:
        pass

    async def warmup(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        yield "canned"

    async def complete_structured(
        self, messages: Sequence[ChatMessage], response_model: type[T]
    ) -> T:
        self.call_count += 1
        return self.canned_intent  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_pipeline_prefers_rules_first() -> None:
    # A query that rule parser can resolve completely
    text = "Ramesh ji ko dhai sau rupaye udhaar likho"
    mock_llm = MockLLMExtractionProvider()

    intent = await extract_ledger_intent(text, mock_llm)
    assert intent.name == "add_credit_sale"
    assert intent.amount == 250.0
    assert intent.customer == "Ramesh"
    # LLM should NOT have been called because rules resolved completely
    assert mock_llm.call_count == 0
    assert intent.provenance["intent"] == "rules"
    assert intent.provenance["amount"] == "rules"


@pytest.mark.asyncio
async def test_pipeline_llm_fallback_for_unstructured_query() -> None:
    # An unusual/unstructured query where rule regex does not match intent keywords
    text = "arre bhai Rakesh ka khata dekho unhe dal aur chini diya tha chaar sau pachaas ka"
    mock_llm = MockLLMExtractionProvider(
        canned_intent=LedgerIntent(
            name="add_credit_sale",
            customer="Rakesh",
            amount=450.0,
            items=["dal", "chini"],
            date="aaj",
        )
    )

    intent = await extract_ledger_intent(text, mock_llm)
    assert intent.name == "add_credit_sale"
    assert intent.customer == "Rakesh"
    assert intent.amount == 450.0
    # Rule parser did find the number "chaar sau pachaas" (450.0)
    assert intent.provenance["amount"] == "rules"
    # Intent and items came from LLM
    assert mock_llm.call_count == 1


@pytest.mark.asyncio
async def test_money_safety_invariant_rule_overrides_llm_amount() -> None:
    # Invariant: If rules found an amount from the text, LLM can NEVER hallucinate a different amount
    text = "Suresh ko teen sau pachaas rupaye likh do"  # exactly 350
    # LLM hallucinates 500
    mock_llm = MockLLMExtractionProvider(
        canned_intent=LedgerIntent(
            name="add_credit_sale",
            customer="Suresh",
            amount=500.0,  # Hallucinated amount!
        )
    )

    intent = await extract_ledger_intent(text, mock_llm)
    # Must use deterministic parsed amount (350), NOT hallucinated LLM amount (500)
    assert intent.amount == 350.0
    assert intent.provenance["amount"] == "rules"
