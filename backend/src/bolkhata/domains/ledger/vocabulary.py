"""
Vocabulary biasing and post-ASR near-miss token correction for the ledger domain.

Implements Prompt F1:
- VocabularyProvider: generates concise, weighted initial_prompt hints from frequent
  customer and commodity names.
- Hard size limits to prevent hallucination or latency degradation.
- Post-ASR token correction with provenance recording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from bolkhata.domains.ledger.resolver import normalize_customer_name

# Standard Kirana commodity terms in Roman and Devanagari
COMMON_COMMODITIES = [
    "chawal",
    "atta",
    "cheeni",
    "shakkar",
    "tel",
    "sarson tel",
    "dal",
    "toor dal",
    "moong dal",
    "doodh",
    "dahi",
    "makhan",
    "ghee",
    "namak",
    "mirch",
    "haldi",
    "dhaniya",
    "jeera",
    "chaap",
    "biscuit",
    "sabun",
    "surf",
    "paste",
    "brush",
    "bread",
    "ande",
    "chai patti",
    "चावल",
    "आटा",
    "चीनी",
    "शक्कर",
    "तेल",
    "दाल",
    "दूध",
    "दही",
    "मक्खन",
    "घी",
    "नमक",
    "बिस्कुट",
    "साबुन",
]


@dataclass
class VocabularyItem:
    """A weighted vocabulary entry."""

    term: str
    category: str  # "customer" | "item"
    frequency: int = 1
    recency_rank: int = 1  # 1 is most recent


class VocabularyProvider:
    """
    Manages customer and item vocabulary hints for ASR prefix conditioning
    and post-ASR phonetic/fuzzy token correction.
    """

    def __init__(
        self,
        customer_names: list[str] | None = None,
        item_names: list[str] | None = None,
        enabled: bool = True,
        max_prompt_chars: int = 250,
    ) -> None:
        self.enabled = enabled
        self.max_prompt_chars = max_prompt_chars
        self._customers: list[str] = list(customer_names or [])
        self._items: list[str] = list(item_names or COMMON_COMMODITIES)

    def add_customer(self, name: str) -> None:
        """Add or bump customer recency."""
        clean = name.strip()
        if clean and clean not in self._customers:
            self._customers.insert(0, clean)

    def add_item(self, item: str) -> None:
        """Add or bump item recency."""
        clean = item.strip().lower()
        if clean and clean not in self._items:
            self._items.insert(0, clean)

    def get_initial_prompt(self) -> str | None:
        """
        Generate a comma-separated vocabulary prompt for Whisper prefix conditioning.

        Returns None if biasing is disabled or vocabulary is empty.
        Enforces a hard character limit to avoid hallucination or GPU cache bloat.
        """
        if not self.enabled:
            return None

        # Blend top customers and frequent commodities
        terms: list[str] = []
        # Customers first (top 10)
        for cust in self._customers[:10]:
            if cust and cust not in terms:
                terms.append(cust)

        # Items next (top 15)
        for it in self._items[:15]:
            if it and it not in terms:
                terms.append(it.title())

        if not terms:
            return None

        prompt_str = ", ".join(terms)
        if len(prompt_str) > self.max_prompt_chars:
            # Truncate cleanly at a comma boundary
            truncated = prompt_str[: self.max_prompt_chars]
            last_comma = truncated.rfind(",")
            if last_comma > 0:
                prompt_str = truncated[:last_comma]
            else:
                prompt_str = truncated

        return prompt_str

    def correct_tokens(
        self,
        text: str,
        similarity_threshold: float = 0.88,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Post-ASR near-miss token correction for known customers and commodities.

        Only substitutes tokens with >= similarity_threshold similarity.
        Records exact provenance for auditability.
        """
        if not self.enabled or not text.strip():
            return text, []

        corrections: list[dict[str, Any]] = []
        tokens = text.split()
        modified = False

        known_targets: list[tuple[str, str, str]] = []
        # (normalized_target, display_target, category)
        for c in self._customers:
            norm = normalize_customer_name(c)
            if norm:
                known_targets.append((norm, c, "customer"))

        for it in self._items:
            norm = it.strip().lower()
            if norm:
                known_targets.append((norm, it, "item"))

        # Single-token check
        new_tokens = list(tokens)
        for i, tok in enumerate(tokens):
            clean_tok = re.sub(r"[^\w\s]", "", tok).lower()
            if not clean_tok or len(clean_tok) < 3:
                continue

            # Don't correct pure digits or common stop words
            if clean_tok.isdigit() or clean_tok in {
                "hai",
                "ko",
                "ka",
                "ki",
                "aur",
                "and",
                "rs",
                "rupaye",
            }:
                continue

            best_match: tuple[str, str, str] | None = None
            best_score: float = 0.0

            for norm_target, display_target, cat in known_targets:
                # Use token sort ratio
                score = fuzz.ratio(clean_tok, norm_target) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = (norm_target, display_target, cat)

            if best_match and best_score >= similarity_threshold and best_score < 1.0:
                orig = tokens[i]
                corrected = best_match[1]
                new_tokens[i] = corrected
                corrections.append(
                    {
                        "original": orig,
                        "corrected": corrected,
                        "category": best_match[2],
                        "similarity": round(best_score, 3),
                        "provenance": "rules_vocabulary_bias",
                    }
                )
                modified = True

        corrected_text = " ".join(new_tokens) if modified else text
        return corrected_text, corrections
