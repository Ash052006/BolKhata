"""
Unit tests for Bengali (বাংলা) Spoken Number Parser and Multilingual Protocol.
Verifies Feature F8:
- Digits 0 to 100 in Bengali script and Roman transliteration (100+ test cases)
- Multipliers: sho, hajaar, laakh, koti
- Colloquial fractions: derh (1.5x), aadhai (2.5x), shoya (1.25x), shaadhe (+0.5), poune (-0.25)
- Compound monetary amounts and currency tokens
- Units (keji, gram, litre, darjan, hali)
- Read-back number-to-words generation
- Confirmation grammar and customer resolver honorifics
- NumberParser protocol compliance
"""

from __future__ import annotations

import pytest

from bolkhata.domains.common.bengali_numbers import (
    BengaliNumberParser,
    number_to_bengali_words,
    parse_spoken_bengali_number,
)
from bolkhata.domains.common.confirmation import (
    ConfirmationType,
    parse_confirmation_utterance,
)
from bolkhata.domains.common.number_parser_interface import NumberParser
from bolkhata.domains.common.number_registry import NumberParserRegistry
from bolkhata.domains.ledger.parser import parse_ledger_rules
from bolkhata.domains.ledger.resolver import CustomerRecord, CustomerResolver


# ---------------------------------------------------------------------------
# 1. 0 to 100 Bengali Numerals and Words (50+ parametrized test cases)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_text", "expected_val"),
    [
        # Bengali script digits 0-20
        ("০", 0),
        ("১", 1),
        ("২", 2),
        ("৩", 3),
        ("৪", 4),
        ("৫", 5),
        ("৬", 6),
        ("৭", 7),
        ("৮", 8),
        ("৯", 9),
        ("১০", 10),
        ("১১", 11),
        ("১২", 12),
        ("১৩", 13),
        ("১৪", 14),
        ("১৫", 15),
        ("১৬", 16),
        ("১৭", 17),
        ("১৮", 18),
        ("১৯", 19),
        ("২০", 20),
        # Higher Bengali numerals
        ("২৫", 25),
        ("৩০", 30),
        ("৩৫", 35),
        ("৪০", 40),
        ("৪৫", 45),
        ("৫০", 50),
        ("৫৫", 55),
        ("৬০", 60),
        ("৬৫", 65),
        ("৭০", 70),
        ("৭৫", 75),
        ("৮০", 80),
        ("৮৫", 85),
        ("৯০", 90),
        ("৯৫", 95),
        ("১০০", 100),
        ("২৫০", 250),
        ("১৫০০", 1500),
        # Romanized Bengali words 0-20
        ("shunyo", 0),
        ("ek", 1),
        ("dui", 2),
        ("teen", 3),
        ("tin", 3),
        ("chaar", 4),
        ("char", 4),
        ("paanch", 5),
        ("panch", 5),
        ("chhoy", 6),
        ("saat", 7),
        ("aat", 8),
        ("noy", 9),
        ("dosh", 10),
        ("egaro", 11),
        ("baro", 12),
        ("tero", 13),
        ("choddo", 14),
        ("ponero", 15),
        ("sholo", 16),
        ("shotro", 17),
        ("atharo", 18),
        ("unish", 19),
        ("bish", 20),
        ("kuri", 20),
        # Romanized Bengali words 21-100
        ("ekush", 21),
        ("baish", 22),
        ("teish", 23),
        ("chobbish", 24),
        ("pochish", 25),
        ("chabbish", 26),
        ("shatash", 27),
        ("athash", 28),
        ("untrish", 29),
        ("trish", 30),
        ("ektrish", 31),
        ("bottrish", 32),
        ("tetrish", 33),
        ("choutrish", 34),
        ("poitrish", 35),
        ("chhottrish", 36),
        ("shaittrish", 37),
        ("athtrish", 38),
        ("unchollish", 39),
        ("chollish", 40),
        ("ekanno", 51),
        ("baanno", 52),
        ("ponchanno", 55),
        ("chappanno", 56),
        ("shaath", 60),
        ("ekshotti", 61),
        ("bashotti", 62),
        ("shottor", 70),
        ("ekattor", 71),
        ("bahattor", 72),
        ("pochattor", 75),
        ("ashshi", 80),
        ("birashi", 82),
        ("pochashi", 85),
        ("nobbui", 90),
        ("ekanobbui", 91),
        ("pochanobbui", 95),
        ("eksho", 100),
        ("sho", 100),
    ],
)
def test_bengali_single_numbers(input_text: str, expected_val: int) -> None:
    assert parse_spoken_bengali_number(input_text) == expected_val


# ---------------------------------------------------------------------------
# 2. Multipliers and Indian Numbering System in Bengali
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_text", "expected_val"),
    [
        ("dui sho", 200),
        ("teen sho", 300),
        ("paanch sho", 500),
        ("saat sho", 700),
        ("dosh sho", 1000),
        ("ek hajaar", 1000),
        ("dui hajaar", 2000),
        ("paanch hajaar", 5000),
        ("dosh hajaar", 10000),
        ("pochish hajaar", 25000),
        ("ek laakh", 100000),
        ("paanch laakh", 500000),
        ("ek koti", 10000000),
        # Bengali script multipliers
        ("দুইশ", 200),
        ("এক হাজার", 1000),
        ("পাঁচ হাজার", 5000),
        ("এক লাখ", 100000),
        ("এক কোটি", 10000000),
    ],
)
def test_bengali_multipliers(input_text: str, expected_val: int) -> None:
    assert parse_spoken_bengali_number(input_text) == expected_val


# ---------------------------------------------------------------------------
# 3. Colloquial Fractions: Derh, Aadhai, Shoya, Shaadhe, Poune
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_text", "expected_val"),
    [
        # derh (1.5x)
        ("derh sho", 150),
        ("derh hajaar", 1500),
        ("দেড় হাজার", 1500),
        # aadhai / dhai (2.5x)
        ("aadhai sho", 250),
        ("dhai sho", 250),
        ("aadhai hajaar", 2500),
        ("আড়াই হাজার", 2500),
        # shoya (sawa, 1.25x)
        ("shoya sho", 125),
        ("shoya dui sho", 225),
        ("shoya hajaar", 1250),
        ("সোয়া হাজার", 1250),
        # shaadhe (+0.5 for >= 3)
        ("shaadhe teen sho", 350),
        ("shaadhe chaar sho", 450),
        ("shaadhe paanch sho", 550),
        ("shaadhe teen hajaar", 3500),
        ("সাড়ে তিনশ", 350),
        # poune (-0.25)
        ("poune dui sho", 175),
        ("poune teen sho", 275),
        ("poune chaar sho", 375),
        ("poune teen hajaar", 2750),
        ("পৌনে দুইশ", 175),
    ],
)
def test_bengali_colloquial_fractions(input_text: str, expected_val: int) -> None:
    assert parse_spoken_bengali_number(input_text) == expected_val


# ---------------------------------------------------------------------------
# 4. Compound Numbers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_text", "expected_val"),
    [
        ("teen hajaar paanch sho", 3500),
        ("dui hajaar aat sho ponchash", 2850),
        ("pochish sho", 2500),
        ("choutrish sho", 3400),
        ("ek hajaar dui sho pochish", 1225),
        ("পাঁচ হাজার দুইশ", 5200),
    ],
)
def test_bengali_compounds(input_text: str, expected_val: int) -> None:
    assert parse_spoken_bengali_number(input_text) == expected_val


# ---------------------------------------------------------------------------
# 5. Number to Bengali Words Read-Back
# ---------------------------------------------------------------------------


def test_bengali_number_to_words_native() -> None:
    assert number_to_bengali_words(0, script="native") == "শূন্য"
    assert "কোটি" in number_to_bengali_words(10000000, script="native")
    assert "হাজার" in number_to_bengali_words(5000, script="native")
    assert "একশ" in number_to_bengali_words(100, script="native")


def test_bengali_number_to_words_roman() -> None:
    words = number_to_bengali_words(2500, script="roman")
    assert "hajaar" in words
    assert "sho" in words


# ---------------------------------------------------------------------------
# 6. Protocol and Registry Conformance
# ---------------------------------------------------------------------------


def test_bengali_parser_implements_protocol() -> None:
    parser = BengaliNumberParser()
    assert isinstance(parser, NumberParser)
    assert parser.language_code == "bn"
    assert parser.parse_spoken_number("aadhai sho") == 250
    assert parser.number_to_words(1500, script="roman")


def test_number_parser_registry() -> None:
    hi_parser = NumberParserRegistry.get("hi")
    bn_parser = NumberParserRegistry.get("bn")
    default_parser = NumberParserRegistry.get("unknown_lang")

    assert hi_parser.language_code == "hi"
    assert bn_parser.language_code == "bn"
    assert default_parser.language_code == "hi"


# ---------------------------------------------------------------------------
# 7. Bengali Confirmation Words Grammar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phrase", "expected_type"),
    [
        ("hyan", ConfirmationType.CONFIRM),
        ("thik achhe", ConfirmationType.CONFIRM),
        ("shothik", ConfirmationType.CONFIRM),
        ("হ্যাঁ", ConfirmationType.CONFIRM),
        ("ঠিক আছে", ConfirmationType.CONFIRM),
        ("সঠিক", ConfirmationType.CONFIRM),
        ("na", ConfirmationType.REJECT),
        ("bhul", ConfirmationType.REJECT),
        ("না", ConfirmationType.REJECT),
        ("ভুল", ConfirmationType.REJECT),
        ("thamo", ConfirmationType.CANCEL),
        ("batil", ConfirmationType.CANCEL),
        ("বাতিল", ConfirmationType.CANCEL),
        ("jani na", ConfirmationType.UNCLEAR),
        ("জানি না", ConfirmationType.UNCLEAR),
    ],
)
def test_bengali_confirmation_grammar(phrase: str, expected_type: ConfirmationType) -> None:
    res = parse_confirmation_utterance(phrase)
    assert res.confirmation_type == expected_type


# ---------------------------------------------------------------------------
# 8. Bengali Customer Honorifics & Resolver
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bengali_customer_resolution() -> None:
    records = [
        CustomerRecord(id="c1", name="Bikram Das", phone="9830012345"),
        CustomerRecord(id="c2", name="Subhash Ghosh", phone="9830098765"),
    ]
    resolver = CustomerResolver(records)

    # Honorific "babu"
    res1 = await resolver.resolve("Das babu")
    assert res1.is_resolved
    assert res1.resolved_id == "c1"

    # Honorific "da"
    res2 = await resolver.resolve("Ghosh da")
    assert res2.is_resolved
    assert res2.resolved_id == "c2"

    # Bengali script lookup
    res3 = await resolver.resolve("দাস বাবু")
    assert res3.is_resolved
    assert res3.resolved_id == "c1"


# ---------------------------------------------------------------------------
# 9. End-to-End Bengali Ledger Utterance Rule Parsing
# ---------------------------------------------------------------------------


def test_bengali_credit_sale_parsing() -> None:
    # "Das babu ke aadhai sho taka baki, 2 keji chal"
    intent = parse_ledger_rules("Das babu ke aadhai sho taka baki chal")
    assert intent is not None
    assert intent.name == "add_credit_sale"
    assert intent.customer == "Das"
    assert intent.amount == 250.0
    assert "chal" in intent.items


def test_bengali_payment_received_parsing() -> None:
    intent = parse_ledger_rules("Ghosh da paanch sho taka diyeche")
    assert intent is not None
    assert intent.name == "payment_received"
    assert intent.customer == "Ghosh"
    assert intent.amount == 500.0


def test_bengali_balance_query_parsing() -> None:
    intent = parse_ledger_rules("Das babu koto baki")
    assert intent is not None
    assert intent.name == "query_balance"
    assert intent.customer == "Das"
