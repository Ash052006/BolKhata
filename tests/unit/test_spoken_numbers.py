"""Unit tests for deterministic spoken number parsing across Hindi, English, and Hinglish."""

import pytest

from bolkhata.domains.common.numbers import (
    extract_numbers,
    parse_spoken_number,
)


@pytest.mark.parametrize(
    ("input_text", "expected_val"),
    [
        # Exact examples specified in task requirements:
        ("dhai sau", 250.0),
        ("derh hazaar", 1500.0),
        ("sawa sau", 125.0),
        ("sadhe teen sau", 350.0),
        ("paune do sau", 175.0),
        # Devanagari variants of prompt required examples:
        ("ढाई सौ", 250.0),
        ("डेढ़ हज़ार", 1500.0),
        ("सवा सौ", 125.0),
        ("साढ़े तीन सौ", 350.0),
        ("पौने दो सौ", 175.0),
        # Fractional multipliers and idioms:
        ("dedh sau", 150.0),
        ("dhaai hazaar", 2500.0),
        ("sawa do sau", 225.0),
        ("sawa hazaar", 1250.0),
        ("sadhe char sau", 450.0),
        ("sadhe teen hazaar", 3500.0),
        ("paune sau", 75.0),
        ("paune do hazaar", 1750.0),
        # Standalone fraction words:
        ("dhai", 2.5),
        ("derh", 1.5),
        ("dedh", 1.5),
        ("sawa", 1.25),
        ("paun", 0.75),
        ("paune", 0.75),
        # Standard Hindi 0-100 vocabulary samples:
        ("shunya", 0.0),
        ("ek", 1.0),
        ("do", 2.0),
        ("teen", 3.0),
        ("chaar", 4.0),
        ("paanch", 5.0),
        ("das", 10.0),
        ("gyarah", 11.0),
        ("pandrah", 15.0),
        ("solah", 16.0),
        ("unnees", 19.0),
        ("bees", 20.0),
        ("ikkees", 21.0),
        ("pachees", 25.0),
        ("tees", 30.0),
        ("paintees", 35.0),
        ("chhattees", 36.0),
        ("chaalees", 40.0),
        ("pachaas", 50.0),
        ("saath", 60.0),
        ("sattar", 70.0),
        ("pachhattar", 75.0),
        ("assee", 80.0),
        ("nabbe", 90.0),
        ("sau", 100.0),
        # English numerals:
        ("zero", 0.0),
        ("five", 5.0),
        ("twenty five", 25.0),
        ("fifty", 50.0),
        ("one hundred", 100.0),
        # Colloquial compounds:
        ("teen hazaar paanch sau", 3500.0),
        ("pachees sau", 2500.0),
        ("two fifty", 250.0),
        ("do lakh pachaas hazaar", 250000.0),
        ("ek crore", 10000000.0),
        # Pure digit strings:
        ("250", 250.0),
        ("1,500.50", 1500.50),
        ("₹350", 350.0),
    ],
)
def test_parse_spoken_number(input_text: str, expected_val: float) -> None:
    result = parse_spoken_number(input_text)
    assert result == pytest.approx(expected_val)


def test_extract_numbers_in_sentence() -> None:
    text = "Ramesh ji ko dhai sau rupaye udhaar diye aur Suresh ko teen hazaar paanch sau"
    extracted = extract_numbers(text)
    assert len(extracted) == 2
    assert extracted[0].value == 250.0
    assert extracted[0].raw_text == "dhai sau"
    assert extracted[1].value == 3500.0
    assert extracted[1].raw_text == "teen hazaar paanch sau"


def test_parse_invalid_number() -> None:
    assert parse_spoken_number("ramesh kumar") is None
    assert parse_spoken_number("aaj sham ko") is None
    assert parse_spoken_number("") is None
