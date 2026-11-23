"""
Unit tests for realtime WebSocket protocol serialization and message schemas.
"""

from __future__ import annotations

import base64

import pytest

from bolkhata.realtime.protocol import (
    AssistantTextMessage,
    AudioChunkMessage,
    CancelUtteranceMessage,
    EndUtteranceMessage,
    ErrorMessage,
    SessionStateMessage,
    StartUtteranceMessage,
    TimingsMessage,
    TranscriptMessage,
    WordTimingItem,
    parse_client_message,
)


class TestClientMessageParsing:
    """Test client message schema validation and parsing."""

    def test_parse_valid_start_utterance(self) -> None:
        data = {
            "type": "start_utterance",
            "turn_id": "turn-123",
            "language": "hi",
            "initial_prompt": "Sharma ji",
        }
        msg = parse_client_message(data)
        assert isinstance(msg, StartUtteranceMessage)
        assert msg.turn_id == "turn-123"
        assert msg.language == "hi"
        assert msg.initial_prompt == "Sharma ji"

    def test_parse_start_utterance_defaults(self) -> None:
        data = {"type": "start_utterance", "turn_id": "turn-456"}
        msg = parse_client_message(data)
        assert isinstance(msg, StartUtteranceMessage)
        assert msg.language == "hi"
        assert msg.initial_prompt is None

    def test_parse_valid_end_utterance(self) -> None:
        data = {"type": "end_utterance", "turn_id": "turn-123"}
        msg = parse_client_message(data)
        assert isinstance(msg, EndUtteranceMessage)
        assert msg.turn_id == "turn-123"

    def test_parse_valid_cancel_utterance(self) -> None:
        data = {"type": "cancel_utterance", "turn_id": "turn-123"}
        msg = parse_client_message(data)
        assert isinstance(msg, CancelUtteranceMessage)
        assert msg.turn_id == "turn-123"

    def test_parse_unknown_type_raises_error(self) -> None:
        data = {"type": "unknown_action", "foo": "bar"}
        with pytest.raises(ValueError, match="Unknown client message type: unknown_action"):
            parse_client_message(data)

    def test_parse_missing_type_raises_error(self) -> None:
        data = {"turn_id": "123"}
        with pytest.raises(ValueError, match="Unknown client message type: None"):
            parse_client_message(data)


class TestServerMessageSerialization:
    """Test server message serialization models."""

    def test_session_state_message(self) -> None:
        msg = SessionStateMessage(
            session_id="sess-1",
            state="LISTENING",
            turn_id="turn-1",
            generation_id=None,
        )
        payload = msg.model_dump()
        assert payload["type"] == "session_state"
        assert payload["session_id"] == "sess-1"
        assert payload["state"] == "LISTENING"
        assert payload["turn_id"] == "turn-1"
        assert payload["generation_id"] is None

    def test_transcript_message(self) -> None:
        words = [
            WordTimingItem(word="Sharma", start_ms=0.0, end_ms=300.0, confidence=0.9),
            WordTimingItem(word="ji", start_ms=300.0, end_ms=500.0, confidence=None),
        ]
        msg = TranscriptMessage(
            session_id="sess-1",
            turn_id="turn-1",
            generation_id="gen-1",
            text="Sharma ji",
            confidence=0.9,
            language="hi",
            duration_ms=500.0,
            words=words,
        )
        payload = msg.model_dump()
        assert payload["type"] == "transcript"
        assert payload["text"] == "Sharma ji"
        assert len(payload["words"]) == 2
        assert payload["words"][0]["word"] == "Sharma"
        assert payload["words"][1]["confidence"] is None

    def test_assistant_text_message(self) -> None:
        msg = AssistantTextMessage(
            session_id="sess-1",
            turn_id="turn-1",
            generation_id="gen-1",
            token="Sahi hai?",
            is_final=True,
        )
        payload = msg.model_dump()
        assert payload["type"] == "assistant_text"
        assert payload["token"] == "Sahi hai?"
        assert payload["is_final"] is True

    def test_audio_chunk_message_from_pcm(self) -> None:
        raw_pcm = b"\x00\x01\x02\x03"
        msg = AudioChunkMessage.from_pcm(
            session_id="sess-1",
            turn_id="turn-1",
            generation_id="gen-1",
            sequence_number=0,
            pcm_bytes=raw_pcm,
            is_final=True,
            sample_rate=16000,
        )
        payload = msg.model_dump()
        assert payload["type"] == "audio_chunk"
        assert payload["sequence_number"] == 0
        assert payload["is_final"] is True
        assert payload["sample_rate"] == 16000
        assert base64.b64decode(payload["data_b64"]) == raw_pcm

    def test_timings_message(self) -> None:
        msg = TimingsMessage(
            session_id="sess-1",
            turn_id="turn-1",
            generation_id="gen-1",
            asr_ms=100.5,
            llm_ms=50.2,
            tts_ms=75.3,
            total_ms=226.0,
        )
        payload = msg.model_dump()
        assert payload["type"] == "timings"
        assert payload["asr_ms"] == 100.5
        assert payload["total_ms"] == 226.0

    def test_error_message(self) -> None:
        msg = ErrorMessage(
            session_id="sess-1",
            turn_id="turn-1",
            generation_id=None,
            code="INVALID_STATE",
            message="Cannot start utterance",
        )
        payload = msg.model_dump()
        assert payload["type"] == "error"
        assert payload["code"] == "INVALID_STATE"
