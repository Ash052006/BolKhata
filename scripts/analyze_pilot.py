#!/usr/bin/env python3
"""
Field trial and pilot instrumentation analysis script (Feature F7).

Analyzes anonymized participant trial logs from BolKhata voice ledger sessions.
Honesty invariant: No synthetic numbers or extrapolated statistical significance.
With small pilot cohorts, reports sample size N, descriptive ranges, and medians.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def analyze_csv(file_path: Path) -> str:
    if not file_path.exists():
        return f"Error: Pilot log file '{file_path}' does not exist."

    with file_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return "No pilot interaction records found."

    total_interactions = len(rows)
    participants = sorted({r["Participant Code"] for r in rows})
    voice_entries = [r for r in rows if r["Interaction Type"] == "voice_entry"]
    manual_entries = [r for r in rows if r["Interaction Type"] == "baseline_manual"]

    def get_stats(subset: list[dict[str, str]]) -> tuple[float, float, float]:
        if not subset:
            return 0.0, 0.0, 0.0
        times = sorted(float(r["Time To Confirm (ms)"]) for r in subset)
        n = len(times)
        median = times[n // 2] if n % 2 != 0 else (times[n // 2 - 1] + times[n // 2]) / 2.0
        return times[0], median, times[-1]

    v_min, v_med, v_max = get_stats(voice_entries)
    m_min, m_med, m_max = get_stats(manual_entries)

    total_corrections = sum(int(r.get("Correction Count", 0)) for r in voice_entries)
    total_failures = sum(1 for r in rows if r.get("Failure Type"))

    lines = [
        "# BolKhata Pilot Trial Analysis Report",
        "",
        f"> **Total Interaction Sample Size (N):** {total_interactions}",
        f"> **Participating Shopkeeper Cohort:** {len(participants)} ({', '.join(participants)})",
        "> **Methodology Notice:** Descriptive metrics only. No inferential significance claims on small cohorts.",
        "",
        "## 1. Time-to-Record Comparison: Voice vs Manual Method",
        "",
        "| Interaction Mode | N | Fastest (s) | Median (s) | Slowest (s) |",
        "|---|---|---|---|---|",
        f"| **BolKhata Push-to-Talk Voice** | {len(voice_entries)} | {v_min/1000.0:.2f}s | **{v_med/1000.0:.2f}s** | {v_max/1000.0:.2f}s |",
        f"| **Baseline Manual Paper/App** | {len(manual_entries)} | {m_min/1000.0:.2f}s | **{m_med/1000.0:.2f}s** | {m_max/1000.0:.2f}s |",
        "",
        "## 2. Voice Accuracy and Failure Indicators",
        "",
        f"- **Voice Correction Rate:** {total_corrections / max(len(voice_entries), 1):.1%} of turns required verbal correction.",
        f"- **System Failure Rate:** {total_failures / total_interactions:.1%} (network drop, unrecognized speech, or retry).",
        "",
        "## 3. Qualitative Shopkeeper Feedback",
        "",
    ]

    comments = [
        (r["Participant Code"], r["Participant Comment"])
        for r in rows
        if r.get("Participant Comment")
    ]
    if comments:
        for code, c in comments:
            lines.append(f"- **[{code}]:** *\"{c}\"*")
    else:
        lines.append("*No participant comments recorded in this trial batch.*")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze BolKhata pilot trial CSV logs.")
    parser.add_argument("file", nargs="?", default="pilot_log.csv", help="Path to pilot CSV file.")
    args = parser.parse_args()

    report = analyze_csv(Path(args.file))
    print(report)


if __name__ == "__main__":
    main()
