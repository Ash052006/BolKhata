#!/usr/bin/env python3
"""
Validation script for BolKhata evaluation datasets.

Verifies:
- Schema conformance of metadata JSON/JSONL
- Audio file existence and validity (WAV 16kHz, 16-bit, Mono)
- Duration consistency between header and metadata
- Category and language distribution
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from collections import Counter
from pathlib import Path

VALID_LANGUAGES = {"hindi", "english", "hinglish"}
VALID_NOISE_LEVELS = {"low", "medium", "high"}
VALID_CATEGORIES = {
    "plain_hindi",
    "plain_english",
    "hinglish",
    "number_heavy",
    "noisy_shop",
    "correction",
}


def validate_wav_file(path: Path) -> tuple[bool, str, float]:
    """Validate audio file format and return (is_valid, error_msg, duration_seconds)."""
    if not path.is_file():
        return False, f"File does not exist: {path}", 0.0

    try:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()

            if channels != 1:
                return False, f"Expected 1 channel (mono), found {channels}", 0.0
            if sample_width != 2:
                return False, f"Expected 16-bit audio (sampwidth=2), found {sample_width}", 0.0
            if framerate != 16000:
                return False, f"Expected 16000 Hz sample rate, found {framerate}", 0.0

            duration = float(n_frames) / float(framerate)
            return True, "", duration
    except Exception as e:
        return False, f"Invalid WAV header: {e}", 0.0


def validate_dataset(metadata_path: Path, audio_base_dir: Path | None = None) -> int:
    """Validate dataset and print statistical summary."""
    if not metadata_path.is_file():
        print(f"ERROR: Metadata file not found: {metadata_path}", file=sys.stderr)
        return 1

    if audio_base_dir is None:
        audio_base_dir = metadata_path.parent

    try:
        content = metadata_path.read_text(encoding="utf-8").strip()
        if content.startswith("["):
            entries = json.loads(content)
        else:
            entries = [json.loads(line) for line in content.splitlines() if line.strip()]
    except Exception as e:
        print(f"ERROR: Failed to parse metadata file: {e}", file=sys.stderr)
        return 1

    if not isinstance(entries, list):
        print("ERROR: Metadata root must be a list of records.", file=sys.stderr)
        return 1

    print(f"Validating {len(entries)} metadata records from {metadata_path}...")

    errors: list[str] = []
    total_duration = 0.0
    category_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    noise_counts: Counter[str] = Counter()
    speakers: set[str] = set()

    for idx, entry in enumerate(entries):
        entry_id = entry.get("id", f"record_{idx}")

        # Required fields check
        for field in ("id", "audio_file", "reference", "language", "speaker_id", "noise_level", "category"):
            if field not in entry:
                errors.append(f"[{entry_id}] Missing required field: '{field}'")

        ref = entry.get("reference", "")
        if not ref.strip():
            errors.append(f"[{entry_id}] Empty reference transcript.")

        lang = entry.get("language")
        if lang not in VALID_LANGUAGES:
            errors.append(f"[{entry_id}] Invalid language: '{lang}'. Expected one of {VALID_LANGUAGES}")
        else:
            language_counts[lang] += 1

        noise = entry.get("noise_level")
        if noise not in VALID_NOISE_LEVELS:
            errors.append(f"[{entry_id}] Invalid noise_level: '{noise}'. Expected one of {VALID_NOISE_LEVELS}")
        else:
            noise_counts[noise] += 1

        cat = entry.get("category")
        if cat not in VALID_CATEGORIES:
            errors.append(f"[{entry_id}] Invalid category: '{cat}'. Expected one of {VALID_CATEGORIES}")
        else:
            category_counts[cat] += 1

        spk = entry.get("speaker_id")
        if spk:
            speakers.add(spk)

        # Audio file validation
        audio_rel = entry.get("audio_file")
        if audio_rel:
            audio_path = audio_base_dir / audio_rel
            is_valid, err_msg, dur = validate_wav_file(audio_path)
            if not is_valid:
                errors.append(f"[{entry_id}] Audio validation failed ({audio_rel}): {err_msg}")
            else:
                total_duration += dur
                claimed_dur = entry.get("duration_seconds")
                if claimed_dur is not None and abs(dur - float(claimed_dur)) > 0.5:
                    errors.append(
                        f"[{entry_id}] Claimed duration ({claimed_dur}s) differs from actual ({dur:.2f}s)"
                    )

    if errors:
        print(f"\nFAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors[:20]:
            print(f"  - {err}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors", file=sys.stderr)
        return 1

    print("\nSUCCESS: Dataset is valid!")
    print(f"Total utterances: {len(entries)}")
    print(f"Total duration: {total_duration:.2f} seconds ({total_duration / 60.0:.2f} minutes)")
    print(f"Unique speakers: {len(speakers)} ({', '.join(sorted(speakers))})")
    print("\nCategory breakdown:")
    for cat, count in sorted(category_counts.items()):
        print(f"  - {cat:15}: {count}")
    print("\nLanguage breakdown:")
    for lang, count in sorted(language_counts.items()):
        print(f"  - {lang:15}: {count}")
    print("\nNoise level breakdown:")
    for noise, count in sorted(noise_counts.items()):
        print(f"  - {noise:15}: {count}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate BolKhata evaluation dataset.")
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("tests/data/eval/metadata.json"),
        help="Path to metadata JSON or JSONL file",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=None,
        help="Base directory for audio files (defaults to metadata file's directory)",
    )
    args = parser.parse_args()

    sys.exit(validate_dataset(args.metadata, args.audio_dir))


if __name__ == "__main__":
    main()
