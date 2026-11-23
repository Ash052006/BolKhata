"""
Deterministic unit and currency normalization for Kirana and commerce domains.

Handles:
- Weights: kilo/kg, gram/gm, quintal, pau (250g), aadha kilo (500g)
- Volume: litre/l, millilitre/ml
- Count/Packaging: dozen/darjan (12), aadha darjan (6), packet/pkt, thaili/pouch, piece/pc/nag, dabba/box, peti/crate, bori/sack
- Currency: rupee/rupaye/rs/inr/₹, paise/paisa (0.01 INR)
- Ambiguity detection: ranges ('do teen kilo' -> candidates [2.0, 3.0], is_ambiguous=True),
  missing units, ambiguous denominations.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from bolkhata.domains.common.numbers import (
    NUM_0_TO_100,
    parse_spoken_number,
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ParsedQuantity(BaseModel):
    """Normalized physical or discrete quantity."""

    value: float
    unit: str  # canonical: kg, g, l, ml, dozen, packet, piece, pouch, sack, box, crate
    raw_text: str
    is_ambiguous: bool = False
    confidence: float = 1.0
    candidates: list[float] = Field(default_factory=list)


class ParsedMoney(BaseModel):
    """Normalized monetary amount in standard INR."""

    amount: float
    currency: str = "INR"
    raw_text: str
    is_ambiguous: bool = False
    confidence: float = 1.0
    candidates: list[float] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------

UNIT_LEXICON: dict[str, tuple[str, float]] = {
    # Weight
    "kg": ("kg", 1.0),
    "kgs": ("kg", 1.0),
    "kilo": ("kg", 1.0),
    "kilos": ("kg", 1.0),
    "kilogram": ("kg", 1.0),
    "kilograms": ("kg", 1.0),
    "किलो": ("kg", 1.0),
    "किलोग्राम": ("kg", 1.0),
    "केजी": ("kg", 1.0),
    "g": ("g", 1.0),
    "gm": ("g", 1.0),
    "gms": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "ग्राम": ("g", 1.0),
    "ग्राम्स": ("g", 1.0),
    "quintal": ("quintal", 1.0),
    "क्विंटल": ("quintal", 1.0),
    # Volume
    "l": ("l", 1.0),
    "lt": ("l", 1.0),
    "ltr": ("l", 1.0),
    "ltrs": ("l", 1.0),
    "litre": ("l", 1.0),
    "litres": ("l", 1.0),
    "liter": ("l", 1.0),
    "liters": ("l", 1.0),
    "लीटर": ("l", 1.0),
    "ली": ("l", 1.0),
    "ml": ("ml", 1.0),
    "mili": ("ml", 1.0),
    "millilitre": ("ml", 1.0),
    "millilitres": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "मिली": ("ml", 1.0),
    "मिलीलीटर": ("ml", 1.0),
    # Count / Units
    "dozen": ("dozen", 1.0),
    "dozens": ("dozen", 1.0),
    "darjan": ("dozen", 1.0),
    "darzan": ("dozen", 1.0),
    "दर्जन": ("dozen", 1.0),
    "packet": ("packet", 1.0),
    "packets": ("packet", 1.0),
    "pkt": ("packet", 1.0),
    "pkts": ("packet", 1.0),
    "pack": ("packet", 1.0),
    "packs": ("packet", 1.0),
    "पैकेट": ("packet", 1.0),
    "पैक": ("packet", 1.0),
    "piece": ("piece", 1.0),
    "pieces": ("piece", 1.0),
    "pc": ("piece", 1.0),
    "pcs": ("piece", 1.0),
    "पीस": ("piece", 1.0),
    "nag": ("piece", 1.0),
    "नग": ("piece", 1.0),
    "bori": ("sack", 1.0),
    "boriyaan": ("sack", 1.0),
    "boriyan": ("sack", 1.0),
    "बोरी": ("sack", 1.0),
    "sack": ("sack", 1.0),
    "sacks": ("sack", 1.0),
    "thaili": ("pouch", 1.0),
    "theli": ("pouch", 1.0),
    "थैली": ("pouch", 1.0),
    "pouch": ("pouch", 1.0),
    "pouches": ("pouch", 1.0),
    "dabba": ("box", 1.0),
    "dibba": ("box", 1.0),
    "dabbe": ("box", 1.0),
    "डिब्बा": ("box", 1.0),
    "डिब्बे": ("box", 1.0),
    "box": ("box", 1.0),
    "boxes": ("box", 1.0),
    "bottle": ("bottle", 1.0),
    "bottles": ("bottle", 1.0),
    "botal": ("bottle", 1.0),
    "बोतल": ("bottle", 1.0),
    "peti": ("crate", 1.0),
    "पेटी": ("crate", 1.0),
    "crate": ("crate", 1.0),
    "crates": ("crate", 1.0),
}

CURRENCY_WORDS: set[str] = {
    "rupee",
    "rupees",
    "rupaye",
    "rupaya",
    "rupay",
    "rs",
    "rs.",
    "inr",
    "₹",
    "रुपये",
    "रुपया",
    "रु",
    "रू",
    "bucks",
}

PAISE_WORDS: set[str] = {
    "paisa",
    "paise",
    "पैसे",
    "पैसा",
    "p",
}


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_quantity(text: str) -> ParsedQuantity | None:
    """
    Parse a quantity expression such as '2 kg', 'aadha kilo', 'pau kilo', 'ek darjan', 'do teen packet'.
    """
    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # Check for range / ambiguous quantities: e.g. "do teen kilo" -> candidates [2.0, 3.0]
    range_match = re.search(
        r"^(?P<w1>[a-z\u0900-\u097f]+|\d+)\s*(?:se|ya|to|-)\s*(?P<w2>[a-z\u0900-\u097f]+|\d+)\s*(?P<unit>[a-z\u0900-\u097f]+)$",
        cleaned,
    )
    if not range_match:
        # Check two adjacent number words before unit: e.g. "do teen kilo", "ek do packet"
        # Must exclude multipliers like 'sau' / 'hazaar' which form compound numbers like 'paanch sau'
        words = cleaned.split()
        if (
            len(words) == 3
            and words[0] in NUM_0_TO_100
            and words[1] in NUM_0_TO_100
            and words[1] not in ("sau", "सौ", "hundred", "hazaar", "हज़ार", "lakh", "crore")
            and words[2] in UNIT_LEXICON
        ):
            v1 = float(NUM_0_TO_100[words[0]])
            v2 = float(NUM_0_TO_100[words[1]])
            canon_unit, _ = UNIT_LEXICON[words[2]]
            return ParsedQuantity(
                value=v1,
                unit=canon_unit,
                raw_text=text,
                is_ambiguous=True,
                confidence=0.5,
                candidates=[v1, v2],
            )

    if range_match:
        g = range_match.groupdict()
        n1 = parse_spoken_number(g["w1"])
        n2 = parse_spoken_number(g["w2"])
        u_raw = g["unit"]
        if n1 is not None and n2 is not None and u_raw in UNIT_LEXICON:
            canon_unit, _ = UNIT_LEXICON[u_raw]
            return ParsedQuantity(
                value=n1,
                unit=canon_unit,
                raw_text=text,
                is_ambiguous=True,
                confidence=0.5,
                candidates=[n1, n2],
            )

    # Special colloquial Indian quantity phrases:
    # "aadha kilo" / "adha kilo" -> 0.5 kg (or 500 g)
    if re.search(r"^(?:aadha|adha|आधा)\s+(?:kilo|किलो|kg)$", cleaned):
        return ParsedQuantity(value=0.5, unit="kg", raw_text=text)

    # "aadha darjan" -> 0.5 dozen
    if re.search(r"^(?:aadha|adha|आधा)\s+(?:darjan|dozen|दर्जन)$", cleaned):
        return ParsedQuantity(value=0.5, unit="dozen", raw_text=text)

    # "aadha litre" -> 0.5 l
    if re.search(r"^(?:aadha|adha|आधा)\s+(?:litre|liter|लीटर|l)$", cleaned):
        return ParsedQuantity(value=0.5, unit="l", raw_text=text)

    # "pau" / "paav" / "पाव" standalone = 250g
    if cleaned in ("pau", "paav", "पाव", "पाओ"):
        return ParsedQuantity(value=250.0, unit="g", raw_text=text)

    # "pau kilo" / "paav kilo" = 0.25 kg
    if re.search(r"^(?:pau|paav|पाव|पाओ)\s+(?:kilo|किलो|kg)$", cleaned):
        return ParsedQuantity(value=0.25, unit="kg", raw_text=text)

    # "dedh kilo" = 1.5 kg
    if re.search(r"^(?:dedh|derh|deedh|डेढ़)\s+(?:kilo|किलो|kg)$", cleaned):
        return ParsedQuantity(value=1.5, unit="kg", raw_text=text)

    # "dhai kilo" = 2.5 kg
    if re.search(r"^(?:dhai|dhaai|ढाई)\s+(?:kilo|किलो|kg)$", cleaned):
        return ParsedQuantity(value=2.5, unit="kg", raw_text=text)

    # "sawa kilo" = 1.25 kg
    if re.search(r"^(?:sawa|सवा)\s+(?:kilo|किलो|kg)$", cleaned):
        return ParsedQuantity(value=1.25, unit="kg", raw_text=text)

    # "paune do kilo" = 1.75 kg
    if re.search(r"^(?:paune|paun|पौने)\s+do\s+(?:kilo|किलो|kg)$", cleaned):
        return ParsedQuantity(value=1.75, unit="kg", raw_text=text)

    # General pattern: <number_phrase> <unit>
    # Separate trailing unit token
    tokens = cleaned.split()
    if not tokens:
        return None

    unit_token = tokens[-1].strip(",.!?")
    if unit_token in UNIT_LEXICON:
        canon_unit, multiplier = UNIT_LEXICON[unit_token]
        num_str = " ".join(tokens[:-1])
        if not num_str:
            # Bare unit without quantity: e.g. "kilo" -> default 1.0 but ambiguous
            return ParsedQuantity(
                value=1.0,
                unit=canon_unit,
                raw_text=text,
                is_ambiguous=True,
                confidence=0.7,
                candidates=[1.0],
            )
        val = parse_spoken_number(num_str)
        if val is not None:
            return ParsedQuantity(
                value=val * multiplier,
                unit=canon_unit,
                raw_text=text,
                is_ambiguous=False,
                confidence=1.0,
            )

    return None


def parse_money_amount(text: str) -> ParsedMoney | None:
    """
    Parse a money phrase in rupees and paise (e.g. '₹250', 'dhai sau rupaye', 'do sau पचास paise').
    """
    cleaned = text.strip().lower()
    if not cleaned:
        return None

    # Check for range / ambiguous amounts: e.g. "do teen sau rupaye"
    words = cleaned.split()
    if len(words) >= 3 and words[-1] in CURRENCY_WORDS:
        # Check if first two are numbers before "sau"
        if (
            len(words) == 4
            and words[0] in NUM_0_TO_100
            and words[1] in NUM_0_TO_100
            and words[2] in ("sau", "सौ")
        ):
            v1 = float(NUM_0_TO_100[words[0]]) * 100
            v2 = float(NUM_0_TO_100[words[1]]) * 100
            return ParsedMoney(
                amount=v1,
                currency="INR",
                raw_text=text,
                is_ambiguous=True,
                confidence=0.5,
                candidates=[v1, v2],
            )

    # Check for direct symbol pattern: ₹500, Rs. 250, INR 1200
    cleaned_sym = re.sub(r"^(?:₹|rs\.?|inr)\s*", "", cleaned).strip()
    direct_num = parse_spoken_number(cleaned_sym)
    if direct_num is not None and (
        cleaned.startswith("₹")
        or cleaned.startswith("rs")
        or cleaned.startswith("inr")
        or any(w in cleaned for w in CURRENCY_WORDS)
    ):
        return ParsedMoney(
            amount=direct_num,
            currency="INR",
            raw_text=text,
            is_ambiguous=False,
            confidence=1.0,
        )

    # Check compound rupees and paise: e.g. "das rupaye pachaas paise" -> 10.50
    compound_match = re.match(
        r"^(?P<rs>.+?)\s*(?:rupaye|rupee|rupees|रुपये|रुपया)\s*(?:aur|and|और)?\s*(?P<paise>.+?)\s*(?:paise|paisa|पैसे|पैसा)$",
        cleaned,
    )
    if compound_match:
        rs_str = compound_match.group("rs")
        paise_str = compound_match.group("paise")
        rs_val = parse_spoken_number(rs_str)
        paise_val = parse_spoken_number(paise_str)
        if rs_val is not None and paise_val is not None:
            total = rs_val + (paise_val / 100.0)
            return ParsedMoney(
                amount=total,
                currency="INR",
                raw_text=text,
                is_ambiguous=False,
                confidence=1.0,
            )

    # Check bare paise: e.g. "pachaas paise" -> 0.50 INR
    paise_match = re.match(r"^(?P<paise>.+?)\s*(?:paise|paisa|पैसे|पैसा)$", cleaned)
    if paise_match:
        paise_str = paise_match.group("paise")
        paise_val = parse_spoken_number(paise_str)
        if paise_val is not None:
            return ParsedMoney(
                amount=paise_val / 100.0,
                currency="INR",
                raw_text=text,
                is_ambiguous=False,
                confidence=1.0,
            )

    # Strip currency words from beginning or end and parse remainder as rupees
    cleaned_tokens = [t for t in words if t not in CURRENCY_WORDS]
    if cleaned_tokens:
        val = parse_spoken_number(" ".join(cleaned_tokens))
        if val is not None:
            # Check if text actually contained any currency word
            had_currency = any(w in words for w in CURRENCY_WORDS) or cleaned.startswith("₹")
            return ParsedMoney(
                amount=val,
                currency="INR",
                raw_text=text,
                is_ambiguous=not had_currency,  # If no explicit currency word was spoken, flag ambiguity
                confidence=1.0 if had_currency else 0.8,
            )

    return None
