"""
Deterministic spoken number parser and generator for Bengali (বাংলা) and Romanized Bengali.

Strictly deterministic, zero-dependency, zero-LLM.
Covers:
- Standard digits and Bengali script numerals (০-৯)
- Numbers 0 to 100 in Bengali script, Romanized Bengali, and English
- Multipliers: sho / eksho (100), hajaar (1,000), laakh (100,000), koti (10,000,000)
- Colloquial fractional prefixes:
    * aadhai / dhai / arai / আড়াই (2.5x base): aadhai sho = 250, aadhai hajaar = 2500
    * derh / dedh / দেড় (1.5x base): derh hajaar = 1500, derh sho = 150
    * shoya / sawa / সোয়া (+0.25 of unit): shoya sho = 125, shoya dui sho = 225, shoya hajaar = 1250
    * shaadhe / sadhe / সাড়ে (+0.5 of unit for >= 3): shaadhe teen sho = 350, shaadhe chaar sho = 450
    * poune / paune / পৌনে (-0.25 of unit): poune dui sho = 175, poune teen hajaar = 2750
- Compound structures: teen hajaar paanch sho = 3500, pochish sho = 2500
- Currency & units: taka (টাকা), poisha (পয়সা), kilo/keji (কেজি), gram (গ্রাম), litre (লিটার), darjan (ডজন), hali (হালি)
"""

from __future__ import annotations

import re

from bolkhata.domains.common.numbers import ParsedNumber

# ---------------------------------------------------------------------------
# Bengali 0-100 Lexicon
# ---------------------------------------------------------------------------

BN_NUM_0_TO_100: dict[str, int] = {
    # 0
    "shunyo": 0,
    "shunya": 0,
    "zero": 0,
    "শূন্য": 0,
    "০": 0,
    "0": 0,
    # 1-10
    "ek": 1,
    "aik": 1,
    "এক": 1,
    "১": 1,
    "1": 1,
    "dui": 2,
    "duto": 2,
    "do": 2,
    "দুই": 2,
    "দুটো": 2,
    "২": 2,
    "2": 2,
    "teen": 3,
    "tin": 3,
    "tinta": 3,
    "তিন": 3,
    "তিনটে": 3,
    "৩": 3,
    "3": 3,
    "chaar": 4,
    "char": 4,
    "charta": 4,
    "চার": 4,
    "চারটে": 4,
    "৪": 4,
    "4": 4,
    "paanch": 5,
    "panch": 5,
    "panchta": 5,
    "পাঁচ": 5,
    "পাঁচটা": 5,
    "৫": 5,
    "5": 5,
    "chhoy": 6,
    "choy": 6,
    "chhe": 6,
    "ছয়": 6,
    "ছোয়": 6,
    "৬": 6,
    "6": 6,
    "saat": 7,
    "sat": 7,
    "shat": 7,
    "সাত": 7,
    "৭": 7,
    "7": 7,
    "aat": 8,
    "at": 8,
    "আট": 8,
    "৮": 8,
    "8": 8,
    "noy": 9,
    "noi": 9,
    "নয়": 9,
    "৯": 9,
    "9": 9,
    "dosh": 10,
    "doshta": 10,
    "দশ": 10,
    "১০": 10,
    # 11-20
    "egaro": 11,
    "এগারো": 11,
    "১১": 11,
    "baro": 12,
    "বারো": 12,
    "১২": 12,
    "tero": 13,
    "তেরো": 13,
    "১৩": 13,
    "choddo": 14,
    "chouddo": 14,
    "চৌদ্দ": 14,
    "১৪": 14,
    "ponero": 15,
    "ponro": 15,
    "পনেরো": 15,
    "১৫": 15,
    "sholo": 16,
    "ষোল": 16,
    "১৬": 16,
    "shotro": 17,
    "shotoro": 17,
    "সতেরো": 17,
    "১৭": 17,
    "atharo": 18,
    "আঠারো": 18,
    "১৮": 18,
    "unish": 19,
    "উনিশ": 19,
    "১৯": 19,
    "kuri": 20,
    "bish": 20,
    "কুড়ি": 20,
    "বিশ": 20,
    "২০": 20,
    # 21-30
    "ekush": 21,
    "একুশ": 21,
    "২১": 21,
    "baish": 22,
    "বাইশ": 22,
    "২২": 22,
    "teish": 23,
    "তেইশ": 23,
    "২৩": 23,
    "chobbish": 24,
    "চব্বিশ": 24,
    "২৪": 24,
    "pochish": 25,
    "পঁচিশ": 25,
    "২৫": 25,
    "chabbish": 26,
    "ছাব্বিশ": 26,
    "২৬": 26,
    "shatash": 27,
    "সাতাশ": 27,
    "২৭": 27,
    "athash": 28,
    "আঠাশ": 28,
    "২৮": 28,
    "untrish": 29,
    "উনত্রিশ": 29,
    "২৯": 29,
    "trish": 30,
    "ত্রিশ": 30,
    "তিরিশ": 30,
    "৩০": 30,
    # 31-40
    "ektrish": 31,
    "একত্রিশ": 31,
    "৩১": 31,
    "bottrish": 32,
    "বত্রিশ": 32,
    "৩২": 32,
    "tetrish": 33,
    "তেত্রিশ": 33,
    "৩৩": 33,
    "choutrish": 34,
    "চৌত্রিশ": 34,
    "৩৪": 34,
    "poitrish": 35,
    "পঁয়ত্রিশ": 35,
    "৩৫": 35,
    "chhottrish": 36,
    "ছত্রিশ": 36,
    "৩৬": 36,
    "shaittrish": 37,
    "সাঁইত্রিশ": 37,
    "৩৭": 37,
    "athtrish": 38,
    "আটত্রিশ": 38,
    "৩৮": 38,
    "unchollish": 39,
    "উনচল্লিশ": 39,
    "৩৯": 39,
    "chollish": 40,
    "চল্লিশ": 40,
    "৪০": 40,
    # 41-50
    "ekchollish": 41,
    "একচল্লিশ": 41,
    "৪১": 41,
    "biyallish": 42,
    "বিয়াল্লিশ": 42,
    "৪২": 42,
    "tetallish": 43,
    "তেতাল্লিশ": 43,
    "৪৩": 43,
    "chuallish": 44,
    "চুয়াল্লিশ": 44,
    "৪৪": 44,
    "poentallish": 45,
    "পঁয়তাল্লিশ": 45,
    "৪৫": 45,
    "chetallish": 46,
    "ছেচল্লিশ": 46,
    "৪৬": 46,
    "shatcallish": 47,
    "সাতচল্লিশ": 47,
    "৪৭": 47,
    "athcallish": 48,
    "আটচল্লিশ": 48,
    "৪৮": 48,
    "unoponchash": 49,
    "উনপঞ্চাশ": 49,
    "৪৯": 49,
    "ponchash": 50,
    "পঞ্চাশ": 50,
    "৫০": 50,
    # 51-60
    "ekanno": 51,
    "একান্ন": 51,
    "৫১": 51,
    "baanno": 52,
    "বায়ান্ন": 52,
    "৫২": 52,
    "teppanno": 53,
    "তিপ্পান্ন": 53,
    "৫৩": 53,
    "chuanno": 54,
    "চুয়ান্ন": 54,
    "৫৪": 54,
    "ponchanno": 55,
    "পঞ্চান্ন": 55,
    "৫৫": 55,
    "chappanno": 56,
    "ছাপ্পান্ন": 56,
    "৫৬": 56,
    "shatanno": 57,
    "সাতান্ন": 57,
    "৫৭": 57,
    "athanno": 58,
    "আটান্ন": 58,
    "৫৮": 58,
    "unoshath": 59,
    "উনষাট": 59,
    "৫৯": 59,
    "shaath": 60,
    "ষাট": 60,
    "৬০": 60,
    # 61-70
    "ekshotti": 61,
    "একষট্টি": 61,
    "৬১": 61,
    "bashotti": 62,
    "বাষট্টি": 62,
    "৬২": 62,
    "teshotti": 63,
    "তেষট্টি": 63,
    "৬৩": 63,
    "choushotti": 64,
    "চৌষট্টি": 64,
    "৬৪": 64,
    "poeshotti": 65,
    "পঁয়ষট্টি": 65,
    "৬৫": 65,
    "cheshotti": 66,
    "ছেষট্টি": 66,
    "৬৬": 66,
    "shatshotti": 67,
    "সাতষট্টি": 67,
    "৬৭": 67,
    "athshotti": 68,
    "আটষট্টি": 68,
    "৬৮": 68,
    "unoshottor": 69,
    "উনসত্তর": 69,
    "৬৯": 69,
    "shottor": 70,
    "সত্তর": 70,
    "৭০": 70,
    # 71-80
    "ekattor": 71,
    "একাত্তর": 71,
    "৭১": 71,
    "bahattor": 72,
    "বাহাত্তর": 72,
    "৭২": 72,
    "tehattor": 73,
    "তিয়াত্তর": 73,
    "৭৩": 73,
    "chouhattor": 74,
    "চুয়াত্তর": 74,
    "৭৪": 74,
    "pochattor": 75,
    "পঁচাত্তর": 75,
    "৭৫": 75,
    "cheyattor": 76,
    "ছিয়াত্তর": 76,
    "৭৬": 76,
    "shatattor": 77,
    "সাতাত্তর": 77,
    "৭৭": 77,
    "athattor": 78,
    "আটাত্তর": 78,
    "৭৮": 78,
    "unonashshi": 79,
    "উনাশি": 79,
    "৭৯": 79,
    "ashshi": 80,
    "aashi": 80,
    "আশি": 80,
    "আশী": 80,
    "৮০": 80,
    # 81-90
    "ekashi": 81,
    "একাশি": 81,
    "৮১": 81,
    "birashi": 82,
    "বিরাশি": 82,
    "৮২": 82,
    "terashi": 83,
    "তিরাশি": 83,
    "৮৩": 83,
    "chourashi": 84,
    "চৌরাশি": 84,
    "৮৪": 84,
    "pochashi": 85,
    "পঁচাশি": 85,
    "৮৫": 85,
    "cheyashi": 86,
    "ছিয়াশি": 86,
    "৮৬": 86,
    "shatashi": 87,
    "সাতাশি": 87,
    "৮৭": 87,
    "athashi": 88,
    "আটাশি": 88,
    "৮৮": 88,
    "unonobbui": 89,
    "উননব্বই": 89,
    "৮৯": 89,
    "nobbui": 90,
    "nobboi": 90,
    "নব্বই": 90,
    "৯০": 90,
    # 91-100
    "ekanobbui": 91,
    "একানব্বই": 91,
    "৯১": 91,
    "biranobbui": 92,
    "বিরানব্বই": 92,
    "৯২": 92,
    "teranobbui": 93,
    "তিরানব্বই": 93,
    "৯৩": 93,
    "chouranobbui": 94,
    "চৌরানব্বই": 94,
    "৯৪": 94,
    "pochanobbui": 95,
    "পঁচানব্বই": 95,
    "৯৫": 95,
    "chiyanobbui": 96,
    "ছিয়ানব্বই": 96,
    "৯৬": 96,
    "shatanobbui": 97,
    "সাতানব্বই": 97,
    "৯৭": 97,
    "athanobbui": 98,
    "আটানব্বই": 98,
    "৯৮": 98,
    "niranobbui": 99,
    "নিরানব্বই": 99,
    "৯৯": 99,
    "eksho": 100,
    "sho": 100,
    "ek\u00a0sho": 100,
    "একশ": 100,
    "একশো": 100,
    "শত": 100,
    "১০০": 100,
}

# Multipliers
BN_MULTIPLIERS: dict[str, int] = {
    "sho": 100,
    "shoo": 100,
    "eksho": 100,
    "sau": 100,
    "শত": 100,
    "একশ": 100,
    "একশো": 100,
    "দুইশ": 200,
    "দুইশো": 200,
    "তিনশ": 300,
    "তিনশো": 300,
    "চারশ": 400,
    "চারশো": 400,
    "পাঁচশ": 500,
    "পাঁচশো": 500,
    "ছয়শ": 600,
    "সাতশ": 700,
    "আটশ": 800,
    "নয়শ": 900,
    "hajaar": 1_000,
    "hajar": 1_000,
    "hazar": 1_000,
    "হাজার": 1_000,
    "laakh": 100_000,
    "lakh": 100_000,
    "লাখ": 100_000,
    "লক্ষ": 100_000,
    "koti": 10_000_000,
    "krore": 10_000_000,
    "crore": 10_000_000,
    "কোটি": 10_000_000,
}

# Fractions
BN_FRACTIONS: dict[str, float] = {
    "derh": 1.5,
    "dedh": 1.5,
    "দেড়": 1.5,
    "dhai": 2.5,
    "dhaai": 2.5,
    "aadhai": 2.5,
    "adhai": 2.5,
    "arai": 2.5,
    "আড়াই": 2.5,
    "আড়াই": 2.5,
    "aadh": 0.5,
    "aadha": 0.5,
    "adha": 0.5,
    "আধ": 0.5,
    "আধা": 0.5,
    "shoya": 1.25,
    "sawa": 1.25,
    "সোয়া": 1.25,
    "সোয়া": 1.25,
    "shaadhe": 0.5,  # +0.5 for unit >= 3
    "sadhe": 0.5,
    "সাড়ে": 0.5,
    "সাড়ে": 0.5,
    "poune": -0.25,  # -0.25
    "paune": -0.25,
    "paun": -0.25,
    "পৌনে": -0.25,
}

# Currency tokens
BN_CURRENCY: set[str] = {
    "taka",
    "taaka",
    "tk",
    "টাকা",
    "টাকায়",
    "poisha",
    "poisa",
    "পয়সা",
    "পয়সা",
    "rupaye",
    "rupiya",
    "rs",
    "₹",
}

# Units tokens
BN_UNITS: dict[str, str] = {
    "keji": "kg",
    "kilo": "kg",
    "kg": "kg",
    "কেজি": "kg",
    "কিলো": "kg",
    "gram": "g",
    "gm": "g",
    "g": "g",
    "গ্রাম": "g",
    "litre": "l",
    "liter": "l",
    "lit": "l",
    "লিটার": "l",
    "darjan": "dozen",
    "dorjon": "dozen",
    "dozen": "dozen",
    "ডজন": "dozen",
    "hali": "hali",  # 4 units in Bengali commerce
    "হালি": "hali",
    "packet": "packet",
    "pyaket": "packet",
    "প্যাকেট": "packet",
}


def _clean_token(t: str) -> str:
    """Strip common punctuation from a token without removing Indic vowel marks/matras."""
    return t.strip(" \t\n\r,.;:!?()[]\"'|।-–—").lower()


def _convert_bengali_digits(text: str) -> str:
    """Convert Bengali numerals (০-৯) to ASCII digits (0-9)."""
    bn_digits = "০১২৩৪৫৬৭৮৯"
    for i, char in enumerate(bn_digits):
        text = text.replace(char, str(i))
    return text


def parse_spoken_bengali_number(text: str) -> float | None:
    """
    Parse a spoken Bengali number string into a numeric float or int.
    Deterministic, zero-LLM.
    """
    text_clean = text.strip()
    if not text_clean:
        return None

    # Step 1: Check if input is standard digits or Bengali numerals
    text_ascii = _convert_bengali_digits(text_clean)
    num_match = re.fullmatch(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*$", text_ascii.replace(",", ""))
    if num_match:
        val = float(num_match.group(1))
        return int(val) if val.is_integer() else val

    # Step 2: Tokenize
    raw_tokens = text_clean.split()
    tokens = [_clean_token(t) for t in raw_tokens if _clean_token(t)]
    if not tokens:
        return None

    # Single token exact lookup
    if len(tokens) == 1:
        tok = tokens[0]
        tok_ascii = _convert_bengali_digits(tok)
        if tok in BN_NUM_0_TO_100:
            return BN_NUM_0_TO_100[tok]
        if tok in BN_MULTIPLIERS:
            return BN_MULTIPLIERS[tok]
        if tok_ascii.isdigit():
            return int(tok_ascii)
        return None

    # Check for colloquial fraction prefixes
    # Case A: derh / aadhai + multiplier (e.g. "derh hajaar" = 1500, "aadhai sho" = 250)
    if tokens[0] in (
        "derh",
        "dedh",
        "দেড়",
        "dhai",
        "dhaai",
        "aadhai",
        "adhai",
        "arai",
        "আড়াই",
        "আড়াই",
    ):
        frac_mult = 1.5 if tokens[0] in ("derh", "dedh", "দেড়") else 2.5
        if len(tokens) >= 2 and tokens[1] in BN_MULTIPLIERS:
            base_mult = BN_MULTIPLIERS[tokens[1]]
            val = frac_mult * base_mult
            # Check trailing tokens
            if len(tokens) == 2:
                return int(val)
            rem = parse_spoken_bengali_number(" ".join(tokens[2:]))
            return int(val + (rem or 0))

    # Case B: shoya (sawa) + base:
    # "shoya sho" = 125, "shoya hajaar" = 1250, "shoya dui sho" = 225
    if tokens[0] in ("shoya", "sawa", "সোয়া", "সোয়া"):
        if len(tokens) >= 2:
            if tokens[1] in BN_MULTIPLIERS:
                base = BN_MULTIPLIERS[tokens[1]]
                return int(1.25 * base)
            # "shoya dui sho"
            if len(tokens) >= 3 and tokens[1] in BN_NUM_0_TO_100 and tokens[2] in BN_MULTIPLIERS:
                n = BN_NUM_0_TO_100[tokens[1]]
                mult = BN_MULTIPLIERS[tokens[2]]
                # e.g., 2.25 * 100 = 225
                return int((n + 0.25) * mult)

    # Case C: shaadhe (sadhe) + count + multiplier:
    # "shaadhe teen sho" = 350, "shaadhe chaar hajaar" = 4500, "সাড়ে তিনশ" = 350
    if tokens[0] in ("shaadhe", "sadhe", "সাড়ে", "সাড়ে"):
        compound_hundreds = {
            "তিনশ": 3,
            "তিনশো": 3,
            "চারশ": 4,
            "চারশো": 4,
            "পাঁচশ": 5,
            "পাঁচশো": 5,
            "ছয়শ": 6,
            "সাতশ": 7,
            "আটশ": 8,
            "নয়শ": 9,
        }
        if len(tokens) >= 2 and tokens[1] in compound_hundreds:
            n = compound_hundreds[tokens[1]]
            return int((n + 0.5) * 100)
        if len(tokens) >= 3 and tokens[1] in BN_NUM_0_TO_100 and tokens[2] in BN_MULTIPLIERS:
            n = BN_NUM_0_TO_100[tokens[1]]
            mult = BN_MULTIPLIERS[tokens[2]]
            val = (n + 0.5) * mult
            if len(tokens) == 3:
                return int(val)
            rem = parse_spoken_bengali_number(" ".join(tokens[3:]))
            return int(val + (rem or 0))

    # Case D: poune (paune) + count + multiplier:
    # "poune dui sho" = 175, "poune teen hajaar" = 2750, "পৌনে দুইশ" = 175
    if tokens[0] in ("poune", "paune", "paun", "পৌনে"):
        compound_hundreds_poune = {
            "দুইশ": 2,
            "দুইশো": 2,
            "তিনশ": 3,
            "তিনশো": 3,
            "চারশ": 4,
            "চারশো": 4,
            "পাঁচশ": 5,
            "পাঁচশো": 5,
            "ছয়শ": 6,
            "সাতশ": 7,
            "আটশ": 8,
            "নয়শ": 9,
        }
        if len(tokens) >= 2 and tokens[1] in compound_hundreds_poune:
            n = compound_hundreds_poune[tokens[1]]
            return int((n - 0.25) * 100)
        if len(tokens) >= 3 and tokens[1] in BN_NUM_0_TO_100 and tokens[2] in BN_MULTIPLIERS:
            n = BN_NUM_0_TO_100[tokens[1]]
            mult = BN_MULTIPLIERS[tokens[2]]
            val = (n - 0.25) * mult
            if len(tokens) == 3:
                return int(val)
            rem = parse_spoken_bengali_number(" ".join(tokens[3:]))
            return int(val + (rem or 0))

    # Standard compound parsing (e.g., "teen hajaar paanch sho" = 3500)
    total = 0
    current = 0
    parsed_any = False

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        tok_ascii = _convert_bengali_digits(tok)

        if tok in BN_MULTIPLIERS:
            mult = BN_MULTIPLIERS[tok]
            if current == 0:
                current = 1
            if mult >= 1000:
                total += current * mult
                current = 0
            else:
                current = current * mult
            parsed_any = True
        elif tok in BN_NUM_0_TO_100:
            val = BN_NUM_0_TO_100[tok]
            current += val
            parsed_any = True
        elif tok_ascii.isdigit():
            current += int(tok_ascii)
            parsed_any = True
        else:
            # Unrecognized token in sequence
            return None
        i += 1

    total += current
    return total if parsed_any else None


def extract_bengali_numbers(text: str) -> list[ParsedNumber]:
    """Extract all numbers from text using sliding window recognition."""
    results: list[ParsedNumber] = []
    tokens = text.split()
    n = len(tokens)
    i = 0

    while i < n:
        matched = False
        # Try largest window down to 1
        for length in range(min(5, n - i), 0, -1):
            sub = " ".join(tokens[i : i + length])
            val = parse_spoken_bengali_number(sub)
            if val is not None:
                results.append(
                    ParsedNumber(
                        raw_text=sub,
                        value=float(val),
                        start_char=text.find(sub),
                        end_char=text.find(sub) + len(sub),
                        confidence=1.0,
                    )
                )
                i += length
                matched = True
                break
        if not matched:
            i += 1

    return results


def number_to_bengali_words(number: int | float, script: str = "native") -> str:
    """
    Deterministic conversion of numeric value to Bengali words.
    script can be 'native' (বাংলা) or 'roman' (Bengali in Roman letters).
    """
    if number < 0:
        prefix = "মাইনাস " if script == "native" else "minus "
        return prefix + number_to_bengali_words(abs(number), script)

    int_val = int(number)
    if int_val == 0:
        return "শূন্য" if script == "native" else "shunyo"

    parts: list[str] = []

    # Koti (10,000,000)
    koti = int_val // 10_000_000
    if koti > 0:
        parts.append(number_to_bengali_words(koti, script))
        parts.append("কোটি" if script == "native" else "koti")
        int_val %= 10_000_000

    # Lakh (100,000)
    lakh = int_val // 100_000
    if lakh > 0:
        parts.append(number_to_bengali_words(lakh, script))
        parts.append("লাখ" if script == "native" else "laakh")
        int_val %= 100_000

    # Hajaar (1,000)
    hajar = int_val // 1_000
    if hajar > 0:
        parts.append(number_to_bengali_words(hajar, script))
        parts.append("হাজার" if script == "native" else "hajaar")
        int_val %= 1_000

    # Sho (100)
    sho = int_val // 100
    if sho > 0:
        if sho == 1:
            parts.append("একশ" if script == "native" else "eksho")
        else:
            parts.append(number_to_bengali_words(sho, script))
            parts.append("শো" if script == "native" else "sho")
        int_val %= 100

    # Remaining 1-99
    if int_val > 0:
        # Find token in BN_NUM_0_TO_100
        found = False
        for tok, num in BN_NUM_0_TO_100.items():
            if num == int_val:
                is_bn = any("\u0980" <= c <= "\u09ff" for c in tok)
                if (script == "native" and is_bn) or (
                    script == "roman" and not is_bn and not tok.isdigit()
                ):
                    parts.append(tok)
                    found = True
                    break
        if not found:
            parts.append(str(int_val))

    return " ".join(parts)


class BengaliNumberParser:
    """Pluggable Bengali Spoken Number Parser implementing NumberParser protocol."""

    @property
    def language_code(self) -> str:
        return "bn"

    def parse_spoken_number(self, text: str) -> float | None:
        return parse_spoken_bengali_number(text)

    def extract_numbers(self, text: str) -> list[ParsedNumber]:
        return extract_bengali_numbers(text)

    def number_to_words(self, number: int | float, script: str = "native") -> str:
        return number_to_bengali_words(number, script)
