"""
Unit tests for the evaluation dataset validator and benchmark runner CLI.
"""

import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from bolkhata.eval.cli import run_benchmark

VALIDATE_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_eval_dataset.py"


@pytest.fixture
def temp_eval_dataset(tmp_path: Path) -> tuple[Path, Path]:
    """Create a temporary valid evaluation dataset with a tiny 0.5s 16kHz WAV."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True)
    wav_path = audio_dir / "utt_test_01.wav"

    # Write a 0.5s 16kHz mono 16-bit PCM WAV (8000 frames of silence)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 8000)

    metadata = [
        {
            "id": "utt_test_01",
            "audio_file": "audio/utt_test_01.wav",
            "reference": "dhai sau rupaye udhaar likho",
            "language": "hinglish",
            "speaker_id": "spk_test",
            "noise_level": "low",
            "category": "number_heavy",
            "duration_seconds": 0.5,
        }
    ]

    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")

    return meta_path, tmp_path


def test_validate_eval_dataset_success(temp_eval_dataset: tuple[Path, Path]) -> None:
    meta_path, audio_base = temp_eval_dataset
    res = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--metadata",
            str(meta_path),
            "--audio-dir",
            str(audio_base),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "SUCCESS: Dataset is valid!" in res.stdout


def test_validate_eval_dataset_invalid_sample_rate(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True)
    bad_wav = audio_dir / "bad.wav"
    with wave.open(str(bad_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)  # Invalid sample rate
        wf.writeframes(b"\x00\x00" * 100)

    metadata = [
        {
            "id": "utt_bad",
            "audio_file": "audio/bad.wav",
            "reference": "test",
            "language": "hindi",
            "speaker_id": "spk_test",
            "noise_level": "low",
            "category": "plain_hindi",
            "duration_seconds": 0.1,
        }
    ]
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")

    res = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--metadata",
            str(meta_path),
            "--audio-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Expected 16000 Hz sample rate" in res.stderr


@pytest.mark.asyncio
async def test_run_benchmark_mock_provider(
    temp_eval_dataset: tuple[Path, Path], tmp_path: Path
) -> None:
    meta_path, _ = temp_eval_dataset
    out_dir = tmp_path / "benchmarks"

    exit_code = await run_benchmark(
        models=["mock"],
        metadata_path=meta_path,
        output_dir=out_dir,
        mode="tolerant",
    )
    assert exit_code == 0

    json_files = list(out_dir.glob("*.json"))
    md_files = list(out_dir.glob("*.md"))
    assert len(json_files) == 1
    assert len(md_files) == 1

    report_data = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert "mock" in report_data["models"]
    mock_rep = report_data["models"]["mock"]
    assert mock_rep["total_utterances"] == 1
    assert mock_rep["overall_wer"] == 0.0  # Mock returns exact text
    assert mock_rep["overall_number_accuracy"] == 1.0

    md_content = md_files[0].read_text(encoding="utf-8")
    assert "# BolKhata ASR Benchmark Report" in md_content
    assert "| `mock` |" in md_content
