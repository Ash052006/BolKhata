"""
LLM package contracts and mock implementation.
"""

from __future__ import annotations

from bolkhata.llm.base import ChatMessage, ChatRole, LLMProvider, LLMResponse
from bolkhata.llm.mock import MockLLMProvider

__all__ = [
    "ChatMessage",
    "ChatRole",
    "LLMProvider",
    "LLMResponse",
    "MockLLMProvider",
]
