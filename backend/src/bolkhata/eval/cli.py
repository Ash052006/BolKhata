"""
Command-line interface for running BolKhata evaluation benchmarks.

Example:
    python -m bolkhata.eval run --models mock,mlx-whisper --dataset tests/data/eval/metadata.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from bolkhata.asr.base import ASRProvider
from bolkhata.asr.mock import MockASRProvider
from bolkhata.config.settings import Settings
from bolkhata.eval.runner import (
    BenchmarkSuiteReport,
    evaluate_provider,
    format_markdown_report,
    get_dataset_hash,
    get_git_commit,
    get_system_hardware,
)


def resolve_provider(model_name: str, settings: Settings) -> ASRProvider:
    """Instantiate ASRProvider for model name."""
    clean_name = model_name.strip().lower()
    if clean_name in ("mock", "mock-asr"):
        return MockASRProvider(canned_text="dhai sau rupaye udhaar likho")
    elif clean_name in ("mlx-whisper", "mlx", "mlx_whisper"):
        from bolkhata.asr.mlx_whisper import MLXWhisperASRProvider

        return MLXWhisperASRProvider(settings)
    else:
        raise ValueError(f"Unknown or unsupported model provider: '{model_name}'")


async def run_benchmark(
    models: list[str],
    metadata_path: Path,
    output_dir: Path,
    mode: str = "tolerant",
) -> int:
    """Run benchmark suite across requested models."""
    if not metadata_path.is_file():
        print(f"ERROR: Dataset metadata file not found at: {metadata_path}", file=sys.stderr)
        return 1

    try:
        content = metadata_path.read_text(encoding="utf-8").strip()
        if content.startswith("["):
            entries = json.loads(content)
        else:
            entries = [json.loads(line) for line in content.splitlines() if line.strip()]
    except Exception as e:
        print(f"ERROR: Failed to parse metadata file: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {len(entries)} evaluation records from {metadata_path}")
    settings = Settings()

    suite = BenchmarkSuiteReport(
        git_commit=get_git_commit(),
        hardware=get_system_hardware(),
        os_info=f"{sys.platform} ({sys.version.split()[0]})",
        dataset_name=metadata_path.stem,
        dataset_hash=get_dataset_hash(metadata_path),
        normalization_mode=mode,
        timestamp=time.time(),
        models={},
    )

    audio_base = metadata_path.parent

    for m in models:
        clean_m = m.strip()
        print(f"\nEvaluating model: '{clean_m}'...")
        try:
            prov = resolve_provider(clean_m, settings)
            rep = await evaluate_provider(
                provider=prov,
                model_name=clean_m,
                metadata_entries=entries,
                audio_base_dir=audio_base,
                mode=mode,  # type: ignore[arg-type]
            )
            suite.models[clean_m] = rep
            print(
                f"  WER: {rep.overall_wer * 100:.2f}%, CER: {rep.overall_cer * 100:.2f}%, RTF: {rep.overall_rtf:.3f}, Number Acc: {rep.overall_number_accuracy * 100:.1f}%"
            )
        except Exception as e:
            print(f"  FAILED to evaluate '{clean_m}': {e}", file=sys.stderr)

    # Write output reports
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"benchmark_{metadata_path.stem}.json"
    md_path = output_dir / f"benchmark_{metadata_path.stem}.md"

    json_path.write_text(json.dumps(asdict(suite), indent=2), encoding="utf-8")
    md_report = format_markdown_report(suite)
    md_path.write_text(md_report, encoding="utf-8")

    print("\nBenchmark completed!")
    print(f"  JSON output: {json_path}")
    print(f"  Markdown output: {md_path}")
    print("\n" + md_report)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="BolKhata Evaluation Benchmark CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run benchmark on models and dataset")
    run_parser.add_argument(
        "--models",
        type=str,
        default="mock",
        help="Comma-separated list of models to evaluate (e.g. mock,mlx-whisper)",
    )
    run_parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("tests/data/eval/metadata.json"),
        help="Path to dataset metadata JSON",
    )
    run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/benchmarks"),
        help="Directory to save output reports",
    )
    run_parser.add_argument(
        "--mode",
        choices=["strict", "tolerant"],
        default="tolerant",
        help="ASR text normalization mode",
    )

    args = parser.parse_args()

    if args.command == "run":
        model_list = [m.strip() for m in args.models.split(",") if m.strip()]
        exit_code = asyncio.run(
            run_benchmark(
                models=model_list,
                metadata_path=args.dataset,
                output_dir=args.output_dir,
                mode=args.mode,
            )
        )
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
