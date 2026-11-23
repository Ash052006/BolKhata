"""
Pydantic schemas and serialization models for the BolKhata WebSocket protocol.
"""

from __future__ import annotations

import base64
from typing import Any, Literal

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Client-to-Server Messages
# ---------------------------------------------------------------------------


class StartUtteranceMessage(BaseModel):
    """Client initiates push-to-talk recording."""

    type: Literal["start_utterance"] = "start_utterance"
    turn_id: str = Field(..., description="Unique client identifier for this turn")
    language: str = Field(default="hi", description="Spoken language code (e.g. hi, en)")
    initial_prompt: str | None = Field(
        default=None, description="Optional vocabulary prompt biasing prefix"
    )


class EndUtteranceMessage(BaseModel):
    """Client releases push-to-talk button, triggering transcription."""

    type: Literal["end_utterance"] = "end_utterance"
    turn_id: str = Field(..., description="Turn identifier matching the active turn")


class CancelUtteranceMessage(BaseModel):
    """Client cancels in-flight turn."""

    type: Literal["cancel_utterance"] = "cancel_utterance"
    turn_id: str = Field(..., description="Turn identifier to cancel")


ClientMessage = StartUtteranceMessage | EndUtteranceMessage | CancelUtteranceMessage


def parse_client_message(data: dict[str, Any]) -> ClientMessage:
    """Parse raw JSON dictionary into a typed client message."""
    msg_type = data.get("type")
    if msg_type == "start_utterance":
        return StartUtteranceMessage.model_validate(data)
    elif msg_type == "end_utterance":
        return EndUtteranceMessage.model_validate(data)
    elif msg_type == "cancel_utterance":
        return CancelUtteranceMessage.model_validate(data)
    else:
        raise ValueError(f"Unknown client message type: {msg_type}")


# ---------------------------------------------------------------------------
# Server-to-Client Messages
# ---------------------------------------------------------------------------


class SessionStateMessage(BaseModel):
    """Server notifies client of state machine transitions."""

    type: Literal["session_state"] = "session_state"
    session_id: str
    state: str
    turn_id: str | None = None
    generation_id: str | None = None


class WordTimingItem(BaseModel):
    """Word-level timing information."""

    word: str
    start_ms: float
    end_ms: float
    confidence: float | None = None


class TranscriptMessage(BaseModel):
    """Server emits ASR speech transcription."""

    type: Literal["transcript"] = "transcript"
    session_id: str
    turn_id: str
    generation_id: str
    text: str
    confidence: float | None = None
    language: str = "hi"
    duration_ms: float = 0.0
    words: list[WordTimingItem] = Field(default_factory=list)


class AssistantTextMessage(BaseModel):
    """Server emits assistant text or stream token."""

    type: Literal["assistant_text"] = "assistant_text"
    session_id: str
    turn_id: str
    generation_id: str
    token: str
    is_final: bool = False


class AudioChunkMessage(BaseModel):
    """Server emits synthesized PCM chunk for client playback."""

    type: Literal["audio_chunk"] = "audio_chunk"
    session_id: str
    turn_id: str
    generation_id: str
    sequence_number: int
    is_final: bool = False
    sample_rate: int = 16000
    data_b64: str

    @classmethod
    def from_pcm(
        cls,
        session_id: str,
        turn_id: str,
        generation_id: str,
        sequence_number: int,
        pcm_bytes: bytes,
        is_final: bool = False,
        sample_rate: int = 16000,
    ) -> AudioChunkMessage:
        return cls(
            session_id=session_id,
            turn_id=turn_id,
            generation_id=generation_id,
            sequence_number=sequence_number,
            is_final=is_final,
            sample_rate=sample_rate,
            data_b64=base64.b64encode(pcm_bytes).decode("ascii"),
        )


class TimingsMessage(BaseModel):
    """Server emits per-stage latency timings."""

    type: Literal["timings"] = "timings"
    session_id: str
    turn_id: str
    generation_id: str
    asr_ms: float
    llm_ms: float
    tts_ms: float
    total_ms: float


class ErrorMessage(BaseModel):
    """Server emits error description."""

    type: Literal["error"] = "error"
    session_id: str
    turn_id: str | None = None
    generation_id: str | None = None
    code: str
    message: str
