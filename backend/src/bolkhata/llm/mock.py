"""
Deterministic Mock LLM provider for offline testing and CI.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import TypeVar

from pydantic import BaseModel

from bolkhata.llm.base import ChatMessage, LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockFixtureMissingError(ValueError):
    """Raised when a mock structured response is requested for a model with required fields but no fixture was registered."""


class MockFixtureTypeMismatchError(TypeError):
    """Raised when a registered fixture does not match the requested response model type."""


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM provider.

    Returns configured token streams and pre-configured structured output fixtures.
    Does not make external network requests, load local weights, or fabricate
    arbitrary required field values or financial amounts.
    """

    def __init__(
        self,
        canned_tokens: list[str] | None = None,
        structured_fixtures: dict[type[BaseModel], BaseModel] | None = None,
    ) -> None:
        if canned_tokens is None:
            self.canned_tokens = [
                "Sharma ji, ",
                "do sau pachaas rupaye ",
                "udhaar. ",
                "Sahi hai?",
            ]
        else:
            self.canned_tokens = canned_tokens

        self.structured_fixtures: dict[type[BaseModel], BaseModel] = (
            structured_fixtures if structured_fixtures is not None else {}
        )

        self.initialize_calls: int = 0
        self.warmup_calls: int = 0
        self.shutdown_calls: int = 0
        self.stream_chat_calls: int = 0
        self.structured_calls: int = 0
        self.is_initialized: bool = False
        self.is_warmed_up: bool = False
        self.is_shutdown: bool = False

    async def initialize(self) -> None:
        self.initialize_calls += 1
        self.is_initialized = True
        self.is_shutdown = False

    async def warmup(self) -> None:
        self.warmup_calls += 1
        self.is_warmed_up = True

    async def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        self.stream_chat_calls += 1
        for token in self.canned_tokens:
            await asyncio.sleep(0)
            yield token

    async def complete_structured(
        self, messages: Sequence[ChatMessage], response_model: type[T]
    ) -> T:
        self.structured_calls += 1
        await asyncio.sleep(0)

        # 1. Check if an explicit fixture was registered for this model type
        if response_model in self.structured_fixtures:
            fixture = self.structured_fixtures[response_model]
            if isinstance(fixture, response_model):
                return fixture
            raise MockFixtureTypeMismatchError(
                f"Fixture registered for {response_model.__name__} is of type {type(fixture).__name__}, "
                f"expected an instance of {response_model.__name__}."
            )

        # 2. Allow zero-argument construction only when the model can be instantiated with its defaults
        try:
            return response_model()
        except Exception as exc:
            # 3. Fail closed if required fields are missing: never synthesize numbers or text
            raise MockFixtureMissingError(
                f"Cannot instantiate structured output model '{response_model.__name__}': "
                "it has required fields and no deterministic fixture was registered in MockLLMProvider. "
                "Tests must explicitly register fixtures via structured_fixtures={Model: fixture_instance}."
            ) from exc

    async def shutdown(self) -> None:
        self.shutdown_calls += 1
        self.is_initialized = False
        self.is_shutdown = True
