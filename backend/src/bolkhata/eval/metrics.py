"""
Deterministic speech recognition error metrics and performance measurements.

Provides:
- Word Error Rate (WER) with exact Wagner-Fischer edit distance breakdown (S, D, I, H)
- Character Error Rate (CER)
- Real-Time Factor (RTF)
- Memory and timing tracking
"""

from __future__ import annotations

import platform
import resource
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EditStats:
    """Breakdown of Levenshtein edit operations."""

    error_rate: float
    substitutions: int
    deletions: int
    insertions: int
    hits: int
    reference_length: int
    hypothesis_length: int


def _levenshtein_distance(ref: Sequence[str], hyp: Sequence[str]) -> tuple[int, int, int, int]:
    """
    Compute edit distance between reference and hypothesis sequences.

    Returns (substitutions, deletions, insertions, hits).
    """
    n = len(ref)
    m = len(hyp)

    if n == 0 and m == 0:
        return 0, 0, 0, 0
    if n == 0:
        return 0, 0, m, 0
    if m == 0:
        return 0, n, 0, 0

    # DP Matrix: dp[i][j] stores (cost, S, D, I, H)
    # To optimize memory, we keep two rows of states:
    # State: (cost, subs, dels, ins, hits)
    prev_row = [(j, 0, 0, j, 0) for j in range(m + 1)]

    for i in range(1, n + 1):
        curr_row = [(i, 0, i, 0, 0)] + [(0, 0, 0, 0, 0)] * m
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                # Match (hit)
                cost, s, d, ins, h = prev_row[j - 1]
                curr_row[j] = (cost, s, d, ins, h + 1)
            else:
                # Substitution
                sub_cost, sub_s, sub_d, sub_ins, sub_h = prev_row[j - 1]
                cand_sub = (sub_cost + 1, sub_s + 1, sub_d, sub_ins, sub_h)

                # Deletion (from ref)
                del_cost, del_s, del_d, del_ins, del_h = prev_row[j]
                cand_del = (del_cost + 1, del_s, del_d + 1, del_ins, del_h)

                # Insertion (into hyp)
                ins_cost, ins_s, ins_d, ins_ins, ins_h = curr_row[j - 1]
                cand_ins = (ins_cost + 1, ins_s, ins_d, ins_ins + 1, ins_h)

                # Pick minimum cost (tie breaker: sub, del, ins)
                curr_row[j] = min(cand_sub, cand_del, cand_ins, key=lambda x: x[0])

        prev_row = curr_row

    _, s, d, ins, h = prev_row[m]
    return s, d, ins, h


def calculate_wer(reference: str, hypothesis: str) -> EditStats:
    """
    Calculate Word Error Rate (WER) between reference and hypothesis.

    WER = (S + D + I) / N, where N is the number of words in the reference.
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    n = len(ref_words)

    if n == 0:
        if len(hyp_words) == 0:
            return EditStats(0.0, 0, 0, 0, 0, 0, 0)
        return EditStats(1.0, 0, 0, len(hyp_words), 0, 0, len(hyp_words))

    s, d, ins, h = _levenshtein_distance(ref_words, hyp_words)
    wer = (s + d + ins) / float(n)

    return EditStats(
        error_rate=wer,
        substitutions=s,
        deletions=d,
        insertions=ins,
        hits=h,
        reference_length=n,
        hypothesis_length=len(hyp_words),
    )


def calculate_cer(reference: str, hypothesis: str) -> EditStats:
    """
    Calculate Character Error Rate (CER) between reference and hypothesis.

    Characters are compared excluding whitespace.
    """
    ref_chars = [c for c in reference if not c.isspace()]
    hyp_chars = [c for c in hypothesis if not c.isspace()]
    n = len(ref_chars)

    if n == 0:
        if len(hyp_chars) == 0:
            return EditStats(0.0, 0, 0, 0, 0, 0, 0)
        return EditStats(1.0, 0, 0, len(hyp_chars), 0, 0, len(hyp_chars))

    s, d, ins, h = _levenshtein_distance(ref_chars, hyp_chars)
    cer = (s + d + ins) / float(n)

    return EditStats(
        error_rate=cer,
        substitutions=s,
        deletions=d,
        insertions=ins,
        hits=h,
        reference_length=n,
        hypothesis_length=len(hyp_chars),
    )


def calculate_rtf(processing_time_seconds: float, audio_duration_seconds: float) -> float:
    """
    Calculate Real-Time Factor (RTF).

    RTF = processing_time / audio_duration.
    An RTF < 1.0 means faster than real-time execution.
    """
    if audio_duration_seconds <= 0.0:
        return 0.0
    return processing_time_seconds / audio_duration_seconds


def get_peak_memory_mb() -> float:
    """
    Get current peak memory usage in megabytes (MB) across macOS or Linux.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        # macOS returns ru_maxrss in bytes
        return float(usage) / (1024.0 * 1024.0)
    else:
        # Linux returns ru_maxrss in kilobytes
        return float(usage) / 1024.0
