"""
Unit tests for VocabularyProvider and post-ASR token biasing.
"""

from __future__ import annotations

from bolkhata.domains.ledger.vocabulary import VocabularyProvider


def test_vocabulary_provider_disabled() -> None:
    provider = VocabularyProvider(
        customer_names=["Sharma ji", "Gupta ji"],
        enabled=False,
    )
    assert provider.get_initial_prompt() is None
    text, corrections = provider.correct_tokens("Sarma ji ko 500 udhaar")
    assert text == "Sarma ji ko 500 udhaar"
    assert corrections == []


def test_vocabulary_prompt_construction() -> None:
    provider = VocabularyProvider(
        customer_names=["Sharma ji", "Verma ji", "Gupta ji"],
        item_names=["chawal", "atta", "cheeni"],
        enabled=True,
        max_prompt_chars=100,
    )
    prompt = provider.get_initial_prompt()
    assert prompt is not None
    assert "Sharma ji" in prompt
    assert len(prompt) <= 100


def test_vocabulary_prompt_truncation() -> None:
    # Test that truncation respects comma boundary
    long_names = [f"CustomerNameLongFormat{i} Ji" for i in range(20)]
    provider = VocabularyProvider(
        customer_names=long_names,
        enabled=True,
        max_prompt_chars=50,
    )
    prompt = provider.get_initial_prompt()
    assert prompt is not None
    assert len(prompt) <= 50
    assert not prompt.endswith(",")


def test_post_asr_token_correction_customer() -> None:
    provider = VocabularyProvider(
        customer_names=["Sharma ji", "Ramesh"],
        enabled=True,
    )
    # "Sarma" near-miss to "Sharma"
    raw_text = "Sarma ji ko 200 udhaar"
    corrected, corrections = provider.correct_tokens(raw_text, similarity_threshold=0.8)
    assert "Sharma ji" in corrected
    assert len(corrections) == 1
    assert corrections[0]["original"] == "Sarma"
    assert corrections[0]["corrected"] == "Sharma ji"
    assert corrections[0]["category"] == "customer"
    assert corrections[0]["provenance"] == "rules_vocabulary_bias"


def test_post_asr_token_correction_commodity() -> None:
    provider = VocabularyProvider(
        item_names=["chawal", "cheeni"],
        enabled=True,
    )
    # "chawl" near-miss to "chawal"
    raw_text = "do kilo chawl likho"
    corrected, corrections = provider.correct_tokens(raw_text, similarity_threshold=0.8)
    assert "chawal" in corrected
    assert len(corrections) == 1
    assert corrections[0]["original"] == "chawl"
    assert corrections[0]["corrected"] == "chawal"
    assert corrections[0]["category"] == "item"


def test_no_false_positive_hallucination_on_unrelated_audio() -> None:
    provider = VocabularyProvider(
        customer_names=["Sharma ji", "Verma ji", "Agarwal"],
        item_names=["chawal", "makhan", "ghee"],
        enabled=True,
    )
    # Audio with completely unrelated words should not have names injected
    raw_text = "ha theek hai kal subah aana"
    corrected, corrections = provider.correct_tokens(raw_text, similarity_threshold=0.88)
    assert corrected == raw_text
    assert len(corrections) == 0


def test_add_customer_and_item() -> None:
    provider = VocabularyProvider(enabled=True)
    provider.add_customer("Singh Sahab")
    provider.add_item("besan")

    prompt = provider.get_initial_prompt()
    assert prompt is not None
    assert "Singh Sahab" in prompt
    assert "Besan" in prompt
