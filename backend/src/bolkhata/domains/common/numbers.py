"""
Deterministic spoken number parser for Hindi, English, Hinglish, and Devanagari.

Covers:
- Standard digits and formatted numbers (e.g. 250, 1,500.50)
- Numbers 0 to 100 in English, Romanized Hindi, and Devanagari
- Indian numbering system multipliers: sau (100), hazaar (1,000), lakh (100,000), crore (10,000,000)
- Colloquial fractional prefixes:
    * dhai / dhaai / ढाई (2.5x base): dhai sau = 250, dhai hazaar = 2500
    * derh / dedh / deedh / डेढ़ (1.5x base): derh hazaar = 1500, dedh sau = 150
    * sawa / सवा (+0.25 of unit): sawa sau = 125, sawa do sau = 225, sawa hazaar = 1250
    * sadhe / saadhe / साढ़े (+0.5 of unit for >= 3): sadhe teen sau = 350, sadhe char sau = 450
    * paune / paun / पौने (-0.25 of unit): paune do sau = 175, paune teen hazaar = 2750
- Compound structures: teen hazaar paanch sau = 3500, pachees sau = 2500
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Lexicon Dictionaries
# ---------------------------------------------------------------------------

# Single units 0-100 mapping across English, Romanized Hindi, and Devanagari
NUM_0_TO_100: dict[str, int] = {
    # 0
    "zero": 0,
    "shunya": 0,
    "shoonya": 0,
    "sifar": 0,
    "शून्य": 0,
    "सिफर": 0,
    "०": 0,
    "0": 0,
    # 1-10
    "one": 1,
    "ek": 1,
    "aik": 1,
    "एक": 1,
    "१": 1,
    "1": 1,
    "two": 2,
    "do": 2,
    "doo": 2,
    "दो": 2,
    "२": 2,
    "2": 2,
    "three": 3,
    "teen": 3,
    "tin": 3,
    "तीन": 3,
    "३": 3,
    "3": 3,
    "four": 4,
    "chaar": 4,
    "char": 4,
    "चार": 4,
    "४": 4,
    "4": 4,
    "five": 5,
    "paanch": 5,
    "panch": 5,
    "पांच": 5,
    "पाँच": 5,
    "५": 5,
    "5": 5,
    "six": 6,
    "chhe": 6,
    "che": 6,
    "chheh": 6,
    "छह": 6,
    "छे": 6,
    "छः": 6,
    "६": 6,
    "6": 6,
    "seven": 7,
    "saat": 7,
    "sat": 7,
    "सात": 7,
    "७": 7,
    "7": 7,
    "eight": 8,
    "aath": 8,
    "ath": 8,
    "आठ": 8,
    "८": 8,
    "8": 8,
    "nine": 9,
    "nau": 9,
    "no": 9,
    "नौ": 9,
    "९": 9,
    "9": 9,
    "ten": 10,
    "das": 10,
    "duss": 10,
    "दस": 10,
    # 11-20
    "eleven": 11,
    "gyarah": 11,
    "gyaarah": 11,
    "ग्यारह": 11,
    "twelve": 12,
    "barah": 12,
    "baarah": 12,
    "बारह": 12,
    "thirteen": 13,
    "terah": 13,
    "तेरह": 13,
    "fourteen": 14,
    "chaudah": 14,
    "choudah": 14,
    "चौदह": 14,
    "fifteen": 15,
    "pandrah": 15,
    "पंद्रह": 15,
    "पन्द्रह": 15,
    "sixteen": 16,
    "solah": 16,
    "सोलह": 16,
    "seventeen": 17,
    "satrah": 17,
    "सत्रह": 17,
    "eighteen": 18,
    "atharah": 18,
    "athaarah": 18,
    "attharah": 18,
    "अट्ठारह": 18,
    "अठारह": 18,
    "nineteen": 19,
    "unnees": 19,
    "unnis": 19,
    "उन्नीस": 19,
    "twenty": 20,
    "bees": 20,
    "bis": 20,
    "बीस": 20,
    # 21-30
    "twenty one": 21,
    "twenty-one": 21,
    "ikkees": 21,
    "ikkis": 21,
    "इक्कीस": 21,
    "twenty two": 22,
    "twenty-two": 22,
    "baais": 22,
    "बाईस": 22,
    "twenty three": 23,
    "twenty-three": 23,
    "teyees": 23,
    "teis": 23,
    "तेईस": 23,
    "twenty four": 24,
    "twenty-four": 24,
    "chaubees": 24,
    "choubis": 24,
    "चौबीस": 24,
    "twenty five": 25,
    "twenty-five": 25,
    "pachees": 25,
    "pachhees": 25,
    "pachis": 25,
    "पच्चीस": 25,
    "twenty six": 26,
    "twenty-six": 26,
    "chhabbees": 26,
    "chabbis": 26,
    "छब्बीस": 26,
    "twenty seven": 27,
    "twenty-seven": 27,
    "sattaais": 27,
    "sattais": 27,
    "सत्ताईस": 27,
    "twenty eight": 28,
    "twenty-eight": 28,
    "atthaais": 28,
    "tthais": 28,
    "अट्ठाईस": 28,
    "अठ्ठाईस": 28,
    "twenty nine": 29,
    "twenty-nine": 29,
    "untees": 29,
    "untis": 29,
    "उन्तीस": 29,
    "thirty": 30,
    "tees": 30,
    "तीस": 30,
    # 31-40
    "thirty one": 31,
    "thirty-one": 31,
    "iktees": 31,
    "iktis": 31,
    "इकतीस": 31,
    "इकत्तीस": 31,
    "thirty two": 32,
    "thirty-two": 32,
    "battees": 32,
    "battis": 32,
    "बत्तीस": 32,
    "thirty three": 33,
    "thirty-three": 33,
    "taintees": 33,
    "tentis": 33,
    "तैंतीस": 33,
    "thirty four": 34,
    "thirty-four": 34,
    "chauntees": 34,
    "chautis": 34,
    "चौंतीस": 34,
    "thirty five": 35,
    "thirty-five": 35,
    "paintees": 35,
    "paintis": 35,
    "पैंतीस": 35,
    "thirty six": 36,
    "thirty-six": 36,
    "chhattees": 36,
    "chhattis": 36,
    "छत्तीस": 36,
    "thirty seven": 37,
    "thirty-seven": 37,
    "saintees": 37,
    "saintis": 37,
    "सैंतीस": 37,
    "thirty eight": 38,
    "thirty-eight": 38,
    "adtees": 38,
    "adtis": 38,
    "अड़तीस": 38,
    "thirty nine": 39,
    "thirty-nine": 39,
    "untaalees": 39,
    "untalis": 39,
    "उनतालीस": 39,
    "उनचालीस": 39,
    "forty": 40,
    "chaalees": 40,
    "chalis": 40,
    "चालीस": 40,
    # 41-50
    "forty one": 41,
    "forty-one": 41,
    "iktaalees": 41,
    "iktalis": 41,
    "इकतालीस": 41,
    "forty two": 42,
    "forty-two": 42,
    "bayaalees": 42,
    "bayalis": 42,
    "बयालीस": 42,
    "forty three": 43,
    "forty-three": 43,
    "taintaalees": 43,
    "taintalis": 43,
    "तैंतालीस": 43,
    "forty four": 44,
    "forty-four": 44,
    "chauwaalees": 44,
    "chawalis": 44,
    "चवालीस": 44,
    "चौवालीस": 44,
    "forty five": 45,
    "forty-five": 45,
    "paintaalees": 45,
    "paintalis": 45,
    "पैंतालीस": 45,
    "forty six": 46,
    "forty-six": 46,
    "chhiyaalees": 46,
    "chhiyalis": 46,
    "छियालीस": 46,
    "forty seven": 47,
    "forty-seven": 47,
    "saintaalees": 47,
    "saintalis": 47,
    "सैंतालीस": 47,
    "forty eight": 48,
    "forty-eight": 48,
    "adtaalees": 48,
    "adtalis": 48,
    "अड़तालीस": 48,
    "forty nine": 49,
    "forty-nine": 49,
    "unchaas": 49,
    "unchas": 49,
    "उनचास": 49,
    "fifty": 50,
    "pachaas": 50,
    "pachas": 50,
    "पचास": 50,
    # 51-60
    "fifty one": 51,
    "fifty-one": 51,
    "ikyawan": 51,
    "इक्यावन": 51,
    "fifty two": 52,
    "fifty-two": 52,
    "baawan": 52,
    "बावन": 52,
    "fifty three": 53,
    "fifty-three": 53,
    "tirepan": 53,
    "तिरेपन": 53,
    "तिरपन": 53,
    "fifty four": 54,
    "fifty-four": 54,
    "chauwan": 54,
    "चौवन": 54,
    "fifty five": 55,
    "fifty-five": 55,
    "pachpan": 55,
    "पचपन": 55,
    "fifty six": 56,
    "fifty-six": 56,
    "chhappan": 56,
    "छप्पन": 56,
    "fifty seven": 57,
    "fifty-seven": 57,
    "sattawan": 57,
    "सत्तावन": 57,
    "fifty eight": 58,
    "fifty-eight": 58,
    "atthaawan": 58,
    "अट्ठावन": 58,
    "fifty nine": 59,
    "fifty-nine": 59,
    "unsath": 59,
    "उनसठ": 59,
    "sixty": 60,
    "saath": 60,
    "sath": 60,
    "साठ": 60,
    # 61-70
    "sixty one": 61,
    "sixty-one": 61,
    "iksath": 61,
    "इकसठ": 61,
    "sixty two": 62,
    "sixty-two": 62,
    "baasath": 62,
    "बासठ": 62,
    "sixty three": 63,
    "sixty-three": 63,
    "tirsath": 63,
    "तिरसठ": 63,
    "sixty four": 64,
    "sixty-four": 64,
    "chausath": 64,
    "चौसठ": 64,
    "sixty five": 65,
    "sixty-five": 65,
    "painsath": 65,
    "पैंसठ": 65,
    "sixty six": 66,
    "sixty-six": 66,
    "chhiyaasath": 66,
    "छियासठ": 66,
    "sixty seven": 67,
    "sixty-seven": 67,
    "sadsath": 67,
    "सड़सठ": 67,
    "sixty eight": 68,
    "sixty-eight": 68,
    "adsath": 68,
    "अड़सठ": 68,
    "sixty nine": 69,
    "sixty-nine": 69,
    "unhattar": 69,
    "unhatthar": 69,
    "उनहत्तर": 69,
    "seventy": 70,
    "sattar": 70,
    "सत्तर": 70,
    # 71-80
    "seventy one": 71,
    "seventy-one": 71,
    "ikhattar": 71,
    "इकहत्तर": 71,
    "seventy two": 72,
    "seventy-two": 72,
    "bahattar": 72,
    "बहत्तर": 72,
    "seventy three": 73,
    "seventy-three": 73,
    "tihattar": 73,
    "तिहत्तर": 73,
    "seventy four": 74,
    "seventy-four": 74,
    "chauhattar": 74,
    "चौहत्तर": 74,
    "seventy five": 75,
    "seventy-five": 75,
    "pachhattar": 75,
    "पचहत्तर": 75,
    "seventy six": 76,
    "seventy-six": 76,
    "chhihattar": 76,
    "छहत्तर": 76,
    "छिहत्तर": 76,
    "seventy seven": 77,
    "seventy-seven": 77,
    "sathattar": 77,
    "सतहत्तर": 77,
    "seventy eight": 78,
    "seventy-eight": 78,
    "athahattar": 78,
    "अठहत्तर": 78,
    "seventy nine": 79,
    "seventy-nine": 79,
    "unasi": 79,
    "unaasi": 79,
    "उन्नासी": 79,
    "eighty": 80,
    "assee": 80,
    "assi": 80,
    "अस्सी": 80,
    # 81-90
    "eighty one": 81,
    "eighty-one": 81,
    "ikyaasi": 81,
    "इक्यासी": 81,
    "eighty two": 82,
    "eighty-two": 82,
    "bayaasi": 82,
    "बयासी": 82,
    "eighty three": 83,
    "eighty-three": 83,
    "tiraasi": 83,
    "तिरासी": 83,
    "eighty four": 84,
    "eighty-four": 84,
    "chauraasi": 84,
    "चौरासी": 84,
    "eighty five": 85,
    "eighty-five": 85,
    "pachaasi": 85,
    "pachasi": 85,
    "पचासी": 85,
    "eighty six": 86,
    "eighty-six": 86,
    "chhiyaasi": 86,
    "छियासी": 86,
    "eighty seven": 87,
    "eighty-seven": 87,
    "sattaasi": 87,
    "सत्तासी": 87,
    "eighty eight": 88,
    "eighty-eight": 88,
    "atthaasi": 88,
    "अट्ठासी": 88,
    "eighty nine": 89,
    "eighty-nine": 89,
    "nawaasi": 89,
    "nawasi": 89,
    "नवासी": 89,
    "ninety": 90,
    "nabbe": 90,
    "नब्बे": 90,
    # 91-100
    "ninety one": 91,
    "ninety-one": 91,
    "ikyaanwe": 91,
    "इक्यानवे": 91,
    "ninety two": 92,
    "ninety-two": 92,
    "baanwe": 92,
    "बानवे": 92,
    "ninety three": 93,
    "ninety-three": 93,
    "tiraanwe": 93,
    "तिरानवे": 93,
    "ninety four": 94,
    "ninety-four": 94,
    "chauraanwe": 94,
    "चौरानवे": 94,
    "ninety five": 95,
    "ninety-five": 95,
    "pachaanwe": 95,
    "पचानवे": 95,
    "ninety six": 96,
    "ninety-six": 96,
    "chhiyaanwe": 96,
    "छियानवे": 96,
    "ninety seven": 97,
    "ninety-seven": 97,
    "sattaanwe": 97,
    "सत्तानवे": 97,
    "ninety eight": 98,
    "ninety-eight": 98,
    "atthaanwe": 98,
    "अट्ठानवे": 98,
    "ninety nine": 99,
    "ninety-nine": 99,
    "ninyaanwe": 99,
    "निन्यानवे": 99,
    "hundred": 100,
    "sau": 100,
    "सौ": 100,
}

# Large scale multipliers
MULTIPLIERS: dict[str, int] = {
    "sau": 100,
    "hundred": 100,
    "सौ": 100,
    "hazaar": 1000,
    "hazar": 1000,
    "thousand": 1000,
    "हज़ार": 1000,
    "हजार": 1000,
    "k": 1000,
    "lakh": 100000,
    "lac": 100000,
    "लाख": 100000,
    "crore": 10000000,
    "cr": 10000000,
    "करोड़": 10000000,
    "करोड": 10000000,
}

# Special fraction base words
FRACTION_WORDS: set[str] = {
    "dhai",
    "dhaai",
    "ढाई",
    "derh",
    "dedh",
    "deedh",
    "डेढ़",
    "sawa",
    "सवा",
    "sadhe",
    "saadhe",
    "साढ़े",
    "paune",
    "paun",
    "पौने",
    "पौन",
}


@dataclass(frozen=True)
class ParsedNumber:
    """Structured representation of a recognized numeric entity."""

    value: float
    raw_text: str
    start_char: int
    end_char: int
    confidence: float | None = 1.0


# ---------------------------------------------------------------------------
# Core Normalization & Parsing Engine
# ---------------------------------------------------------------------------


def _clean_token(t: str) -> str:
    """Normalize token by stripping punctuation and lowercasing."""
    return t.strip().lower().strip(",.!?\"'`:;()")


def _parse_digits(text: str) -> float | None:
    """Parse pure numeric strings (e.g. '250', '1,500.50', '₹350')."""
    cleaned = re.sub(r"[^\d.]", "", text.strip())
    if cleaned and cleaned.count(".") <= 1 and any(c.isdigit() for c in cleaned):
        try:
            val = float(cleaned)
            return val
        except ValueError:
            return None
    return None


def parse_spoken_number(text: str) -> float | None:
    """
    Parse a spoken phrase representing an Indian number into an exact float or int.

    Returns None if text does not represent a valid number phrase.
    Does not use probabilistic models or heuristics.
    """
    cleaned_input = text.strip().lower()
    if not cleaned_input:
        return None

    # Check for direct digit string
    direct_val = _parse_digits(cleaned_input)
    if direct_val is not None:
        # If it was a clean digit string (or prefixed by currency/symbol)
        cleaned_no_sym = re.sub(r"^[₹$\s,a-zA-Z]+", "", cleaned_input).strip()
        if re.fullmatch(r"[\d,]+(\.\d+)?", cleaned_no_sym):
            return direct_val

    # Tokenize
    raw_tokens = [t for t in re.split(r"[\s\-]+", cleaned_input) if t]
    tokens = [_clean_token(t) for t in raw_tokens if _clean_token(t)]
    if not tokens:
        return None

    # Remove filler words: "and", "aur", "rupees", "rupaye", "rs"
    clean_tokens: list[str] = []
    for t in tokens:
        if t in ("and", "aur", "और", "bucks"):
            continue
        clean_tokens.append(t)

    if not clean_tokens:
        return None

    # -----------------------------------------------------------------------
    # Pattern 1: Standalone fraction words
    # -----------------------------------------------------------------------
    if len(clean_tokens) == 1:
        tok = clean_tokens[0]
        if tok in ("dhai", "dhaai", "ढाई"):
            return 2.5
        if tok in ("derh", "dedh", "deedh", "डेढ़"):
            return 1.5
        if tok in ("sawa", "सवा"):
            return 1.25
        if tok in ("paun", "paune", "पौने", "पौन"):
            return 0.75
        if tok in NUM_0_TO_100:
            return float(NUM_0_TO_100[tok])

    # -----------------------------------------------------------------------
    # Pattern 2: Fractional Prefix Constructions
    # -----------------------------------------------------------------------
    first = clean_tokens[0]

    # Subpattern: "dhai <multiplier>" (e.g. "dhai sau" = 250, "dhai hazaar" = 2500)
    if first in ("dhai", "dhaai", "ढाई"):
        if len(clean_tokens) >= 2 and clean_tokens[1] in MULTIPLIERS:
            base_mult = MULTIPLIERS[clean_tokens[1]]
            remainder = clean_tokens[2:]
            if remainder:
                rem_val = parse_spoken_number(" ".join(remainder))
                if rem_val is None:
                    return None
                return 2.5 * base_mult + rem_val
            return 2.5 * base_mult
        # e.g. "dhai" + unit/noun handled by caller, bare "dhai" handled above

    # Subpattern: "derh / dedh <multiplier>" (e.g. "derh hazaar" = 1500, "dedh sau" = 150)
    if first in ("derh", "dedh", "deedh", "डेढ़"):
        if len(clean_tokens) >= 2 and clean_tokens[1] in MULTIPLIERS:
            base_mult = MULTIPLIERS[clean_tokens[1]]
            remainder = clean_tokens[2:]
            if remainder:
                rem_val = parse_spoken_number(" ".join(remainder))
                if rem_val is None:
                    return None
                return 1.5 * base_mult + rem_val
            return 1.5 * base_mult

    # Subpattern: "sawa <num> <multiplier>" or "sawa <multiplier>"
    # "sawa sau" = 125 (1.25 * 100), "sawa do sau" = 225 (2 * 100 + 25)
    # "sawa hazaar" = 1250 (1.25 * 1000), "sawa do hazaar" = 2250 (2 * 1000 + 250)
    if first in ("sawa", "सवा"):
        if len(clean_tokens) >= 2:
            second = clean_tokens[1]
            if second in MULTIPLIERS:
                # "sawa sau" (125), "sawa hazaar" (1250), "sawa lakh" (125000)
                base_mult = MULTIPLIERS[second]
                remainder = clean_tokens[2:]
                if remainder:
                    rem_val = parse_spoken_number(" ".join(remainder))
                    if rem_val is None:
                        return None
                    return 1.25 * base_mult + rem_val
                return 1.25 * base_mult
            elif second in NUM_0_TO_100:
                count = NUM_0_TO_100[second]
                if len(clean_tokens) >= 3 and clean_tokens[2] in MULTIPLIERS:
                    # "sawa do sau" -> 225, "sawa teen sau" -> 325
                    # "sawa do hazaar" -> 2250
                    mult = MULTIPLIERS[clean_tokens[2]]
                    remainder = clean_tokens[3:]
                    if remainder:
                        rem_val = parse_spoken_number(" ".join(remainder))
                        if rem_val is None:
                            return None
                        return count * mult + 0.25 * mult + rem_val
                    return count * mult + 0.25 * mult
                elif len(clean_tokens) == 2:
                    # "sawa do" -> 2.25
                    return count + 0.25
                else:
                    return None

    # Subpattern: "sadhe <num> <multiplier>" or "sadhe <num>"
    # "sadhe teen sau" = 350, "sadhe char sau" = 450, "sadhe teen hazaar" = 3500
    if first in ("sadhe", "saadhe", "साढ़े"):
        if len(clean_tokens) >= 2:
            second = clean_tokens[1]
            if second in NUM_0_TO_100:
                count = NUM_0_TO_100[second]
                if len(clean_tokens) >= 3 and clean_tokens[2] in MULTIPLIERS:
                    mult = MULTIPLIERS[clean_tokens[2]]
                    remainder = clean_tokens[3:]
                    if remainder:
                        rem_val = parse_spoken_number(" ".join(remainder))
                        if rem_val is None:
                            return None
                        return count * mult + 0.5 * mult + rem_val
                    return count * mult + 0.5 * mult
                elif len(clean_tokens) == 2:
                    # "sadhe teen" -> 3.5
                    return count + 0.5
                else:
                    return None
            elif second in MULTIPLIERS:
                # Fallback if someone says "sadhe sau" -> 150 (rare, usually dedh sau)
                if len(clean_tokens) == 2:
                    mult = MULTIPLIERS[second]
                    return 1.5 * mult
                return None

    # Subpattern: "paune <num> <multiplier>" or "paune <multiplier>"
    # "paune do sau" = 175 (2 * 100 - 25)
    # "paune teen sau" = 275 (3 * 100 - 25)
    # "paune sau" / "paun sau" = 75 (100 - 25)
    # "paune do hazaar" = 1750 (2 * 1000 - 250)
    # "paune do" = 1.75
    if first in ("paune", "paun", "पौने", "पौन"):
        if len(clean_tokens) >= 2:
            second = clean_tokens[1]
            if second in MULTIPLIERS:
                # "paune sau" -> 75, "paune hazaar" -> 750
                mult = MULTIPLIERS[second]
                remainder = clean_tokens[2:]
                if remainder:
                    rem_val = parse_spoken_number(" ".join(remainder))
                    if rem_val is None:
                        return None
                    return 0.75 * mult + rem_val
                return 0.75 * mult
            elif second in NUM_0_TO_100:
                count = NUM_0_TO_100[second]
                if len(clean_tokens) >= 3 and clean_tokens[2] in MULTIPLIERS:
                    mult = MULTIPLIERS[clean_tokens[2]]
                    remainder = clean_tokens[3:]
                    if remainder:
                        rem_val = parse_spoken_number(" ".join(remainder))
                        if rem_val is None:
                            return None
                        return (count - 1) * mult + 0.75 * mult + rem_val
                    return (count - 1) * mult + 0.75 * mult
                elif len(clean_tokens) == 2:
                    # "paune do" -> 1.75
                    return (count - 1) + 0.75
                else:
                    return None

    # -----------------------------------------------------------------------
    # Pattern 3: Standard Compound Multiplicative Additive Numbers
    # (e.g. "teen hazaar paanch sau", "do lakh pachaas hazaar", "pachees sau", "two fifty")
    # -----------------------------------------------------------------------
    total = 0.0
    current_acc = 0.0
    matched_any = False

    i = 0
    while i < len(clean_tokens):
        tok = clean_tokens[i]

        # Check raw digits token (e.g. "500", "50")
        if re.fullmatch(r"\d+(\.\d+)?", tok):
            val = float(tok)
            matched_any = True
            if current_acc == 0:
                current_acc = val
            else:
                total += current_acc
                current_acc = val
            i += 1
            continue

        # Check multiplier (sau, hazaar, lakh, crore)
        if tok in MULTIPLIERS:
            mult = MULTIPLIERS[tok]
            matched_any = True
            if current_acc == 0.0:
                current_acc = 1.0 * mult
            else:
                current_acc = current_acc * mult

            if mult >= 1000:
                total += current_acc
                current_acc = 0.0
            i += 1
            continue

        # Check 0-100 vocabulary
        if tok in NUM_0_TO_100:
            val = float(NUM_0_TO_100[tok])
            matched_any = True
            # Check for colloquial Indian English compounds like "two fifty" -> 250
            if current_acc in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0) and 10 <= val <= 99:
                # "two fifty" -> 250, "three forty" -> 340
                current_acc = current_acc * 100 + val
            elif current_acc == 0:
                current_acc = val
            else:
                # e.g. "twenty five"
                current_acc += val
            i += 1
            continue

        # Unrecognized token in candidate number sequence
        return None

    if not matched_any:
        return None

    total += current_acc
    return total


def extract_numbers(text: str) -> list[ParsedNumber]:
    """
    Extract all spoken and numeric number instances from a natural language text.

    Finds substrings that parse into valid numbers and returns non-overlapping
    ParsedNumber entities ordered by start position.
    """
    results: list[ParsedNumber] = []
    # Tokenize text with span boundaries
    tokens_with_spans: list[tuple[str, int, int]] = []
    for match in re.finditer(r"\S+", text):
        clean = _clean_token(match.group())
        if clean:
            tokens_with_spans.append((clean, match.start(), match.end()))

    n = len(tokens_with_spans)
    visited_idx: set[int] = set()

    # Greedy maximal matching (from longest window down to single tokens)
    for length in range(min(n, 6), 0, -1):
        for i in range(n - length + 1):
            indices = set(range(i, i + length))
            if any(idx in visited_idx for idx in indices):
                continue

            window_tokens = [tokens_with_spans[j][0] for j in range(i, i + length)]
            window_str = " ".join(window_tokens)

            val = parse_spoken_number(window_str)
            if val is not None:
                start_c = tokens_with_spans[i][1]
                end_c = tokens_with_spans[i + length - 1][2]
                raw_substring = text[start_c:end_c]

                results.append(
                    ParsedNumber(
                        value=val,
                        raw_text=raw_substring,
                        start_char=start_c,
                        end_char=end_c,
                        confidence=1.0,
                    )
                )
                for idx in indices:
                    visited_idx.add(idx)

    # Sort by start_char
    results.sort(key=lambda r: r.start_char)
    return results
