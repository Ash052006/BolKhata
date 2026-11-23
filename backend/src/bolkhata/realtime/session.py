"""
Session manager orchestrating the push-to-talk audio loop and stage coordination.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

from bolkhata.asr.base import ASRProvider, ASRResult
from bolkhata.asr.common import BYTES_PER_SECOND
from bolkhata.common.logging import get_logger
from bolkhata.config.settings import Settings
from bolkhata.llm.base import ChatMessage, LLMProvider
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
)
from bolkhata.realtime.state import (
    InvalidStateTransitionError,
    SessionState,
    SessionStateMachine,
)
from bolkhata.tts.base import TTSProvider, TTSResult

logger = get_logger(__name__)


class WebSocketSender(Protocol):
    """Protocol for sending JSON messages over WebSocket."""

    async def send_json(self, data: dict[str, Any]) -> None: ...


class SessionManager:
    """
    Manages a single client WebSocket push-to-talk session.

    Coordinates:
    - Bounded binary audio buffering (enforcing asr_max_duration_seconds).
    - Session state machine transitions and invalid transition rejection.
    - Asynchronous turn pipeline: ASR -> LLM -> TTS with stage latency timing.
    - Generation ID tagging and dropping of stale turns upon cancellation.
    """

    def __init__(
        self,
        sender: WebSocketSender,
        settings: Settings,
        asr_provider: ASRProvider,
        llm_provider: LLMProvider,
        tts_provider: TTSProvider,
        session_id: str | None = None,
    ) -> None:
        self.sender = sender
        self.settings = settings
        self.asr_provider = asr_provider
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider

        self.state_machine = SessionStateMachine(session_id=session_id)
        self.session_id: str = self.state_machine.session_id

        self._audio_buffer: bytearray = bytearray()
        self._max_audio_bytes: int = int(self.settings.asr_max_duration_seconds * BYTES_PER_SECOND)

        self._language: str = "hi"
        self._initial_prompt: str | None = None
        self._active_turn_task: asyncio.Task[None] | None = None

    @property
    def state(self) -> SessionState:
        return self.state_machine.state

    async def emit_state(self) -> None:
        """Send current session state message to client."""
        msg = SessionStateMessage(
            session_id=self.session_id,
            state=self.state_machine.state.value,
            turn_id=self.state_machine.turn_id,
            generation_id=self.state_machine.generation_id,
        )
        await self.sender.send_json(msg.model_dump())

    async def emit_error(self, code: str, message: str, turn_id: str | None = None) -> None:
        """Send structured error frame to client."""
        msg = ErrorMessage(
            session_id=self.session_id,
            turn_id=turn_id or self.state_machine.turn_id,
            generation_id=self.state_machine.generation_id,
            code=code,
            message=message,
        )
        await self.sender.send_json(msg.model_dump())

    async def handle_start_utterance(self, msg: StartUtteranceMessage) -> None:
        """Handle client start_utterance event."""
        # Cancel any active turn task if client restarts while speaking
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()
            self._active_turn_task = None

        try:
            self.state_machine.transition_to(
                SessionState.LISTENING,
                turn_id=msg.turn_id,
                reason="client_start_utterance",
            )
        except InvalidStateTransitionError as err:
            await self.emit_error("INVALID_STATE_TRANSITION", str(err), turn_id=msg.turn_id)
            return

        self._audio_buffer.clear()
        self._language = msg.language
        self._initial_prompt = msg.initial_prompt
        await self.emit_state()

    async def handle_audio_frame(self, chunk: bytes) -> None:
        """Accumulate binary audio frame while in LISTENING state."""
        if self.state_machine.state != SessionState.LISTENING:
            # Drop audio frame silently if not actively listening
            return

        if len(self._audio_buffer) + len(chunk) > self._max_audio_bytes:
            logger.warning(
                "session_audio_buffer_overflow",
                session_id=self.session_id,
                turn_id=self.state_machine.turn_id,
                max_bytes=self._max_audio_bytes,
            )
            await self.emit_error(
                "AUDIO_TOO_LONG",
                f"Audio exceeded maximum duration of {self.settings.asr_max_duration_seconds}s.",
            )
            self._audio_buffer.clear()
            self.state_machine.reset_to_idle(reason="audio_too_long")
            await self.emit_state()
            return

        self._audio_buffer.extend(chunk)

    async def handle_end_utterance(self, msg: EndUtteranceMessage) -> None:
        """Handle client end_utterance event."""
        try:
            _, generation_id = self.state_machine.transition_to(
                SessionState.THINKING,
                turn_id=msg.turn_id,
                reason="client_end_utterance",
            )
        except InvalidStateTransitionError as err:
            await self.emit_error("INVALID_STATE_TRANSITION", str(err), turn_id=msg.turn_id)
            return

        await self.emit_state()

        # Copy audio buffer and spawn background turn pipeline task
        audio_snapshot = bytes(self._audio_buffer)
        self._audio_buffer.clear()

        turn_id = msg.turn_id
        assert generation_id is not None

        self._active_turn_task = asyncio.create_task(
            self._execute_turn(turn_id, generation_id, audio_snapshot)
        )

    async def handle_cancel_utterance(self, msg: CancelUtteranceMessage) -> None:
        """Handle client cancel_utterance event."""
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()
            self._active_turn_task = None

        self._audio_buffer.clear()
        self.state_machine.reset_to_idle(reason="client_cancel")
        await self.emit_state()

    async def _execute_turn(self, turn_id: str, generation_id: str, audio_bytes: bytes) -> None:
        """Execute ASR -> LLM -> TTS pipeline for a single turn."""
        turn_start = time.perf_counter()
        asr_ms = 0.0
        llm_ms = 0.0
        tts_ms = 0.0

        try:
            # -------------------------------------------------------------
            # Stage 1: Automatic Speech Recognition (ASR)
            # -------------------------------------------------------------
            asr_start = time.perf_counter()
            asr_result: ASRResult = await self.asr_provider.transcribe(
                audio_bytes=audio_bytes,
                language=self._language,
                initial_prompt=self._initial_prompt,
            )
            asr_ms = (time.perf_counter() - asr_start) * 1000.0

            # Guard against stale turn execution
            if self.state_machine.generation_id != generation_id:
                logger.info("stale_turn_dropped_after_asr", generation_id=generation_id)
                return

            word_items = [
                WordTimingItem(
                    word=w.word,
                    start_ms=w.start_ms,
                    end_ms=w.end_ms,
                    confidence=w.confidence,
                )
                for w in asr_result.words
            ]

            transcript_msg = TranscriptMessage(
                session_id=self.session_id,
                turn_id=turn_id,
                generation_id=generation_id,
                text=asr_result.text,
                confidence=asr_result.confidence,
                language=asr_result.language,
                duration_ms=asr_result.duration_ms,
                words=word_items,
            )
            await self.sender.send_json(transcript_msg.model_dump())

            # If transcript is empty, finish turn immediately
            if not asr_result.text.strip():
                total_ms = (time.perf_counter() - turn_start) * 1000.0
                timings_msg = TimingsMessage(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    generation_id=generation_id,
                    asr_ms=asr_ms,
                    llm_ms=0.0,
                    tts_ms=0.0,
                    total_ms=total_ms,
                )
                await self.sender.send_json(timings_msg.model_dump())
                self.state_machine.reset_to_idle(reason="empty_transcript")
                await self.emit_state()
                return

            # -------------------------------------------------------------
            # Stage 2: Language Model (LLM)
            # -------------------------------------------------------------
            llm_start = time.perf_counter()
            messages = [ChatMessage(role="user", content=asr_result.text)]
            token_list: list[str] = []

            async for token in self.llm_provider.stream_chat(messages):
                if self.state_machine.generation_id != generation_id:
                    logger.info("stale_turn_dropped_during_llm", generation_id=generation_id)
                    return
                token_list.append(token)
                await self.sender.send_json(
                    AssistantTextMessage(
                        session_id=self.session_id,
                        turn_id=turn_id,
                        generation_id=generation_id,
                        token=token,
                        is_final=False,
                    ).model_dump()
                )

            llm_ms = (time.perf_counter() - llm_start) * 1000.0
            full_assistant_text = "".join(token_list)

            # Emit final token message
            await self.sender.send_json(
                AssistantTextMessage(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    generation_id=generation_id,
                    token="",
                    is_final=True,
                ).model_dump()
            )

            # -------------------------------------------------------------
            # Stage 3: Text to Speech (TTS)
            # -------------------------------------------------------------
            if full_assistant_text.strip():
                tts_start = time.perf_counter()
                self.state_machine.transition_to(
                    SessionState.SPEAKING,
                    turn_id=turn_id,
                    reason="tts_start",
                )
                await self.emit_state()

                tts_res: TTSResult = await self.tts_provider.synthesize(
                    full_assistant_text, voice=None
                )
                tts_ms = (time.perf_counter() - tts_start) * 1000.0

                if self.state_machine.generation_id != generation_id:
                    logger.info("stale_turn_dropped_after_tts", generation_id=generation_id)
                    return

                # Send audio chunk
                audio_msg = AudioChunkMessage.from_pcm(
                    session_id=self.session_id,
                    turn_id=turn_id,
                    generation_id=generation_id,
                    sequence_number=0,
                    pcm_bytes=tts_res.audio_bytes,
                    is_final=True,
                    sample_rate=tts_res.sample_rate,
                )
                await self.sender.send_json(audio_msg.model_dump())

            # -------------------------------------------------------------
            # Stage 4: Turn Timings Telemetry
            # -------------------------------------------------------------
            total_ms = (time.perf_counter() - turn_start) * 1000.0
            timings_msg = TimingsMessage(
                session_id=self.session_id,
                turn_id=turn_id,
                generation_id=generation_id,
                asr_ms=asr_ms,
                llm_ms=llm_ms,
                tts_ms=tts_ms,
                total_ms=total_ms,
            )
            await self.sender.send_json(timings_msg.model_dump())

            # -------------------------------------------------------------
            # Stage 5: Transition to IDLE
            # -------------------------------------------------------------
            self.state_machine.reset_to_idle(reason="turn_completed")
            await self.emit_state()

        except asyncio.CancelledError:
            logger.info("turn_execution_cancelled", generation_id=generation_id)
            self.state_machine.reset_to_idle(reason="task_cancelled")
            raise
        except Exception as err:
            logger.exception("turn_execution_error", generation_id=generation_id, error=str(err))
            await self.emit_error("TURN_EXECUTION_FAILED", str(err), turn_id=turn_id)
            self.state_machine.reset_to_idle(reason="execution_error")
            await self.emit_state()

    async def close(self) -> None:
        """Clean up on WebSocket disconnection."""
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()
            self._active_turn_task = None
        self._audio_buffer.clear()
        self.state_machine.reset_to_idle(reason="connection_closed")
