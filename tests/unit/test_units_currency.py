"""
Table-driven unit tests for unit and currency normalization (100+ tricky test cases).

Verifies:
- Mass/Weight (kg, g, quintal, colloquial pau, aadha kilo, dedh kilo, dhai kilo, sawa kilo, paune do kilo)
- Volume (litre, ml, aadha litre)
- Count & Containers (dozen/darjan, aadha darjan, packet, pouch/thaili, piece/nag, sack/bori, box/dabba, crate/peti)
- Currency (rupees, INR, Rs, ₹, paise, compound rupees + paise)
- Ambiguity detection (ranges e.g. 'do teen kilo', missing units, missing currency words)
"""

import pytest

from bolkhata.domains.common.units import (
    parse_money_amount,
    parse_quantity,
)

# ---------------------------------------------------------------------------
# Test Data: 100+ Table-Driven Cases
# ---------------------------------------------------------------------------

QUANTITY_TEST_CASES = [
    # 1-10: Standard metric weights (English)
    ("1 kg", 1.0, "kg", False),
    ("2 kgs", 2.0, "kg", False),
    ("500 g", 500.0, "g", False),
    ("250 gm", 250.0, "g", False),
    ("100 grams", 100.0, "g", False),
    ("5 kilogram", 5.0, "kg", False),
    ("10 kilograms", 10.0, "kg", False),
    ("2 quintal", 2.0, "quintal", False),
    ("50 gm", 50.0, "g", False),
    ("1.5 kg", 1.5, "kg", False),
    # 11-20: Metric weights (Hinglish words)
    ("ek kilo", 1.0, "kg", False),
    ("do kilo", 2.0, "kg", False),
    ("teen kilo", 3.0, "kg", False),
    ("paanch kilo", 5.0, "kg", False),
    ("das kilo", 10.0, "kg", False),
    ("pachees kilo", 25.0, "kg", False),
    ("pachaas gram", 50.0, "g", False),
    ("sau gram", 100.0, "g", False),
    ("dhai sau gram", 250.0, "g", False),
    ("panch sau gram", 500.0, "g", False),
    # 21-30: Colloquial weights & fractions
    ("aadha kilo", 0.5, "kg", False),
    ("adha kilo", 0.5, "kg", False),
    ("pau", 250.0, "g", False),
    ("paav", 250.0, "g", False),
    ("pau kilo", 0.25, "kg", False),
    ("paav kilo", 0.25, "kg", False),
    ("dedh kilo", 1.5, "kg", False),
    ("derh kilo", 1.5, "kg", False),
    ("dhai kilo", 2.5, "kg", False),
    ("sawa kilo", 1.25, "kg", False),
    # 31-40: Devanagari weights
    ("१ किलो", 1.0, "kg", False),
    ("दो किलो", 2.0, "kg", False),
    ("पाँच किलो", 5.0, "kg", False),
    ("दस किलो", 10.0, "kg", False),
    ("आधा किलो", 0.5, "kg", False),
    ("पाव किलो", 0.25, "kg", False),
    ("डेढ़ किलो", 1.5, "kg", False),
    ("ढाई किलो", 2.5, "kg", False),
    ("सवा किलो", 1.25, "kg", False),
    ("सौ ग्राम", 100.0, "g", False),
    # 41-50: Liquid volume (English & Hinglish)
    ("1 l", 1.0, "l", False),
    ("2 litre", 2.0, "l", False),
    ("5 litres", 5.0, "l", False),
    ("500 ml", 500.0, "ml", False),
    ("200 ml", 200.0, "ml", False),
    ("ek litre", 1.0, "l", False),
    ("do litre", 2.0, "l", False),
    ("aadha litre", 0.5, "l", False),
    ("dedh litre", 1.5, "l", False),
    ("dhai litre", 2.5, "l", False),
    # 51-60: Discrete items & packaging (English & Hinglish)
    ("1 dozen", 1.0, "dozen", False),
    ("2 dozen", 2.0, "dozen", False),
    ("ek darjan", 1.0, "dozen", False),
    ("do darjan", 2.0, "dozen", False),
    ("aadha darjan", 0.5, "dozen", False),
    ("1 packet", 1.0, "packet", False),
    ("5 packet", 5.0, "packet", False),
    ("das packet", 10.0, "packet", False),
    ("2 pkt", 2.0, "packet", False),
    ("teen pack", 3.0, "packet", False),
    # 61-70: Containers & bags (bori, thaili, dabba, peti, bottle, piece)
    ("ek bori", 1.0, "sack", False),
    ("do bori", 2.0, "sack", False),
    ("teen boriyaan", 3.0, "sack", False),
    ("ek thaili", 1.0, "pouch", False),
    ("do theli", 2.0, "pouch", False),
    ("paanch piece", 5.0, "piece", False),
    ("das nag", 10.0, "piece", False),
    ("ek dabba", 1.0, "box", False),
    ("do dibba", 2.0, "box", False),
    ("ek peti", 1.0, "crate", False),
    # 71-75: Devanagari packaging
    ("एक दर्जन", 1.0, "dozen", False),
    ("आधा दर्जन", 0.5, "dozen", False),
    ("दो पैकेट", 2.0, "packet", False),
    ("एक बोरी", 1.0, "sack", False),
    ("चार पीस", 4.0, "piece", False),
]

MONEY_TEST_CASES = [
    # 76-85: Direct symbols and notation
    ("₹50", 50.0, False),
    ("₹100", 100.0, False),
    ("₹250", 250.0, False),
    ("₹1500", 1500.0, False),
    ("₹3,500.50", 3500.50, False),
    ("Rs 500", 500.0, False),
    ("Rs. 200", 200.0, False),
    ("INR 1200", 1200.0, False),
    ("Rs. 50.50", 50.50, False),
    ("₹10", 10.0, False),
    # 86-95: Spoken rupees in Hinglish
    ("dhai sau rupaye", 250.0, False),
    ("derh hazaar rupaye", 1500.0, False),
    ("sawa sau rupaye", 125.0, False),
    ("sadhe teen sau rupaye", 350.0, False),
    ("paune do sau rupaye", 175.0, False),
    ("pachees rupaye", 25.0, False),
    ("pachaas rupaye", 50.0, False),
    ("ek sau bees rupaye", 120.0, False),
    ("teen hazaar paanch sau rupaye", 3500.0, False),
    ("das hazaar rupaye", 10000.0, False),
    # 96-105: Spoken rupees in Devanagari
    ("ढाई सौ रुपये", 250.0, False),
    ("डेढ़ हज़ार रुपये", 1500.0, False),
    ("सवा सौ रुपये", 125.0, False),
    ("साढ़े तीन सौ रुपये", 350.0, False),
    ("पौने दो सौ रुपये", 175.0, False),
    ("पचास रुपये", 50.0, False),
    ("सौ रुपये", 100.0, False),
    ("पाँच सौ रुपये", 500.0, False),
    ("दो हज़ार रुपये", 2000.0, False),
    ("दस रुपये", 10.0, False),
    # 106-115: Compound Rupees and Paise
    ("das rupaye pachaas paise", 10.50, False),
    ("pachees rupaye pachaas paise", 25.50, False),
    ("sau rupaye pachaas paise", 100.50, False),
    ("paanch rupaye pachees paise", 5.25, False),
    ("do rupaye pachaas paise", 2.50, False),
    ("bees rupaye pachaas paise", 20.50, False),
    ("50 rupaye 50 paise", 50.50, False),
    ("ek sau rupaye aur pachaas paise", 100.50, False),
    ("pachaas paise", 0.50, False),
    ("pachees paise", 0.25, False),
]

AMBIGUITY_TEST_CASES = [
    # 116-125: Ambiguous quantities (ranges or bare units)
    ("do teen kilo", "kg", [2.0, 3.0]),
    ("ek do packet", "packet", [1.0, 2.0]),
    ("chaar paanch darjan", "dozen", [4.0, 5.0]),
    ("paanch chhe bori", "sack", [5.0, 6.0]),
    ("kilo", "kg", [1.0]),
    # 126-130: Ambiguous money amounts
    ("do teen sau rupaye", [200.0, 300.0]),
    ("chaar paanch sau rupaye", [400.0, 500.0]),
    ("500", [500.0]),  # Missing currency indicator -> flagged is_ambiguous
]


@pytest.mark.parametrize(
    ("input_str", "expected_val", "expected_unit", "expected_ambiguous"),
    QUANTITY_TEST_CASES,
)
def test_parse_quantity_table(
    input_str: str,
    expected_val: float,
    expected_unit: str,
    expected_ambiguous: bool,
) -> None:
    res = parse_quantity(input_str)
    assert res is not None, f"Failed to parse quantity for '{input_str}'"
    assert res.value == pytest.approx(expected_val)
    assert res.unit == expected_unit
    assert res.is_ambiguous == expected_ambiguous


@pytest.mark.parametrize(
    ("input_str", "expected_amount", "expected_ambiguous"),
    MONEY_TEST_CASES,
)
def test_parse_money_table(
    input_str: str,
    expected_amount: float,
    expected_ambiguous: bool,
) -> None:
    res = parse_money_amount(input_str)
    assert res is not None, f"Failed to parse money for '{input_str}'"
    assert res.amount == pytest.approx(expected_amount)
    assert res.currency == "INR"
    assert res.is_ambiguous == expected_ambiguous


def test_ambiguous_quantities() -> None:
    for input_str, unit, candidates in AMBIGUITY_TEST_CASES[:5]:
        res = parse_quantity(input_str)
        assert res is not None, f"Failed to parse '{input_str}'"
        assert res.is_ambiguous is True
        assert res.unit == unit
        assert res.candidates == candidates
        assert res.confidence < 1.0


def test_ambiguous_money() -> None:
    for input_str, candidates in AMBIGUITY_TEST_CASES[5:]:
        res = parse_money_amount(input_str)
        assert res is not None, f"Failed to parse '{input_str}'"
        assert res.is_ambiguous is True
        assert res.confidence < 1.0
        if candidates != [500.0]:
            assert res.candidates == candidates
