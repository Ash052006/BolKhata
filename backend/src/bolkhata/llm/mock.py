"""
Deterministic Mock LLM provider for offline testing and CI.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from bolkhata.llm.base import ChatMessage, LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM provider.

    Returns configured token streams and pre-configured structured output fixtures.
    Does not make external network requests or load local weights.
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

        # 2. Attempt zero-arg instantiation (models with all default fields)
        try:
            return response_model()
        except Exception:
            pass

        # 3. Build a mock instance with mock values for required fields
        dummy_data: dict[str, Any] = {}
        for field_name, field_info in response_model.model_fields.items():
            if field_info.is_required():
                ann = field_info.annotation
                if ann is not None and isinstance(ann, type):
                    if issubclass(ann, str):
                        dummy_data[field_name] = "mock_value"
                    elif issubclass(ann, bool):
                        dummy_data[field_name] = True
                    elif issubclass(ann, int):
                        dummy_data[field_name] = 1
                    elif issubclass(ann, float):
                        dummy_data[field_name] = 1.0
                    else:
                        dummy_data[field_name] = None
                else:
                    dummy_data[field_name] = "mock_value"

        return response_model.model_validate(dummy_data)

    async def shutdown(self) -> None:
        self.shutdown_calls += 1
        self.is_initialized = False
        self.is_shutdown = True
