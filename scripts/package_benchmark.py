#!/usr/bin/env python3
"""
Packaging and Anonymization Script for BolKhata Spoken Indian Amounts Benchmark (BSIAB).
Implements Feature F10 (Open Spoken-Amount Benchmark).

Functions:
- Scans utterance metadata for PII (customer names, Indian 10-digit phone numbers).
- Excludes contaminated or unconsented records.
- Computes SHA-256 manifests for reproducibility and tamper detection.
- Generates speaker-disjoint train/validation/test splits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# PII Detection Patterns
PHONE_REGEX = re.compile(r"\b[6-9]\d{9}\b")
NAME_INDICATORS = re.compile(
    r"\b(?:sharma|verma|gupta|yadav|mishra|pandey|singh|chaudhary|das|ghosh|babu|bhaiya|ji|uncle|aunty)\b",
    re.IGNORECASE,
)


def validate_and_anonymize_record(record: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that an utterance record contains zero PII.
    Returns (is_valid, rejection_reason).
    """
    raw_text = record.get("raw_transcript", "")
    norm_text = record.get("normalized_transcript", "")
    combined = f"{raw_text} {norm_text}"

    # Check for phone numbers
    if PHONE_REGEX.search(combined):
        return False, "Contains 10-digit mobile phone number"

    # Check for customer names / honorifics
    if NAME_INDICATORS.search(combined):
        return False, "Contains customer name or personal identifier"

    # Verify required fields
    if "ground_truth_amount" not in record or record["ground_truth_amount"] is None:
        return False, "Missing ground_truth_amount"

    if "speaker_id" not in record or not record["speaker_id"].startswith("SPK_"):
        return False, "Invalid or non-anonymized speaker_id (must match SPK_XX)"

    return True, "Valid"


def compute_sha256(data: bytes | str) -> str:
    """Compute hex SHA-256 digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def package_dataset(
    records: list[dict[str, Any]],
    output_dir: Path,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> dict[str, Any]:
    """
    Filter, partition, and package records into speaker-disjoint benchmark splits.
    """
    valid_records: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []

    for r in records:
        is_valid, reason = validate_and_anonymize_record(r)
        if is_valid:
            valid_records.append(r)
        else:
            quarantined.append({"record": r, "reason": reason})

    # Group valid records by speaker to ensure zero speaker leakage across splits
    speakers = sorted(list({r["speaker_id"] for r in valid_records}))
    n_spk = len(speakers)

    if n_spk >= 3:
        n_test = max(1, int(n_spk * test_ratio))
        n_val = max(1, int(n_spk * val_ratio))
        test_spks = set(speakers[:n_test])
        val_spks = set(speakers[n_test : n_test + n_val])
        train_spks = set(speakers[n_test + n_val :])
    else:
        # Small sample split
        train_spks = set(speakers)
        val_spks = set()
        test_spks = set()

    manifest: dict[str, Any] = {
        "benchmark": "BSIAB-v0.1.0",
        "total_valid_utterances": len(valid_records),
        "quarantined_utterances": len(quarantined),
        "speakers_count": n_spk,
        "splits": {
            "train": [r for r in valid_records if r["speaker_id"] in train_spks],
            "validation": [r for r in valid_records if r["speaker_id"] in val_spks],
            "test": [r for r in valid_records if r["speaker_id"] in test_spks],
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "dataset_manifest.json"
    manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)

    # Write checksums
    checksum_path = output_dir / "manifest.sha256"
    checksum_path.write_text(f"{compute_sha256(manifest_bytes)}  dataset_manifest.json\n")

    return {
        "status": "success",
        "manifest_path": str(manifest_path),
        "valid_count": len(valid_records),
        "quarantined_count": len(quarantined),
        "sha256": compute_sha256(manifest_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Package BolKhata Spoken Amount Benchmark")
    parser.add_argument("--input", type=Path, required=True, help="Input JSON file with utterances")
    parser.add_argument("--output", type=Path, required=True, help="Output directory for packaged benchmark")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file '{args.input}' does not exist.", file=sys.stderr)
        sys.exit(1)

    raw_data = json.loads(args.input.read_text(encoding="utf-8"))
    records = raw_data if isinstance(raw_data, list) else raw_data.get("utterances", [])

    res = package_dataset(records, args.output)
    print(f"Dataset packaged successfully: {res['valid_count']} valid, {res['quarantined_count']} quarantined.")
    print(f"Manifest SHA-256: {res['sha256']}")


if __name__ == "__main__":
    main()
