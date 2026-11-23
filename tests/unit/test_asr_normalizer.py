"""
Unit tests for ASR text normalization policy (strict and tolerant modes).
"""

from bolkhata.eval.normalizer import normalize_text


def test_strict_normalization() -> None:
    # Lowercase & punctuation removal
    assert normalize_text("Hello, World!") == "hello world"
    # Indic danda removal
    assert normalize_text("रमेश जी को ढाई सौ रुपये।") == "रमेश जी को ढाई सौ रुपये"
    # Whitespace collapsing
    assert normalize_text("   dhai   sau \t rupaye \n ") == "dhai sau rupaye"
    # Empty string
    assert normalize_text("") == ""


def test_tolerant_normalization_spelling() -> None:
    # Phonetic Hinglish unification
    ref = "paanch hazaar rupaye"
    hyp = "panch hazar rupee"
    assert normalize_text(ref, mode="tolerant") == normalize_text(hyp, mode="tolerant")

    ref2 = "dhaai sau deedh hazaar"
    hyp2 = "dhai sau dedh hazar"
    assert normalize_text(ref2, mode="tolerant") == normalize_text(hyp2, mode="tolerant")


def test_tolerant_normalization_devanagari_digits_and_nukta() -> None:
    # Devanagari digit mapping to ASCII
    assert normalize_text("१२५ रुपये", mode="tolerant") == "125 रुपये"
    # Nukta unification
    assert normalize_text("ज़्यादा", mode="tolerant") == "ज्यादा"
    assert normalize_text("फ़ोन", mode="tolerant") == "फोन"
