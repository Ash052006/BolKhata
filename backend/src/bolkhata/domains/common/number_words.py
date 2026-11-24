"""
Deterministic conversion of numbers to spoken Hindi (Roman & Devanagari) and English words.

Strictly deterministic, zero-dependency, zero-LLM.
Used for financial read-back confirmation so amounts are spoken exactly as persisted.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Hindi 0-99 mapping (Romanized and Devanagari)
# ---------------------------------------------------------------------------

HINDI_NUMBERS_0_TO_99: dict[int, tuple[str, str]] = {
    0: ("shunya", "शून्य"),
    1: ("ek", "एक"),
    2: ("do", "दो"),
    3: ("teen", "तीन"),
    4: ("char", "चार"),
    5: ("panch", "पांच"),
    6: ("chhah", "छह"),
    7: ("saat", "सात"),
    8: ("aath", "आठ"),
    9: ("nau", "नौ"),
    10: ("das", "दस"),
    11: ("gyarah", "ग्यारह"),
    12: ("barah", "बारह"),
    13: ("terah", "तेरह"),
    14: ("chaudah", "चौदह"),
    15: ("pandrah", "पंद्रह"),
    16: ("solah", "सोलह"),
    17: ("satrah", "सत्रह"),
    18: ("atharah", "अठारह"),
    19: ("unnis", "उन्नीस"),
    20: ("bees", "बीस"),
    21: ("ikkis", "इक्कीस"),
    22: ("baees", "बाईस"),
    23: ("teis", "तेईस"),
    24: ("chaubees", "चौबीस"),
    25: ("pachchis", "पच्चीस"),
    26: ("chhabbees", "छब्बीस"),
    27: ("sattaees", "सत्ताईस"),
    28: ("atthaees", "अट्ठाईस"),
    29: ("untees", "उनतीस"),
    30: ("tees", "तीस"),
    31: ("ikattis", "इकत्तीस"),
    32: ("battis", "बत्तीस"),
    33: ("tentis", "तैंतीस"),
    34: ("chauntis", "चौंतीस"),
    35: ("paintis", "पैंतीस"),
    36: ("chhattis", "छत्तीस"),
    37: ("saintis", "सैंतीस"),
    38: ("adhtis", "अड़तीस"),
    39: ("untalis", "उनतालीस"),
    40: ("chalis", "चालीस"),
    41: ("iktalis", "इकतालीस"),
    42: ("bayalis", "बयालीस"),
    43: ("taintalis", "तैंतालीस"),
    44: ("chawalis", "चवालीस"),
    45: ("paintalis", "पैंतालीस"),
    46: ("chhiyalis", "छियालीस"),
    47: ("saintalis", "सैंतालीस"),
    48: ("adtalis", "अड़तालीस"),
    49: ("unchas", "उनचास"),
    50: ("pachaas", "पचास"),
    51: ("ikkyawan", "इक्यावन"),
    52: ("bawan", "बावन"),
    53: ("tirepan", "तिरेपन"),
    54: ("chauwan", "चौवन"),
    55: ("pachpan", "पचपन"),
    56: ("chhappan", "छप्पन"),
    57: ("sattawan", "सत्तावन"),
    58: ("athawan", "अट्ठावन"),
    59: ("unsath", "उनसठ"),
    60: ("saath", "साठ"),
    61: ("iksath", "इकसठ"),
    62: ("basath", "बासठ"),
    63: ("tirasath", "तिरसठ"),
    64: ("chaunsath", "चौंसठ"),
    65: ("painsath", "पैंसठ"),
    66: ("chhiyasath", "छियासठ"),
    67: ("sarsath", "सरसठ"),
    68: ("adsath", "अड़सठ"),
    69: ("unhattar", "उनहत्तर"),
    70: ("sattar", "सत्तर"),
    71: ("ikhattar", "इकहत्तर"),
    72: ("bahattar", "बहत्तर"),
    73: ("tihattar", "तिहत्तर"),
    74: ("chauhattar", "चौहत्तर"),
    75: ("pachhattar", "पचहत्तर"),
    76: ("chhihattar", "छहत्तर"),
    77: ("sathattar", "सतहत्तर"),
    78: ("athhattar", "अठहत्तर"),
    79: ("unassi", "उन्नासी"),
    80: ("assi", "अस्सी"),
    81: ("ikyassi", "इक्यासी"),
    82: ("bayassi", "बयासी"),
    83: ("tirassi", "तिरासी"),
    84: ("chaurassi", "चौरासी"),
    85: ("pachassi", "पचासी"),
    86: ("chhiyassi", "छियासी"),
    87: ("sattassi", "सत्तासी"),
    88: ("athassi", "अठासी"),
    89: ("nauassi", "नवासी"),
    90: ("nabbe", "नब्बे"),
    91: ("ikyanwe", "इक्यानवे"),
    92: ("banwe", "बानवे"),
    93: ("tiranwe", "तिरानवे"),
    94: ("chauranwe", "चौरानवे"),
    95: ("pachanwe", "पचानवे"),
    96: ("chhiyanwe", "छियानवे"),
    97: ("sattanwe", "सत्तानवे"),
    98: ("anthanwe", "अट्ठानवे"),
    99: ("ninyanwe", "निन्यानवे"),
}

# ---------------------------------------------------------------------------
# English numbers 0-19 and tens
# ---------------------------------------------------------------------------

ENGLISH_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]

ENGLISH_TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]


def number_to_english_words(number: int | float) -> str:
    """Convert a numeric amount into English words, including decimal cents/paise."""
    if math.isnan(number) or math.isinf(number):
        return str(number)

    if number < 0:
        return f"minus {number_to_english_words(-number)}"

    integer_part = int(math.floor(number))
    fractional_part = int(round((number - integer_part) * 100))

    if integer_part == 0 and fractional_part == 0:
        return "zero"

    words: list[str] = []

    def _convert_hundreds(n: int) -> list[str]:
        res: list[str] = []
        if n >= 100:
            res.append(f"{ENGLISH_ONES[n // 100]} hundred")
            n %= 100
        if n >= 20:
            tens_word = ENGLISH_TENS[n // 10]
            rem = n % 10
            if rem > 0:
                res.append(f"{tens_word} {ENGLISH_ONES[rem]}")
            else:
                res.append(tens_word)
        elif n > 0:
            res.append(ENGLISH_ONES[n])
        return res

    # Indian numbering scale: Crores (10^7), Lakhs (10^5), Thousands (10^3), Hundreds
    crores = integer_part // 10000000
    rem = integer_part % 10000000
    lakhs = rem // 100000
    rem = rem % 100000
    thousands = rem // 1000
    rem = rem % 1000
    hundreds = rem

    if crores > 0:
        words.extend(_convert_hundreds(crores))
        words.append("crore")
    if lakhs > 0:
        words.extend(_convert_hundreds(lakhs))
        words.append("lakh")
    if thousands > 0:
        words.extend(_convert_hundreds(thousands))
        words.append("thousand")
    if hundreds > 0 or (crores == 0 and lakhs == 0 and thousands == 0 and integer_part > 0):
        words.extend(_convert_hundreds(hundreds))

    if not words and integer_part == 0:
        words.append("zero")

    main_text = " ".join(words).strip()

    if fractional_part > 0:
        frac_words = " ".join(_convert_hundreds(fractional_part)).strip()
        if main_text == "zero":
            return f"{frac_words} paise"
        return f"{main_text} and {frac_words} paise"

    return main_text


def number_to_hindi_words(number: int | float, devanagari: bool = False) -> str:
    """
    Convert a numeric amount into spoken Hindi words (Romanized or Devanagari).

    Supports Indian numbering scale:
    - Ek / Do ... (1-99)
    - Sau (100)
    - Hazaar (1,000)
    - Lakh (1,00,000)
    - Crore (1,00,00,000)
    """
    if math.isnan(number) or math.isinf(number):
        return str(number)

    if number < 0:
        prefix = "ऋण " if devanagari else "minus "
        return f"{prefix}{number_to_hindi_words(-number, devanagari=devanagari)}"

    integer_part = int(math.floor(number))
    fractional_part = int(round((number - integer_part) * 100))

    if integer_part == 0 and fractional_part == 0:
        return "शून्य" if devanagari else "shunya"

    def _get_name(val: int) -> str:
        entry = HINDI_NUMBERS_0_TO_99.get(val, (str(val), str(val)))
        return entry[1] if devanagari else entry[0]

    scale_sau = "सौ" if devanagari else "sau"
    scale_hazaar = "हज़ार" if devanagari else "hazaar"
    scale_lakh = "लाख" if devanagari else "lakh"
    scale_crore = "करोड़" if devanagari else "crore"
    word_paise = "पैसे" if devanagari else "paise"

    words: list[str] = []

    crores = integer_part // 10000000
    rem = integer_part % 10000000
    lakhs = rem // 100000
    rem = rem % 100000
    thousands = rem // 1000
    rem = rem % 1000
    hundreds = rem // 100
    tens_and_ones = rem % 100

    if crores > 0:
        words.append(f"{_get_name(crores)} {scale_crore}")
    if lakhs > 0:
        words.append(f"{_get_name(lakhs)} {scale_lakh}")
    if thousands > 0:
        words.append(f"{_get_name(thousands)} {scale_hazaar}")
    if hundreds > 0:
        words.append(f"{_get_name(hundreds)} {scale_sau}")
    if tens_and_ones > 0:
        words.append(_get_name(tens_and_ones))

    main_text = " ".join(words).strip()
    if not main_text:
        main_text = "शून्य" if devanagari else "shunya"

    if fractional_part > 0:
        frac_str = f"{_get_name(fractional_part)} {word_paise}"
        if main_text in ("shunya", "शून्य"):
            return frac_str
        return f"{main_text} {frac_str}"

    return main_text


def number_to_digits_spoken(number: int | float, devanagari: bool = False) -> str:
    """
    Format a number digit-by-digit for strict high-risk confirmation.

    Example: 12500 -> 'ek do panch shunya shunya' / 'एक दो पांच शून्य शून्य'
    """
    s = str(int(math.floor(number))) if number == int(number) else f"{number:.2f}"
    res: list[str] = []
    for ch in s:
        if ch == ".":
            res.append("दशमलव" if devanagari else "dashamalav")
        elif ch.isdigit():
            val = int(ch)
            entry = HINDI_NUMBERS_0_TO_99.get(val, (ch, ch))
            res.append(entry[1] if devanagari else entry[0])
    return " ".join(res)
