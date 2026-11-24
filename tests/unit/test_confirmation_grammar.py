"""
Unit tests for confirmation grammar across Hindi, English, and Hinglish.
Verifies YES, NO, CANCEL, CORRECTION, and ambiguous UNCLEAR behaviors.
"""

from __future__ import annotations

import pytest

from bolkhata.domains.common.confirmation import (
    ConfirmationType,
    parse_confirmation_utterance,
)


@pytest.mark.parametrize(
    "text",
    [
        "haan",
        "haa",
        "ha",
        "ji haan",
        "sahi hai",
        "theek hai",
        "thik hai",
        "bilkul",
        "likh do",
        "yes",
        "yep",
        "okay",
        "correct",
        "हाँ",
        "जी हाँ",
        "सही है",
        "ठीक है",
        "लिख दो",
    ],
)
def test_parse_confirmation_positive(text: str) -> None:
    res = parse_confirmation_utterance(text)
    assert res.confirmation_type == ConfirmationType.CONFIRM
    assert res.confidence >= 0.90


@pytest.mark.parametrize(
    "text",
    [
        "nahi",
        "nahin",
        "na",
        "galat",
        "galat hai",
        "no",
        "nope",
        "wrong",
        "नहीं",
        "गलत",
        "गलत है",
    ],
)
def test_parse_confirmation_negative(text: str) -> None:
    res = parse_confirmation_utterance(text)
    assert res.confirmation_type == ConfirmationType.REJECT
    assert res.confidence >= 0.90


@pytest.mark.parametrize(
    "text",
    [
        "ruko",
        "stop",
        "cancel",
        "cancel karo",
        "mat likho",
        "chhod do",
        "rehne do",
        "रुको",
        "रद्द करो",
        "मत लिखो",
    ],
)
def test_parse_confirmation_cancel(text: str) -> None:
    res = parse_confirmation_utterance(text)
    assert res.confirmation_type == ConfirmationType.CANCEL
    assert res.confidence >= 0.90


@pytest.mark.parametrize(
    ("text", "expected_field"),
    [
        ("nahi teen sau nahi, teen sau pachaas", "amount"),
        ("nahi 500 rupaye", "amount"),
        ("customer Verma ji hai", "customer"),
        ("Sharma nahi Verma", "customer"),
        ("kal ka likho", "date"),
    ],
)
def test_parse_confirmation_correction(text: str, expected_field: str) -> None:
    res = parse_confirmation_utterance(text)
    assert res.confirmation_type == ConfirmationType.CORRECTION
    assert res.is_correction is True
    assert res.correction_field == expected_field


@pytest.mark.parametrize(
    "text",
    [
        "pata nahi",
        "kya bola aapne",
        "ek second",
        "chai lao",
        "hmm",
        "",
        "asdfghjk",
    ],
)
def test_parse_confirmation_unclear_safety_invariant(text: str) -> None:
    """Anything ambiguous or non-committal must lead to UNCLEAR (re-ask), never default to yes."""
    res = parse_confirmation_utterance(text)
    assert res.confirmation_type == ConfirmationType.UNCLEAR
    assert res.confidence < 0.5
