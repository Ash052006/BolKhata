"""
API routes for Pilot Instrumentation (Feature F7).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from bolkhata.common.pilot import PilotMetricEntry, pilot_store

router = APIRouter(prefix="/api/v1/pilot", tags=["pilot"])


class PilotRecordRequest(BaseModel):
    participant_code: str = Field(..., max_length=16, pattern=r"^[A-Za-z0-9_-]+$")
    session_id: str
    turn_id: str
    interaction_type: str = "voice_entry"
    time_to_confirm_ms: float = Field(..., ge=0.0)
    correction_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    failure_type: str | None = None
    offline_mode: bool = False
    language: str = "hi"
    participant_comment: str | None = Field(default=None, max_length=200)


@router.post("/record", status_code=status.HTTP_201_CREATED)
async def record_pilot_metric(payload: PilotRecordRequest) -> dict[str, Any]:
    """Record an anonymized trial interaction."""
    entry = PilotMetricEntry(
        participant_code=payload.participant_code,
        session_id=payload.session_id,
        turn_id=payload.turn_id,
        interaction_type=payload.interaction_type,
        time_to_confirm_ms=payload.time_to_confirm_ms,
        correction_count=payload.correction_count,
        retry_count=payload.retry_count,
        failure_type=payload.failure_type,
        offline_mode=payload.offline_mode,
        language=payload.language,
        participant_comment=payload.participant_comment,
    )
    try:
        pilot_store.record(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    return {"status": "recorded", "participant_code": payload.participant_code}


@router.get("/export/csv")
async def export_pilot_csv() -> Response:
    """Download pilot session logs as CSV."""
    csv_text = pilot_store.export_csv()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bolkhata_pilot_trial.csv"'},
    )


@router.get("/summary")
async def get_pilot_summary() -> dict[str, Any]:
    """Get aggregate statistics across all recorded trial interactions."""
    return pilot_store.get_summary()


@router.delete("/clear")
async def clear_pilot_data() -> dict[str, str]:
    """Reset pilot trial metrics buffer."""
    pilot_store.clear()
    return {"status": "cleared"}
