#!/usr/bin/env python3
"""
Evaluation script for BolKhata Spoken Indian Amounts Benchmark (BSIAB).
Scores any model or provider predictions against ground-truth amounts.

Metrics:
- Amount Exact Match (A-EM %): Percentage of transactions where amount matches exactly.
- Magnitude Error Rate (MER %): Percentage where prediction is off by 10x or more.
- Currency Accuracy (%): Percentage where currency token was correctly recognized.
- Colloquial Fraction Accuracy (%): Breakdown on dhai, derh, sawa, sadhe, paune.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def evaluate_amount_predictions(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Score model predictions against benchmark ground truth.
    """
    pred_map = {p["utterance_id"]: p for p in predictions}

    total = len(ground_truth)
    if total == 0:
        return {"error": "Empty ground truth dataset"}

    exact_matches = 0
    magnitude_errors = 0
    currency_matches = 0
    fraction_total = 0
    fraction_exact = 0

    per_category: dict[str, dict[str, int]] = {}

    for gt in ground_truth:
        u_id = gt["utterance_id"]
        gt_amount = float(gt["ground_truth_amount"])
        gt_currency = gt.get("currency", "INR").upper()
        frac_type = gt.get("fraction_type")

        cat = frac_type if frac_type else "standard_numerals"
        if cat not in per_category:
            per_category[cat] = {"total": 0, "exact": 0}
        per_category[cat]["total"] += 1

        pred = pred_map.get(u_id)
        if not pred:
            continue

        pred_amount = pred.get("predicted_amount")
        pred_currency = str(pred.get("predicted_currency", "INR")).upper()

        if pred_amount is not None:
            pred_val = float(pred_amount)
            # Exact match (tolerance 0.01 for floating point)
            if math.isclose(gt_amount, pred_val, abs_tol=0.01):
                exact_matches += 1
                per_category[cat]["exact"] += 1
                if frac_type:
                    fraction_exact += 1
            else:
                # Check for magnitude slip (ratio >= 9.5 or <= 0.105)
                if gt_amount > 0 and pred_val > 0:
                    ratio = pred_val / gt_amount
                    if ratio >= 9.5 or ratio <= 0.105:
                        magnitude_errors += 1

        if pred_currency == gt_currency:
            currency_matches += 1

        if frac_type:
            fraction_total += 1

    a_em = (exact_matches / total) * 100.0
    mer = (magnitude_errors / total) * 100.0
    cur_acc = (currency_matches / total) * 100.0
    frac_em = (fraction_exact / fraction_total * 100.0) if fraction_total > 0 else 0.0

    return {
        "total_utterances": total,
        "amount_exact_match_pct": round(a_em, 2),
        "magnitude_error_rate_pct": round(mer, 2),
        "currency_accuracy_pct": round(cur_acc, 2),
        "colloquial_fraction_accuracy_pct": round(frac_em, 2),
        "category_breakdown": {
            cat: {
                "total": stats["total"],
                "exact": stats["exact"],
                "accuracy_pct": round(stats["exact"] / stats["total"] * 100.0, 2)
                if stats["total"] > 0
                else 0.0,
            }
            for cat, stats in per_category.items()
        },
    }


def format_markdown_report(results: dict[str, Any]) -> str:
    """Format evaluation results into standard Markdown table."""
    lines = [
        "# BolKhata Spoken Indian Amounts Benchmark (BSIAB) Evaluation Report",
        "",
        f"- **Total Evaluated Utterances:** {results['total_utterances']}",
        f"- **Amount Exact Match (A-EM):** **{results['amount_exact_match_pct']}%**",
        f"- **Magnitude Error Rate (10x Slips):** {results['magnitude_error_rate_pct']}%",
        f"- **Currency Token Accuracy:** {results['currency_accuracy_pct']}%",
        f"- **Colloquial Fraction Accuracy:** {results['colloquial_fraction_accuracy_pct']}%",
        "",
        "## Performance by Number Category",
        "",
        "| Category | Total Tested | Exact Matches | Accuracy (%) |",
        "|---|---|---|---|",
    ]

    for cat, stats in results.get("category_breakdown", {}).items():
        lines.append(
            f"| `{cat}` | {stats['total']} | {stats['exact']} | {stats['accuracy_pct']}% |"
        )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate predictions on BSIAB")
    parser.add_argument("--ground-truth", type=Path, required=True, help="Path to manifest or ground truth JSON")
    parser.add_argument("--predictions", type=Path, required=True, help="Path to predictions JSON")
    parser.add_argument("--output-report", type=Path, help="Optional markdown output report file")
    args = parser.parse_args()

    gt_data = json.loads(args.ground_truth.read_text(encoding="utf-8"))
    gt_records = gt_data if isinstance(gt_data, list) else gt_data.get("splits", {}).get("test", [])
    pred_data = json.loads(args.predictions.read_text(encoding="utf-8"))
    pred_records = pred_data if isinstance(pred_data, list) else pred_data.get("predictions", [])

    results = evaluate_amount_predictions(gt_records, pred_records)
    md_report = format_markdown_report(results)
    print(md_report)

    if args.output_report:
        args.output_report.write_text(md_report, encoding="utf-8")
        print(f"Report written to {args.output_report}")


if __name__ == "__main__":
    main()
