"""
DomainPack framework core abstractions and protocols.

Defines the pluggable interface between the speech pipeline and business domain packs.
Enforces domain isolation so core ASR/TTS/WebSocket pipelines remain 100% domain-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

ProvenanceSource = Literal["rules", "llm", "default"]


class EntityProvenance(BaseModel):
    """Provenance tracking showing whether each extracted field came from rules or LLM."""

    sources: dict[str, ProvenanceSource] = Field(default_factory=dict)


class DomainIntent(BaseModel):
    """Base model for extracted domain intent and entities."""

    name: str
    confidence: float = 1.0
    provenance: dict[str, str] = Field(default_factory=dict)
    is_ambiguous: bool = False
    ambiguity_details: list[str] = Field(default_factory=list)


class DomainAction(BaseModel):
    """An executable domain action proposed by intent parsing or extraction."""

    action_type: str
    parameters: dict[str, Any]
    requires_confirmation: bool = True
    idempotency_key: str


class ResolutionCandidate(BaseModel):
    """A matched entity candidate with a confidence score."""

    id: str
    name: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolutionResult(BaseModel):
    """Result of entity resolution (e.g. customer name disambiguation)."""

    is_resolved: bool
    resolved_id: str | None = None
    resolved_name: str | None = None
    is_ambiguous: bool = False
    is_new: bool = False
    candidates: list[ResolutionCandidate] = Field(default_factory=list)


@runtime_checkable
class EntityResolver(Protocol):
    """Protocol for resolving spoken entity strings to stored database records."""

    async def resolve(self, query: str, **kwargs: Any) -> ResolutionResult:
        """Resolve entity name/string to unique ID or candidate list."""
        ...


class DomainPack(ABC):
    """
    Abstract base class for a pluggable Domain Pack.

    Encapsulates:
    - Intent definitions and Pydantic schemas
    - Rule-based parser
    - Versioned LLM system prompt
    - Entity resolver
    - Deterministic read-back generator
    - Action factory with idempotency keys
    """

    name: str
    version: str
    system_prompt: str

    @abstractmethod
    async def parse_rules(self, text: str) -> DomainIntent | None:
        """Attempt deterministic rule-based extraction on utterance text."""
        ...

    @abstractmethod
    def format_read_back(self, action: DomainAction) -> str:
        """Format an action into a deterministic spoken/visual confirmation string."""
        ...

    @abstractmethod
    def create_action(self, intent: DomainIntent, **context: Any) -> DomainAction | None:
        """Convert a parsed intent into an executable DomainAction with idempotency key."""
        ...
