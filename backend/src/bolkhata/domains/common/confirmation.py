"""
Confirmation and intent grammar for voice interactions.

Recognizes yes, no, cancel, stop, and correction cues across Hindi, English, and Hinglish.
Enforces the safety invariant:
Anything ambiguous or unclear leads to UNCLEAR (re-ask), never a default 'yes'.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from bolkhata.domains.common.numbers import extract_numbers


class ConfirmationType(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    CANCEL = "cancel"
    CORRECTION = "correction"
    UNCLEAR = "unclear"


class ConfirmationResult(BaseModel):
    confirmation_type: ConfirmationType
    confidence: float = 1.0
    detected_keywords: list[str] = Field(default_factory=list)
    raw_text: str
    is_correction: bool = False
    correction_field: Literal["amount", "customer", "date", "items", "general"] | None = None
    extracted_replacement: str | None = None


# Explicit uncertainty phrases that mean "I don't know" -> UNCLEAR
UNCERTAINTY_PATTERNS = [
    r"\b(?:pata\s*nahi|malum\s*nahi|samajh\s*nahi|idea\s*nahi|dont\s*know|not\s*sure)\b",
    r"(?:पता\s*नहीं|मालूम\s*नहीं|समझ\s*नहीं)",
]

# Exact and regex patterns for YES/CONFIRM
CONFIRM_PATTERNS = [
    r"^(?:haan|ha|haa|haji|ji\s*haan|sahi|sahi\s*hai|theek|theek\s*hai|thik|thik\s*hai|chalega|bilkul|kar\s*do|likh\s*do|likho|yes|yep|yeah|ok|okay|correct|confirm)$",
    r"\b(?:haan|ha|haa|haji|ji\s*haan|sahi\s*hai|theek\s*hai|thik\s*hai|yes|yep|yeah|correct|confirm)\b",
    r"^(?:हाँ|हा|हाँजी|जी\s*हाँ|सही|सही\s*है|ठीक|ठीक\s*है|बिल्कुल|कर\s*दो|लिख\s*दो|लिखो)$",
]

# Exact and regex patterns for NO/REJECT
REJECT_PATTERNS = [
    r"^(?:nahi|nahin|na|galat|galat\s*hai|no|nope|wrong|not\s*this)$",
    r"\b(?:galat|wrong)\b",
    r"^(?:नहीं|नही|ना|गलत|गलत\s*है)$",
]

# Exact and regex patterns for CANCEL/STOP
CANCEL_PATTERNS = [
    r"\b(?:ruko|rok|roko|cancel|cancel\s*karo|stop|chhod\s*do|mat\s*karo|mat\s*likho|rehne\s*do)\b",
    r"(?:रुको|रोक|रोको|रद्द|रद्द\s*करो|छोड़\s*दो|मत\s*लिखो|रहने\s*दो)",
]

# Correction indicator patterns ("nahi X nahi Y", "X nahi Y", "badal do", "X ki jagah Y")
CORRECTION_PATTERNS = [
    r"\b(?:nahi|nahin)\b.*?\b(?:nahi|nahin)\b",  # e.g. "nahi 300 nahi 350"
    r"\b\w+\s+nahi\s+\w+\b",  # e.g. "Sharma nahi Verma"
    r"\b(?:ki\s*jagah|badle|badal\s*do|customer|naam|taareekh|tarikh|date)\b",
    r"\b(?:kal|parso|aaj)\s+(?:ka|ko)\b",
]


def parse_confirmation_utterance(text: str) -> ConfirmationResult:
    """
    Parse a user utterance during the confirmation phase.

    Returns:
    - CONFIRM if explicit positive confirmation
    - REJECT if explicit negative rejection
    - CANCEL if stop/cancel command
    - CORRECTION if the utterance provides a patch/correction
    - UNCLEAR if ambiguous or unrecognized (must prompt re-ask)
    """
    clean_text = text.strip().lower()
    if not clean_text:
        return ConfirmationResult(
            confirmation_type=ConfirmationType.UNCLEAR,
            confidence=0.0,
            raw_text=text,
        )

    # 1. Check for Uncertainty phrases ("pata nahi", "malum nahi") -> UNCLEAR
    for pat in UNCERTAINTY_PATTERNS:
        if re.search(pat, clean_text, flags=re.IGNORECASE):
            return ConfirmationResult(
                confirmation_type=ConfirmationType.UNCLEAR,
                confidence=0.2,
                detected_keywords=["uncertainty"],
                raw_text=text,
            )

    # 2. Check for Stop / Cancel (highest safety precedence)
    for pat in CANCEL_PATTERNS:
        match = re.search(pat, clean_text, flags=re.IGNORECASE)
        if match:
            return ConfirmationResult(
                confirmation_type=ConfirmationType.CANCEL,
                confidence=0.98,
                detected_keywords=[match.group(0)],
                raw_text=text,
            )

    # 3. Check for standalone confirmation ("likh do", "haan", "theek hai")
    # If the user says an unambiguous confirmation phrase and does not mention a correction marker
    for pat in CONFIRM_PATTERNS:
        match = re.search(pat, clean_text, flags=re.IGNORECASE)
        if match and not any(
            re.search(cp, clean_text, flags=re.IGNORECASE) for cp in CORRECTION_PATTERNS
        ):
            return ConfirmationResult(
                confirmation_type=ConfirmationType.CONFIRM,
                confidence=0.95,
                detected_keywords=[match.group(0)],
                raw_text=text,
            )

    # 4. Check for standalone single-word rejection ("no", "nahi", "galat")
    for pat in REJECT_PATTERNS:
        if re.search(pat, clean_text, flags=re.IGNORECASE):
            return ConfirmationResult(
                confirmation_type=ConfirmationType.REJECT,
                confidence=0.95,
                detected_keywords=[clean_text],
                raw_text=text,
            )

    # 5. Check for Voice Correction
    has_correction_marker = False
    for pat in CORRECTION_PATTERNS:
        if re.search(pat, clean_text, flags=re.IGNORECASE):
            has_correction_marker = True
            break

    # If numbers or dates or customer keywords are mentioned with a correction intent
    numbers = []
    if clean_text != "no":
        numbers = extract_numbers(clean_text)

    has_date_phrase = bool(re.search(r"\b(?:kal|parso|aaj)\s+(?:ka|ko|likho)\b", clean_text))
    has_amount_change = bool(
        numbers and (has_correction_marker or "nahi" in clean_text or "rupaye" in clean_text)
    )

    if (
        has_correction_marker
        or has_amount_change
        or has_date_phrase
        or re.search(r"\b(?:nahi\s+\d+|nahi\s+[a-z]+)\b", clean_text)
    ):
        corr_field: Literal["amount", "customer", "date", "items", "general"] = "general"
        replacement_val: str | None = None

        if numbers and ("rupaye" in clean_text or "nahi" in clean_text or has_correction_marker):
            corr_field = "amount"
            replacement_val = str(numbers[-1].value)
        elif has_date_phrase or re.search(r"\b(?:kal|parso|aaj)\b", clean_text):
            corr_field = "date"
            d_m = re.search(r"\b(kal|parso|aaj)\b", clean_text)
            if d_m:
                replacement_val = d_m.group(1)
        elif (
            re.search(r"\b(?:customer|naam|ko|seth|ji|bhai)\b", clean_text)
            or re.search(r"\b\w+\s+nahi\s+\w+\b", clean_text)
            or ("nahi" in clean_text and any(c.isalpha() for c in clean_text))
        ):
            corr_field = "customer"

        return ConfirmationResult(
            confirmation_type=ConfirmationType.CORRECTION,
            confidence=0.95,
            raw_text=text,
            is_correction=True,
            correction_field=corr_field,
            extracted_replacement=replacement_val,
        )

    # 6. Default Safety Invariant: Any ambiguous phrase is UNCLEAR
    return ConfirmationResult(
        confirmation_type=ConfirmationType.UNCLEAR,
        confidence=0.3,
        raw_text=text,
    )
