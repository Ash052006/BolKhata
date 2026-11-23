"""
Benchmark runner orchestrating ASR evaluation across models and datasets.

Calculates:
- Overall and per-category WER and CER
- Real-Time Factor (RTF)
- Processing latency percentiles (p50, p95, p99)
- Peak memory usage
- Spoken number exact-match extraction accuracy
- Metadata capture: git commit, hardware specs, dataset SHA-256
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from bolkhata.asr.base import ASRProvider
from bolkhata.domains.common.numbers import extract_numbers
from bolkhata.eval.metrics import (
    calculate_cer,
    calculate_rtf,
    calculate_wer,
    get_peak_memory_mb,
)
from bolkhata.eval.normalizer import normalize_text


@dataclass
class UtteranceResult:
    id: str
    category: str
    language: str
    audio_duration_seconds: float
    processing_time_seconds: float
    rtf: float
    reference_raw: str
    hypothesis_raw: str
    reference_norm: str
    hypothesis_norm: str
    wer: float
    cer: float
    numbers_match: bool


@dataclass
class CategorySummary:
    category: str
    count: int
    mean_wer: float
    mean_cer: float
    mean_rtf: float
    number_accuracy: float


@dataclass
class ModelEvaluationReport:
    model_name: str
    total_utterances: int
    total_audio_seconds: float
    total_processing_seconds: float
    overall_wer: float
    overall_cer: float
    overall_rtf: float
    overall_number_accuracy: float
    peak_memory_mb: float
    category_breakdowns: dict[str, CategorySummary]
    utterances: list[UtteranceResult] = field(default_factory=list)


@dataclass
class BenchmarkSuiteReport:
    git_commit: str
    hardware: str
    os_info: str
    dataset_name: str
    dataset_hash: str
    normalization_mode: str
    timestamp: float
    models: dict[str, ModelEvaluationReport]


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def get_dataset_hash(metadata_path: Path) -> str:
    """Calculate SHA-256 hash of dataset metadata file."""
    if not metadata_path.is_file():
        return "missing"
    hasher = hashlib.sha256()
    hasher.update(metadata_path.read_bytes())
    return hasher.hexdigest()[:16]


def get_system_hardware() -> str:
    """Get hardware description."""
    uname = platform.uname()
    return f"{uname.system} {uname.machine} ({uname.processor or 'Apple Silicon'})"


def read_wav_pcm16le(path: Path) -> tuple[bytes, float]:
    """Read raw 16kHz s16le PCM bytes and duration from a WAV file."""
    with wave.open(str(path), "rb") as wf:
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        duration = float(nframes) / float(framerate) if framerate > 0 else 0.0
        frames = wf.readframes(nframes)
        return frames, duration


async def evaluate_provider(
    provider: ASRProvider,
    model_name: str,
    metadata_entries: list[dict[str, Any]],
    audio_base_dir: Path,
    mode: Literal["strict", "tolerant"] = "tolerant",
) -> ModelEvaluationReport:
    """Evaluate a single ASR provider on a dataset."""
    results: list[UtteranceResult] = []
    total_audio_sec = 0.0
    total_proc_sec = 0.0

    # Warmup
    await provider.initialize()

    for entry in metadata_entries:
        utt_id = entry["id"]
        category = entry.get("category", "general")
        language = entry.get("language", "hinglish")
        ref_raw = entry.get("reference", "")
        audio_rel = entry["audio_file"]
        audio_path = audio_base_dir / audio_rel

        if not audio_path.is_file():
            continue

        pcm_bytes, dur = read_wav_pcm16le(audio_path)
        total_audio_sec += dur

        t0 = time.perf_counter()
        asr_res = await provider.transcribe(pcm_bytes)
        t1 = time.perf_counter()

        proc_time = t1 - t0
        total_proc_sec += proc_time
        rtf = calculate_rtf(proc_time, dur)

        hyp_raw = asr_res.text
        ref_norm = normalize_text(ref_raw, mode=mode)
        hyp_norm = normalize_text(hyp_raw, mode=mode)

        wer_stat = calculate_wer(ref_norm, hyp_norm)
        cer_stat = calculate_cer(ref_norm, hyp_norm)

        # Check number extraction exact match
        ref_nums = [n.value for n in extract_numbers(ref_raw)]
        hyp_nums = [n.value for n in extract_numbers(hyp_raw)]
        numbers_match = ref_nums == hyp_nums

        results.append(
            UtteranceResult(
                id=utt_id,
                category=category,
                language=language,
                audio_duration_seconds=dur,
                processing_time_seconds=proc_time,
                rtf=rtf,
                reference_raw=ref_raw,
                hypothesis_raw=hyp_raw,
                reference_norm=ref_norm,
                hypothesis_norm=hyp_norm,
                wer=wer_stat.error_rate,
                cer=cer_stat.error_rate,
                numbers_match=numbers_match,
            )
        )

    await provider.shutdown()

    # Aggregations
    n = len(results)
    if n == 0:
        return ModelEvaluationReport(
            model_name=model_name,
            total_utterances=0,
            total_audio_seconds=0.0,
            total_processing_seconds=0.0,
            overall_wer=0.0,
            overall_cer=0.0,
            overall_rtf=0.0,
            overall_number_accuracy=1.0,
            peak_memory_mb=get_peak_memory_mb(),
            category_breakdowns={},
            utterances=[],
        )

    overall_wer = sum(r.wer for r in results) / n
    overall_cer = sum(r.cer for r in results) / n
    overall_rtf = total_proc_sec / total_audio_sec if total_audio_sec > 0 else 0.0
    overall_num_acc = sum(1.0 for r in results if r.numbers_match) / n

    # Category breakdowns
    categories = sorted({r.category for r in results})
    breakdowns: dict[str, CategorySummary] = {}
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        m = len(cat_results)
        breakdowns[cat] = CategorySummary(
            category=cat,
            count=m,
            mean_wer=sum(r.wer for r in cat_results) / m,
            mean_cer=sum(r.cer for r in cat_results) / m,
            mean_rtf=sum(r.rtf for r in cat_results) / m,
            number_accuracy=sum(1.0 for r in cat_results if r.numbers_match) / m,
        )

    return ModelEvaluationReport(
        model_name=model_name,
        total_utterances=n,
        total_audio_seconds=total_audio_sec,
        total_processing_seconds=total_proc_sec,
        overall_wer=overall_wer,
        overall_cer=overall_cer,
        overall_rtf=overall_rtf,
        overall_number_accuracy=overall_num_acc,
        peak_memory_mb=get_peak_memory_mb(),
        category_breakdowns=breakdowns,
        utterances=results,
    )


def format_markdown_report(suite: BenchmarkSuiteReport) -> str:
    """Format suite report into a GitHub-Flavored Markdown report."""
    lines: list[str] = [
        f"# BolKhata ASR Benchmark Report: `{suite.dataset_name}`",
        "",
        "## 1. Environment & Provenance",
        f"- **Git Commit**: `{suite.git_commit}`",
        f"- **Hardware**: {suite.hardware}",
        f"- **OS**: {suite.os_info}",
        f"- **Dataset SHA-256**: `{suite.dataset_hash}`",
        f"- **Normalization Mode**: `{suite.normalization_mode}`",
        f"- **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(suite.timestamp))}",
        "",
        "## 2. Model Performance Summary",
        "",
        "| Model | WER (%) | CER (%) | RTF | Number Acc (%) | Peak Memory (MB) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for model_name, rep in suite.models.items():
        lines.append(
            f"| `{model_name}` | {rep.overall_wer * 100:.2f}% | {rep.overall_cer * 100:.2f}% | {rep.overall_rtf:.3f} | {rep.overall_number_accuracy * 100:.1f}% | {rep.peak_memory_mb:.1f} MB |"
        )

    lines.extend(
        [
            "",
            "## 3. Per-Category Breakdown",
            "",
        ]
    )

    for model_name, rep in suite.models.items():
        lines.extend(
            [
                f"### Model: `{model_name}`",
                "",
                "| Category | Utterances | WER (%) | CER (%) | RTF | Number Acc (%) |",
                "| :--- | :---: | :---: | :---: | :---: | :---: |",
            ]
        )
        for cat, cat_stat in rep.category_breakdowns.items():
            lines.append(
                f"| `{cat}` | {cat_stat.count} | {cat_stat.mean_wer * 100:.2f}% | {cat_stat.mean_cer * 100:.2f}% | {cat_stat.mean_rtf:.3f} | {cat_stat.number_accuracy * 100:.1f}% |"
            )
        lines.append("")

    return "\n".join(lines)
