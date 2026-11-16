"""
LLM provider interfaces, typed message schemas, and structured output contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    """Typed chat message for conversational completion."""

    role: ChatRole
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """Full assistant response with token metrics."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """
    Abstract interface for Language Model providers.

    Architectural constraint:
      The LLM must NEVER compute, calculate, or decide financial ledger
      amounts. Ledger values and arithmetic are handled by deterministic domain
      parsers and database engines.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize client sessions or verify connectivity. Idempotent."""
        pass

    @abstractmethod
    async def warmup(self) -> None:
        """Prime connections or model context."""
        pass

    @abstractmethod
    def stream_chat(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        """Stream response tokens as they are generated."""
        pass

    @abstractmethod
    async def complete_structured(
        self, messages: Sequence[ChatMessage], response_model: type[T]
    ) -> T:
        """Complete structured output validated against a Pydantic schema."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Close client sessions cleanly. Idempotent."""
        pass
