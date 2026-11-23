"""
WebSocket endpoint for realtime push-to-talk audio streaming.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bolkhata.common.logging import get_logger
from bolkhata.common.registry import ProviderRegistry
from bolkhata.config.settings import Settings
from bolkhata.config.settings import settings as global_settings
from bolkhata.realtime.protocol import parse_client_message
from bolkhata.realtime.session import SessionManager

logger = get_logger(__name__)

router = APIRouter(tags=["session"])


@router.websocket("/ws/session")
async def websocket_session_endpoint(websocket: WebSocket) -> None:
    """
    Full-duplex WebSocket endpoint for push-to-talk interaction.

    Accepts:
      - JSON text frames: start_utterance, end_utterance, cancel_utterance.
      - Binary frames: 16 kHz s16le PCM audio.

    Emits:
      - JSON text frames: session_state, transcript, assistant_text, audio_chunk, timings, error.
    """
    await websocket.accept()

    registry: ProviderRegistry | None = getattr(websocket.app.state, "registry", None)
    if registry is None:
        logger.error("session_endpoint_missing_provider_registry")
        await websocket.close(code=1011, reason="Server error: Provider registry not initialized.")
        return

    settings: Settings = getattr(websocket.app.state, "settings", global_settings)

    session_manager = SessionManager(
        sender=websocket,
        settings=settings,
        asr_provider=registry.asr,
        llm_provider=registry.llm,
        tts_provider=registry.tts,
    )

    # Emit initial IDLE state
    await session_manager.emit_state()

    logger.info("websocket_session_connected", session_id=session_manager.session_id)

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            # Handle binary audio frame
            if "bytes" in message and message["bytes"] is not None:
                audio_bytes: bytes = message["bytes"]
                await session_manager.handle_audio_frame(audio_bytes)
                continue

            # Handle text control message
            if "text" in message and message["text"] is not None:
                text_data: str = message["text"]
                try:
                    payload: dict[str, Any] = json.loads(text_data)
                    client_msg = parse_client_message(payload)
                except Exception as err:
                    logger.warning(
                        "websocket_invalid_client_message", error=str(err), raw_text=text_data
                    )
                    await session_manager.emit_error("INVALID_MESSAGE", f"Malformed message: {err}")
                    continue

                if client_msg.type == "start_utterance":
                    await session_manager.handle_start_utterance(client_msg)
                elif client_msg.type == "end_utterance":
                    await session_manager.handle_end_utterance(client_msg)
                elif client_msg.type == "cancel_utterance":
                    await session_manager.handle_cancel_utterance(client_msg)

    except WebSocketDisconnect:
        logger.info("websocket_session_disconnected", session_id=session_manager.session_id)
    except Exception as err:
        logger.exception(
            "websocket_session_unhandled_error",
            session_id=session_manager.session_id,
            error=str(err),
        )
    finally:
        await session_manager.close()
