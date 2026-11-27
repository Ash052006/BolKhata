"""
Registry for multilingual spoken number parsers.
Enables pluggable resolution of language-specific parsers based on session language.
"""

from __future__ import annotations

from typing import ClassVar

from bolkhata.domains.common.bengali_numbers import BengaliNumberParser
from bolkhata.domains.common.number_parser_interface import NumberParser
from bolkhata.domains.common.number_words import (
    number_to_english_words,
    number_to_hindi_words,
)
from bolkhata.domains.common.numbers import (
    ParsedNumber,
)
from bolkhata.domains.common.numbers import (
    extract_numbers as extract_hindi_numbers,
)
from bolkhata.domains.common.numbers import (
    parse_spoken_number as parse_hindi_number,
)


class HindiNumberParser:
    """Default Hindi/Hinglish/English Spoken Number Parser."""

    @property
    def language_code(self) -> str:
        return "hi"

    def parse_spoken_number(self, text: str) -> float | None:
        return parse_hindi_number(text)

    def extract_numbers(self, text: str) -> list[ParsedNumber]:
        return extract_hindi_numbers(text)

    def number_to_words(self, number: int | float, script: str = "native") -> str:
        if script == "english":
            return number_to_english_words(number)
        use_dev = script in ("native", "devanagari")
        return number_to_hindi_words(number, devanagari=use_dev)


class NumberParserRegistry:
    """Thread-safe registry for language-specific number parsers."""

    _parsers: ClassVar[dict[str, NumberParser]] = {
        "hi": HindiNumberParser(),
        "en": HindiNumberParser(),
        "bn": BengaliNumberParser(),
    }

    @classmethod
    def get(cls, language_code: str = "hi") -> NumberParser:
        """Get the parser for the requested language code, defaulting to Hindi."""
        code = language_code.lower().strip()
        return cls._parsers.get(code, cls._parsers["hi"])

    @classmethod
    def register(cls, parser: NumberParser) -> None:
        """Register a new language number parser."""
        cls._parsers[parser.language_code.lower()] = parser
