"""
Integration tests for the /ws/session realtime push-to-talk WebSocket endpoint.
"""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from bolkhata.api.app import create_app


def test_websocket_initial_connection_and_idle_state() -> None:
    """Verify WebSocket connection immediately emits session_state IDLE."""
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/session") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "session_state"
            assert msg["state"] == "IDLE"
            assert msg["session_id"] is not None
            assert msg["turn_id"] is None
            assert msg["generation_id"] is None


def test_websocket_full_turn_end_to_end() -> None:
    """
    Verify complete push-to-talk loop without a microphone:
    1. start_utterance transitions to LISTENING.
    2. Binary PCM frames are buffered.
    3. end_utterance triggers THINKING and generates generation_id.
    4. ASR emits transcript.
    5. LLM emits assistant_text tokens.
    6. TTS transitions to SPEAKING and emits audio_chunk.
    7. Turn finishes with timings and transitions to IDLE.
    """
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/session") as ws:
            # 1. Initial IDLE state
            msg = ws.receive_json()
            assert msg["type"] == "session_state"
            assert msg["state"] == "IDLE"

            # 2. Start utterance
            ws.send_json(
                {
                    "type": "start_utterance",
                    "turn_id": "turn-test-1",
                    "language": "hi",
                    "initial_prompt": "Sharma ji, udhaar",
                }
            )

            listening_msg = ws.receive_json()
            assert listening_msg["type"] == "session_state"
            assert listening_msg["state"] == "LISTENING"
            assert listening_msg["turn_id"] == "turn-test-1"

            # 3. Stream binary PCM audio frames (16kHz s16le PCM, ~200ms)
            audio_frame = b"\x00\x00" * 3200
            ws.send_bytes(audio_frame)

            # 4. End utterance
            ws.send_json({"type": "end_utterance", "turn_id": "turn-test-1"})

            # 5. Receive THINKING state
            thinking_msg = ws.receive_json()
            assert thinking_msg["type"] == "session_state"
            assert thinking_msg["state"] == "THINKING"
            generation_id = thinking_msg["generation_id"]
            assert generation_id is not None

            # 6. Receive transcript
            transcript_msg = ws.receive_json()
            assert transcript_msg["type"] == "transcript"
            assert transcript_msg["turn_id"] == "turn-test-1"
            assert transcript_msg["generation_id"] == generation_id
            assert len(transcript_msg["text"]) > 0

            # 7. Collect assistant_text stream tokens until is_final is True
            tokens: list[str] = []
            while True:
                token_msg = ws.receive_json()
                assert token_msg["type"] == "assistant_text"
                assert token_msg["generation_id"] == generation_id
                tokens.append(token_msg["token"])
                if token_msg["is_final"]:
                    break

            full_text = "".join(tokens)
            assert len(full_text) > 0

            # 8. Receive SPEAKING state
            speaking_msg = ws.receive_json()
            assert speaking_msg["type"] == "session_state"
            assert speaking_msg["state"] == "SPEAKING"

            # 9. Receive audio_chunk containing synthesized PCM
            audio_msg = ws.receive_json()
            assert audio_msg["type"] == "audio_chunk"
            assert audio_msg["generation_id"] == generation_id
            assert audio_msg["sample_rate"] == 16000
            decoded_pcm = base64.b64decode(audio_msg["data_b64"])
            assert len(decoded_pcm) > 0
            # Headerless 16-bit PCM must have an even number of bytes
            assert len(decoded_pcm) % 2 == 0

            # 10. Receive timings
            timings_msg = ws.receive_json()
            assert timings_msg["type"] == "timings"
            assert timings_msg["generation_id"] == generation_id
            assert timings_msg["asr_ms"] >= 0.0
            assert timings_msg["llm_ms"] >= 0.0
            assert timings_msg["tts_ms"] >= 0.0
            assert timings_msg["total_ms"] >= 0.0

            # 11. Final IDLE state
            final_idle = ws.receive_json()
            assert final_idle["type"] == "session_state"
            assert final_idle["state"] == "IDLE"
            assert final_idle["turn_id"] is None
            assert final_idle["generation_id"] is None


def test_websocket_cancellation_during_listening() -> None:
    """Verify cancel_utterance during recording immediately resets to IDLE."""
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/session") as ws:
            ws.receive_json()  # IDLE

            ws.send_json({"type": "start_utterance", "turn_id": "turn-cancel-1"})
            msg = ws.receive_json()
            assert msg["state"] == "LISTENING"

            # Send some audio
            ws.send_bytes(b"\x00\x00" * 800)

            # Cancel
            ws.send_json({"type": "cancel_utterance", "turn_id": "turn-cancel-1"})
            cancel_msg = ws.receive_json()
            assert cancel_msg["type"] == "session_state"
            assert cancel_msg["state"] == "IDLE"
            assert cancel_msg["turn_id"] is None


def test_websocket_malformed_client_message_emits_error() -> None:
    """Verify malformed JSON or unknown type emits structured error frame."""
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/session") as ws:
            ws.receive_json()  # IDLE

            # Send invalid JSON structure
            ws.send_text("not a valid json")
            err_msg = ws.receive_json()
            assert err_msg["type"] == "error"
            assert err_msg["code"] == "INVALID_MESSAGE"

            # Send unknown message type
            ws.send_json({"type": "bogus_command"})
            err_msg_2 = ws.receive_json()
            assert err_msg_2["type"] == "error"
            assert err_msg_2["code"] == "INVALID_MESSAGE"


def test_websocket_out_of_order_transition_emits_error() -> None:
    """Verify attempting end_utterance while in IDLE state emits error."""
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/session") as ws:
            ws.receive_json()  # IDLE

            # Send end_utterance without starting first
            ws.send_json({"type": "end_utterance", "turn_id": "turn-orphan"})
            err_msg = ws.receive_json()
            assert err_msg["type"] == "error"
            assert err_msg["code"] == "INVALID_STATE_TRANSITION"
