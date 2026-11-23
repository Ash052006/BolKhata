"""
Unit tests for evaluation metrics engine and cross-validation against jiwer.
"""

import jiwer
import pytest

from bolkhata.eval.metrics import (
    calculate_cer,
    calculate_rtf,
    calculate_wer,
    get_peak_memory_mb,
)


@pytest.mark.parametrize(
    ("ref", "hyp"),
    [
        ("dhai sau rupaye", "dhai sau rupaye"),  # 0% error
        ("dhai sau rupaye", "dedh sau rupaye"),  # 1 substitution (1/3)
        ("dhai sau rupaye", "dhai rupaye"),  # 1 deletion (1/3)
        ("dhai sau rupaye", "ek dhai sau rupaye"),  # 1 insertion (1/3)
        ("ramesh ji ko do sau rupaye", "ramesh ko teen sau rupaye"),  # 1 sub, 1 del
        ("paanch kilo chini", "das packet namak"),  # 3 substitutions (3/3 = 1.0)
        ("ek do teen char", "ek char"),  # 2 deletions (2/4 = 0.5)
        ("a b c d e", "a x c y e"),  # 2 substitutions (2/5 = 0.4)
        ("", ""),  # Empty match
        ("hello world", ""),  # Complete deletion (2/2 = 1.0)
        ("", "hello world"),  # Complete insertion
    ],
)
def test_wer_cross_check_with_jiwer(ref: str, hyp: str) -> None:
    stats = calculate_wer(ref, hyp)

    if ref.strip() == "":
        expected_jiwer = 0.0 if hyp.strip() == "" else 1.0
        assert stats.error_rate == pytest.approx(expected_jiwer)
    else:
        jiwer_wer = jiwer.wer(ref, hyp)
        assert stats.error_rate == pytest.approx(jiwer_wer)


@pytest.mark.parametrize(
    ("ref", "hyp", "expected_cer"),
    [
        ("cat", "cat", 0.0),
        ("cat", "hat", 1 / 3),
        ("cat", "cats", 1 / 3),
        ("cat", "at", 1 / 3),
        ("kitten", "sitting", 3 / 6),
        ("", "", 0.0),
    ],
)
def test_cer_calculation(ref: str, hyp: str, expected_cer: float) -> None:
    stats = calculate_cer(ref, hyp)
    assert stats.error_rate == pytest.approx(expected_cer)


def test_rtf_calculation() -> None:
    assert calculate_rtf(0.5, 2.0) == pytest.approx(0.25)
    assert calculate_rtf(3.0, 1.5) == pytest.approx(2.0)
    assert calculate_rtf(1.0, 0.0) == 0.0


def test_peak_memory_reporting() -> None:
    mem = get_peak_memory_mb()
    assert mem > 0.0
