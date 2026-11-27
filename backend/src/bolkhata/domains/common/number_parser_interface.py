"""
Abstract interface and protocol for multilingual spoken number parsing.
Enables pluggable, deterministic language parsers (Hindi, Bengali, English, etc.)
without altering downstream domain pipelines.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bolkhata.domains.common.numbers import ParsedNumber


@runtime_checkable
class NumberParser(Protocol):
    """Protocol for language-specific spoken number parsers."""

    @property
    def language_code(self) -> str:
        """ISO 639-1 language code (e.g. 'hi', 'bn', 'en')."""
        ...

    def parse_spoken_number(self, text: str) -> float | None:
        """Parse spoken or written text into a numeric float/int, or None."""
        ...

    def extract_numbers(self, text: str) -> list[ParsedNumber]:
        """Extract all candidate numbers from the input string with span metadata."""
        ...

    def number_to_words(self, number: int | float, script: str = "native") -> str:
        """Convert a numeric value to deterministic spoken words in this language."""
        ...
