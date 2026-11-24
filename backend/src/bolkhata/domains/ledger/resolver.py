"""
Customer entity resolver for Kirana retail.

Implements:
- Honorific and suffix stripping (ji, bhai, uncle, aunty, sahab, seth)
- Fuzzy and phonetic similarity across Roman and Devanagari representations
- Exact match, high-confidence match (>= 0.85), gray-zone ambiguity ([0.65, 0.85)),
  and new customer proposal (< 0.65).
- Prevents silent merging of distinct customers.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from bolkhata.domains.base import (
    EntityResolver,
    ResolutionCandidate,
    ResolutionResult,
)

HONORIFICS = {
    "ji",
    "jee",
    "जी",
    "bhai",
    "bhaiya",
    "भाई",
    "भैया",
    "uncle",
    "अंकल",
    "aunty",
    "आंटी",
    "sahab",
    "saab",
    "sahib",
    "साहब",
    "seth",
    "सेठ",
    "bhabhi",
    "भाभी",
    "babuji",
    "बाबूजी",
    "sir",
    "madam",
}

# Devanagari to Roman common phonetic mapping for cross-script matching
DEVANAGARI_ROMAN_APPROX = {
    "रमेश": "ramesh",
    "सुरेश": "suresh",
    "महेश": "mahesh",
    "शर्मा": "sharma",
    "वर्मा": "verma",
    "गुप्ता": "gupta",
    "यादव": "yadav",
    "मिश्रा": "mishra",
    "पांडे": "pandey",
    "सिंह": "singh",
    "चौधरी": "chaudhary",
    "अग्रवाल": "agarwal",
}


def normalize_customer_name(name: str) -> str:
    """Strip honorifics, punctuation, and lowercase with cross-script mapping."""
    cleaned = unicodedata.normalize("NFC", name.strip().lower())
    tokens = re.split(r"[\s\.,]+", cleaned)
    filtered = [t for t in tokens if t and t not in HONORIFICS]
    mapped_tokens = [DEVANAGARI_ROMAN_APPROX.get(t, t) for t in filtered]
    return " ".join(mapped_tokens)


@dataclass
class CustomerRecord:
    id: str
    name: str
    phone: str | None = None


class CustomerResolver(EntityResolver):
    """Fuzzy customer name resolver with explicit gray-zone reporting."""

    def __init__(self, customers: list[CustomerRecord] | None = None) -> None:
        self.customers: list[CustomerRecord] = customers or []

    def set_customers(self, customers: list[CustomerRecord]) -> None:
        """Update active customer pool."""
        self.customers = list(customers)

    async def resolve(self, query: str, **kwargs: Any) -> ResolutionResult:
        """
        Resolve spoken customer name string against stored customer records.

        Thresholds:
        - Score >= 0.85: Resolved to existing customer
        - 0.65 <= Score < 0.85: Gray zone (ambiguous, return candidates)
        - Score < 0.65: Proposed as new customer
        """
        clean_query = normalize_customer_name(query)
        if not clean_query:
            return ResolutionResult(is_resolved=False, is_ambiguous=False, is_new=False)

        scored_candidates: list[ResolutionCandidate] = []

        for cust in self.customers:
            cust_norm = normalize_customer_name(cust.name)
            # Exact normalized match
            if clean_query == cust_norm:
                return ResolutionResult(
                    is_resolved=True,
                    resolved_id=cust.id,
                    resolved_name=cust.name,
                    is_ambiguous=False,
                    candidates=[ResolutionCandidate(id=cust.id, name=cust.name, score=1.0)],
                )

            # RapidFuzz similarity ratio (0 to 100 -> 0.0 to 1.0)
            score = fuzz.ratio(clean_query, cust_norm) / 100.0

            # If query is a single name token matching first or last name (e.g. 'suresh' for 'suresh verma')
            query_tokens = clean_query.split()
            cust_tokens = cust_norm.split()
            if len(query_tokens) == 1 and query_tokens[0] in cust_tokens:
                score = max(score, 0.90)

            if score >= 0.65:
                scored_candidates.append(
                    ResolutionCandidate(
                        id=cust.id,
                        name=cust.name,
                        score=score,
                        metadata={"phone": cust.phone} if cust.phone else {},
                    )
                )

        scored_candidates.sort(key=lambda c: c.score, reverse=True)

        if not scored_candidates:
            # Below 0.65 -> Propose new customer
            return ResolutionResult(
                is_resolved=False,
                is_ambiguous=False,
                is_new=True,
                resolved_name=query.strip(),
                candidates=[],
            )

        top = scored_candidates[0]

        # Check if there is ambiguity between top two candidates (e.g. score difference < 0.08)
        if len(scored_candidates) > 1:
            diff = top.score - scored_candidates[1].score
            if diff < 0.08 and top.score < 0.98:
                # Close candidates -> report ambiguous gray zone
                return ResolutionResult(
                    is_resolved=False,
                    is_ambiguous=True,
                    is_new=False,
                    candidates=scored_candidates[:3],
                )

        if top.score >= 0.85:
            return ResolutionResult(
                is_resolved=True,
                resolved_id=top.id,
                resolved_name=top.name,
                is_ambiguous=False,
                candidates=scored_candidates[:1],
            )
        else:
            # Gray zone [0.65, 0.85) -> report ambiguity
            return ResolutionResult(
                is_resolved=False,
                is_ambiguous=True,
                is_new=False,
                candidates=scored_candidates,
            )
