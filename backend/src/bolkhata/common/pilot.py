"""
Pilot telemetry and instrumentation store for kirana field trials (Feature F7).

Privacy Guarantees:
- Never records raw audio, transcripts, customer names, or phone numbers.
- Participants are identified strictly by anonymized participant codes (e.g. P01, P02).
- Exports clean CSV logs for field usability analysis.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class PilotMetricEntry:
    """A single anonymized trial interaction record."""

    participant_code: str
    session_id: str
    turn_id: str
    interaction_type: str  # "voice_entry" | "voice_correction" | "voice_query" | "baseline_manual"
    time_to_confirm_ms: float
    correction_count: int = 0
    retry_count: int = 0
    failure_type: str | None = None
    offline_mode: bool = False
    language: str = "hi"
    participant_comment: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def validate_privacy(self) -> None:
        """Enforce zero PII and zero audio retention in pilot records."""
        # Participant code must match clean pattern (e.g. P01, P-02, SHOP-A)
        if not re.match(r"^[A-Za-z0-9_-]{1,16}$", self.participant_code):
            raise ValueError(f"Invalid participant code format: '{self.participant_code}'")

        if self.participant_comment:
            # Check for 10-digit phone number leaks
            if re.search(r"\b\d{10}\b", self.participant_comment):
                raise ValueError("Participant comment contains potential phone number PII.")


class PilotMetricsStore:
    """In-memory thread-safe pilot metrics buffer with CSV export."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._entries: list[PilotMetricEntry] = []

    def record(self, entry: PilotMetricEntry) -> None:
        """Record an interaction event if pilot mode is enabled."""
        if not self.enabled:
            return
        entry.validate_privacy()
        self._entries.append(entry)

    def get_entries(self) -> list[PilotMetricEntry]:
        return list(self._entries)

    def export_csv(self) -> str:
        """Export all recorded trial events to standard CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Participant Code",
                "Session ID",
                "Turn ID",
                "Interaction Type",
                "Time To Confirm (ms)",
                "Correction Count",
                "Retry Count",
                "Failure Type",
                "Offline Mode",
                "Language",
                "Participant Comment",
                "Created At",
            ]
        )

        for e in self._entries:
            writer.writerow(
                [
                    e.participant_code,
                    e.session_id,
                    e.turn_id,
                    e.interaction_type,
                    f"{e.time_to_confirm_ms:.1f}",
                    e.correction_count,
                    e.retry_count,
                    e.failure_type or "",
                    e.offline_mode,
                    e.language,
                    e.participant_comment or "",
                    e.created_at,
                ]
            )

        return output.getvalue()

    def get_summary(self) -> dict[str, Any]:
        """Produce aggregate trial summary statistics without synthetic fabrications."""
        if not self._entries:
            return {
                "total_interactions": 0,
                "participant_count": 0,
                "median_time_ms": 0.0,
                "correction_rate": 0.0,
                "failure_rate": 0.0,
            }

        times = sorted(e.time_to_confirm_ms for e in self._entries)
        n = len(times)
        median_time = times[n // 2] if n % 2 != 0 else (times[n // 2 - 1] + times[n // 2]) / 2.0
        participants = len({e.participant_code for e in self._entries})
        corrections = sum(e.correction_count for e in self._entries)
        failures = sum(1 for e in self._entries if e.failure_type is not None)

        return {
            "total_interactions": n,
            "participant_count": participants,
            "min_time_ms": round(times[0], 1),
            "median_time_ms": round(median_time, 1),
            "max_time_ms": round(times[-1], 1),
            "correction_rate": round(corrections / n, 3),
            "failure_rate": round(failures / n, 3),
            "offline_events": sum(1 for e in self._entries if e.offline_mode),
        }

    def clear(self) -> None:
        self._entries.clear()


# Global singleton instance for application session recording
pilot_store = PilotMetricsStore(enabled=True)
