"""
Unit tests for Feature F10: Open Spoken-Amount Benchmark Tooling.
Verifies `scripts/package_benchmark.py` and `scripts/eval_amount_benchmark.py`:
- Zero-PII sanitization and validation gates
- Tamper-evident SHA-256 packaging
- Exact-match, magnitude-slip, and fraction breakdown metrics
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

# Dynamically import scripts
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
package_script_path = ROOT_DIR / "scripts" / "package_benchmark.py"
eval_script_path = ROOT_DIR / "scripts" / "eval_amount_benchmark.py"

spec_pkg = importlib.util.spec_from_file_location("package_benchmark", package_script_path)
pkg_mod = importlib.util.module_from_spec(spec_pkg)  # type: ignore[arg-type]
spec_pkg.loader.exec_module(pkg_mod)  # type: ignore[union-attr]

spec_eval = importlib.util.spec_from_file_location("eval_amount_benchmark", eval_script_path)
eval_mod = importlib.util.module_from_spec(spec_eval)  # type: ignore[arg-type]
spec_eval.loader.exec_module(eval_mod)  # type: ignore[union-attr]


def test_validation_rejects_phone_numbers() -> None:
    contaminated_record = {
        "utterance_id": "UTT_01",
        "speaker_id": "SPK_01",
        "raw_transcript": "call karo 9876543210 par 500 rupaye",
        "ground_truth_amount": 500.0,
    }
    is_valid, reason = pkg_mod.validate_and_anonymize_record(contaminated_record)
    assert not is_valid
    assert "mobile phone number" in reason.lower()


def test_validation_rejects_customer_names() -> None:
    contaminated_record = {
        "utterance_id": "UTT_02",
        "speaker_id": "SPK_02",
        "raw_transcript": "Sharma ji ko teen sau udhaar",
        "ground_truth_amount": 300.0,
    }
    is_valid, reason = pkg_mod.validate_and_anonymize_record(contaminated_record)
    assert not is_valid
    assert "customer name" in reason.lower()


def test_validation_accepts_clean_record() -> None:
    clean_record = {
        "utterance_id": "UTT_03",
        "speaker_id": "SPK_03",
        "raw_transcript": "dhai sau rupaye udhaar do kilo chawal",
        "normalized_transcript": "250 rupaye udhaar 2 kg chawal",
        "ground_truth_amount": 250.0,
    }
    is_valid, reason = pkg_mod.validate_and_anonymize_record(clean_record)
    assert is_valid
    assert reason == "Valid"


def test_package_dataset(tmp_path: Path) -> None:
    records = [
        {
            "utterance_id": "U1",
            "speaker_id": "SPK_01",
            "raw_transcript": "paanch sau rupaye jama",
            "ground_truth_amount": 500.0,
        },
        {
            "utterance_id": "U2",
            "speaker_id": "SPK_02",
            "raw_transcript": "derh hajaar rupaye",
            "ground_truth_amount": 1500.0,
        },
        {
            "utterance_id": "U3",
            "speaker_id": "SPK_03",
            "raw_transcript": "call 9876543210",
            "ground_truth_amount": 100.0,
        },
    ]

    out_dir = tmp_path / "pkg_test"
    res = pkg_mod.package_dataset(records, out_dir)

    assert res["status"] == "success"
    assert res["valid_count"] == 2
    assert res["quarantined_count"] == 1
    assert (out_dir / "dataset_manifest.json").exists()
    assert (out_dir / "manifest.sha256").exists()


def test_evaluate_amount_predictions() -> None:
    ground_truth = [
        {
            "utterance_id": "U1",
            "ground_truth_amount": 250.0,
            "currency": "INR",
            "fraction_type": "dhai",
        },
        {
            "utterance_id": "U2",
            "ground_truth_amount": 1500.0,
            "currency": "INR",
            "fraction_type": "derh",
        },
        {
            "utterance_id": "U3",
            "ground_truth_amount": 50.0,
            "currency": "INR",
            "fraction_type": None,
        },
    ]

    predictions = [
        {
            "utterance_id": "U1",
            "predicted_amount": 250.0,  # Exact match
            "predicted_currency": "INR",
        },
        {
            "utterance_id": "U2",
            "predicted_amount": 150.0,  # 10x Magnitude error (150 vs 1500)
            "predicted_currency": "INR",
        },
        {
            "utterance_id": "U3",
            "predicted_amount": 50.0,  # Exact match
            "predicted_currency": "USD",  # Currency mismatch
        },
    ]

    metrics = eval_mod.evaluate_amount_predictions(ground_truth, predictions)

    # 2 out of 3 exact = 66.67%
    assert metrics["amount_exact_match_pct"] == 66.67
    # 1 magnitude error out of 3 = 33.33%
    assert metrics["magnitude_error_rate_pct"] == 33.33
    # 2 currency matches out of 3 = 66.67%
    assert metrics["currency_accuracy_pct"] == 66.67
    # Category breakdown includes "dhai" and "derh"
    assert "dhai" in metrics["category_breakdown"]
    assert metrics["category_breakdown"]["dhai"]["exact"] == 1
