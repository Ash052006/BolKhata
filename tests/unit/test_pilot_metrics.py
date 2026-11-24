"""
Unit and integration tests for F7 Pilot Instrumentation and Telemetry.
"""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from bolkhata.api.app import create_app
from bolkhata.common.pilot import PilotMetricEntry, PilotMetricsStore, pilot_store


def test_pilot_metric_entry_privacy_validation() -> None:
    # Valid entry
    e = PilotMetricEntry(
        participant_code="P01",
        session_id="sess-1",
        turn_id="turn-1",
        interaction_type="voice_entry",
        time_to_confirm_ms=2300.0,
        participant_comment="Bohat badiya laga",
    )
    e.validate_privacy()

    # Invalid participant code (spaces or symbols)
    bad_code = PilotMetricEntry(
        participant_code="Shopkeeper Ramesh",
        session_id="s",
        turn_id="t",
        interaction_type="voice_entry",
        time_to_confirm_ms=100.0,
    )
    with pytest.raises(ValueError, match="Invalid participant code"):
        bad_code.validate_privacy()

    # Leaked phone number in comment
    bad_comment = PilotMetricEntry(
        participant_code="P02",
        session_id="s",
        turn_id="t",
        interaction_type="voice_entry",
        time_to_confirm_ms=100.0,
        participant_comment="Customer number was 9876543210 please note",
    )
    with pytest.raises(ValueError, match="phone number"):
        bad_comment.validate_privacy()


def test_pilot_metrics_store_summary_and_csv() -> None:
    store = PilotMetricsStore(enabled=True)
    e1 = PilotMetricEntry(
        participant_code="P01",
        session_id="s1",
        turn_id="t1",
        interaction_type="voice_entry",
        time_to_confirm_ms=2000.0,
        correction_count=0,
    )
    e2 = PilotMetricEntry(
        participant_code="P01",
        session_id="s1",
        turn_id="t2",
        interaction_type="voice_entry",
        time_to_confirm_ms=4000.0,
        correction_count=1,
    )
    e3 = PilotMetricEntry(
        participant_code="P02",
        session_id="s2",
        turn_id="t3",
        interaction_type="voice_entry",
        time_to_confirm_ms=3000.0,
        failure_type="network_retry",
    )
    store.record(e1)
    store.record(e2)
    store.record(e3)

    summary = store.get_summary()
    assert summary["total_interactions"] == 3
    assert summary["participant_count"] == 2
    assert summary["min_time_ms"] == 2000.0
    assert summary["median_time_ms"] == 3000.0
    assert summary["max_time_ms"] == 4000.0
    assert summary["correction_rate"] == round(1 / 3, 3)
    assert summary["failure_rate"] == round(1 / 3, 3)

    csv_data = store.export_csv()
    reader = csv.reader(io.StringIO(csv_data))
    rows = list(reader)
    assert len(rows) == 4  # Header + 3 entries
    assert rows[0][0] == "Participant Code"
    assert rows[1][0] == "P01"


@pytest.mark.asyncio
async def test_pilot_api_endpoints() -> None:
    app = create_app()
    pilot_store.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Record metric
        rec_resp = await client.post(
            "/api/v1/pilot/record",
            json={
                "participant_code": "P-TEST",
                "session_id": "sess-test",
                "turn_id": "turn-test",
                "interaction_type": "voice_entry",
                "time_to_confirm_ms": 1500.0,
                "correction_count": 0,
                "participant_comment": "Fast and smooth",
            },
        )
        assert rec_resp.status_code == 201
        assert rec_resp.json()["status"] == "recorded"

        # Check summary
        sum_resp = await client.get("/api/v1/pilot/summary")
        assert sum_resp.status_code == 200
        assert sum_resp.json()["total_interactions"] == 1
        assert sum_resp.json()["participant_count"] == 1

        # Check CSV export
        exp_resp = await client.get("/api/v1/pilot/export/csv")
        assert exp_resp.status_code == 200
        assert "P-TEST" in exp_resp.text

        # Clear
        clr_resp = await client.delete("/api/v1/pilot/clear")
        assert clr_resp.status_code == 200
        sum_resp2 = await client.get("/api/v1/pilot/summary")
        assert sum_resp2.json()["total_interactions"] == 0


def test_analyze_pilot_script(tmp_path: Path) -> None:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "analyze_pilot.py"
    spec = importlib.util.spec_from_file_location("analyze_pilot", script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    csv_file = tmp_path / "trial_test.csv"
    csv_file.write_text(
        "Participant Code,Session ID,Turn ID,Interaction Type,Time To Confirm (ms),Correction Count,Retry Count,Failure Type,Offline Mode,Language,Participant Comment,Created At\n"
        "P01,s1,t1,voice_entry,2500.0,0,0,,False,hi,Kaam aasan ho gaya,2026-11-24T12:00:00\n"
        "P01,s1,t2,baseline_manual,8500.0,0,0,,False,hi,,2026-11-24T12:01:00\n",
        encoding="utf-8",
    )
    report = mod.analyze_csv(csv_file)
    assert "# BolKhata Pilot Trial Analysis Report" in report
    assert "2.50s" in report
    assert "8.50s" in report
    assert "Kaam aasan ho gaya" in report
