"""
ASR text normalizer supporting strict and transliteration-tolerant modes.

Applies deterministic transformations to both reference and hypothesis transcripts
for reproducible error metric calculation (WER/CER).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

# Punctuation to remove: ASCII punctuation + Unicode quotes + Indic danda
PUNCTUATION_PATTERN = re.compile(r"[\.,;:!\?\-_/\"\'\(\)\[\]\{\}«»“”‘’`~@#\$%\^&\*\+=\|\<\>\\।॥]")

# Devanagari numerals to standard ASCII digits
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Devanagari nukta replacements for tolerant comparison
DEVANAGARI_PRECOMPOSED_NUKTA_MAP = str.maketrans(
    {
        "\u0958": "\u0915",  # क़ -> क
        "\u0959": "\u0916",  # ख़ -> ख
        "\u095a": "\u0917",  # ग़ -> ग
        "\u095b": "\u091c",  # ज़ -> ज
        "\u095c": "\u0921",  # ड़ -> ड
        "\u095d": "\u0922",  # ढ़ -> ढ
        "\u095e": "\u092b",  # फ़ -> फ
    }
)

# Common Hinglish phonetic spelling equivalence dictionary for tolerant mode
TOLERANT_HINGLISH_MAP: dict[str, str] = {
    # Numbers & Multipliers
    "paanch": "panch",
    "paan": "panch",
    "chaar": "char",
    "saat": "sat",
    "aath": "ath",
    "chhe": "che",
    "chheh": "che",
    "das": "dus",
    "duss": "dus",
    "gyaarah": "gyarah",
    "baarah": "barah",
    "chaudah": "choudah",
    "pandrah": "pandra",
    "unnees": "unnis",
    "ikkees": "ikkis",
    "baais": "bais",
    "teyees": "teis",
    "chaubees": "chaubis",
    "pachees": "pachis",
    "pachhees": "pachis",
    "chhabbees": "chabbis",
    "sattaais": "sattais",
    "atthaais": "tthais",
    "untees": "untis",
    "chaalees": "chalis",
    "pachaas": "pachas",
    "assee": "assi",
    "nabbe": "nabbey",
    "hazaar": "hazar",
    "sau": "sau",
    "lakh": "lac",
    # Fractional words
    "dhaai": "dhai",
    "deedh": "dedh",
    "derh": "dedh",
    "saadhe": "sadhe",
    "paun": "paune",
    # Currency words
    "rupee": "rupaye",
    "rupees": "rupaye",
    "rupaya": "rupaye",
    "rupay": "rupaye",
    "rs": "rupaye",
    "₹": "rupaye",
    "inr": "rupaye",
    # Units
    "kgs": "kg",
    "kilos": "kilo",
    "kilogram": "kg",
    "kilograms": "kg",
    "grams": "gram",
    "gm": "gram",
    "gms": "gram",
    "litres": "litre",
    "liter": "litre",
    "liters": "litre",
    "ltr": "litre",
    "ltrs": "litre",
    "darzan": "darjan",
    "dozens": "dozen",
    "packets": "packet",
    "pkts": "packet",
    "pkt": "packet",
    "boriyaan": "bori",
    "boriyan": "bori",
    "theli": "thaili",
    "dibba": "dabba",
    "dabbe": "dabba",
    # Common conversational fillers
    "aur": "aur",
    "ji": "ji",
    "ko": "ko",
    "ka": "ka",
    "ki": "ki",
    "ke": "ke",
    "se": "se",
    "hai": "hai",
    "hain": "hai",
}


def normalize_text(text: str, mode: Literal["strict", "tolerant"] = "strict") -> str:
    """
    Normalize reference or hypothesis transcript text.

    Args:
        text: Input string.
        mode:
            - 'strict': Lowercases, strips punctuation and Indic dandas, collapses whitespace.
            - 'tolerant': Strict normalization plus Devanagari digit mapping, nukta unification,
              and Hinglish phonetic spelling regularization.
    """
    if not text:
        return ""

    # Unicode normalization (NFC)
    cleaned = unicodedata.normalize("NFC", text.strip())

    # Lowercase
    cleaned = cleaned.lower()

    # Strip punctuation
    cleaned = PUNCTUATION_PATTERN.sub(" ", cleaned)

    if mode == "tolerant":
        # Map Devanagari digits to ASCII digits
        cleaned = cleaned.translate(DEVANAGARI_DIGITS)
        # Normalize Devanagari nuktas (both precomposed and combining character)
        cleaned = cleaned.translate(DEVANAGARI_PRECOMPOSED_NUKTA_MAP).replace("\u093c", "")

        # Word-level phonetic regularization
        tokens = cleaned.split()
        normalized_tokens: list[str] = []
        for t in tokens:
            normalized_tokens.append(TOLERANT_HINGLISH_MAP.get(t, t))
        cleaned = " ".join(normalized_tokens)

    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned
