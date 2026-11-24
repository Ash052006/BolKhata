"""
Unit tests for deterministic number-to-words conversions (Hindi Roman, Devanagari, English).
"""

from __future__ import annotations

import pytest

from bolkhata.domains.common.number_words import (
    number_to_digits_spoken,
    number_to_english_words,
    number_to_hindi_words,
)


@pytest.mark.parametrize(
    ("val", "expected_roman", "expected_dev"),
    [
        (0, "shunya", "शून्य"),
        (1, "ek", "एक"),
        (5, "panch", "पांच"),
        (15, "pandrah", "पंद्रह"),
        (25, "pachchis", "पच्चीस"),
        (50, "pachaas", "पचास"),
        (99, "ninyanwe", "निन्यानवे"),
        (100, "ek sau", "एक सौ"),
        (250, "do sau pachaas", "दो सौ पचास"),
        (350, "teen sau pachaas", "तीन सौ पचास"),
        (1000, "ek hazaar", "एक हज़ार"),
        (1500, "ek hazaar panch sau", "एक हज़ार पांच सौ"),
        (2500, "do hazaar panch sau", "दो हज़ार पांच सौ"),
        (10000, "das hazaar", "दस हज़ार"),
        (12500, "barah hazaar panch sau", "बारह हज़ार पांच सौ"),
        (100000, "ek lakh", "एक लाख"),
        (250000, "do lakh pachaas hazaar", "दो लाख पचास हज़ार"),
        (10000000, "ek crore", "एक करोड़"),
    ],
)
def test_number_to_hindi_words_integers(val: int, expected_roman: str, expected_dev: str) -> None:
    assert number_to_hindi_words(val, devanagari=False) == expected_roman
    assert number_to_hindi_words(val, devanagari=True) == expected_dev


def test_number_to_hindi_words_decimals() -> None:
    assert number_to_hindi_words(350.50, devanagari=False) == "teen sau pachaas pachaas paise"
    assert number_to_hindi_words(350.50, devanagari=True) == "तीन सौ पचास पचास पैसे"
    assert number_to_hindi_words(0.25, devanagari=False) == "pachchis paise"


@pytest.mark.parametrize(
    ("val", "expected_english"),
    [
        (0, "zero"),
        (15, "fifteen"),
        (25, "twenty five"),
        (100, "one hundred"),
        (350, "three hundred fifty"),
        (1500, "one thousand five hundred"),
        (12500, "twelve thousand five hundred"),
        (100000, "one lakh"),
        (350.50, "three hundred fifty and fifty paise"),
    ],
)
def test_number_to_english_words(val: int | float, expected_english: str) -> None:
    assert number_to_english_words(val) == expected_english


def test_number_to_digits_spoken() -> None:
    digits_roman = number_to_digits_spoken(12500, devanagari=False)
    assert digits_roman == "ek do panch shunya shunya"

    digits_dev = number_to_digits_spoken(12500, devanagari=True)
    assert digits_dev == "एक दो पांच शून्य शून्य"
