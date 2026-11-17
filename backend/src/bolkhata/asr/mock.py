"""
Deterministic Mock ASR provider for offline testing and CI.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from bolkhata.asr.base import ASRPartialResult, ASRProvider, ASRResult, WordTiming


class MockASRProvider(ASRProvider):
    """
    Deterministic mock speech recognition provider.

    Does not download weights, touch network, or run real inference.
    Exposes explicit state flags for deterministic lifecycle verification.
    """

    def __init__(
        self,
        canned_text: str = "Sharma ji ko do sau pachaas udhaar",
        language: str = "hi",
        confidence: float | None = None,
        duration_ms: float = 1200.0,
        words: tuple[WordTiming, ...] | None = None,
    ) -> None:
        self.canned_text = canned_text
        self.language = language
        self.confidence = confidence
        self.duration_ms = duration_ms
        if words is None:
            self.words: tuple[WordTiming, ...] = (
                WordTiming(word="Sharma", start_ms=0.0, end_ms=300.0, confidence=confidence),
                WordTiming(word="ji", start_ms=310.0, end_ms=450.0, confidence=confidence),
                WordTiming(word="ko", start_ms=460.0, end_ms=550.0, confidence=confidence),
                WordTiming(word="do", start_ms=560.0, end_ms=700.0, confidence=confidence),
                WordTiming(word="sau", start_ms=710.0, end_ms=850.0, confidence=confidence),
                WordTiming(word="pachaas", start_ms=860.0, end_ms=1050.0, confidence=confidence),
                WordTiming(word="udhaar", start_ms=1060.0, end_ms=1200.0, confidence=confidence),
            )
        else:
            self.words = words

        # State tracking for lifecycle assertions (no fragile sleep/timing required)
        self.initialize_calls: int = 0
        self.warmup_calls: int = 0
        self.shutdown_calls: int = 0
        self.transcribe_calls: int = 0
        self.last_initial_prompt: str | None = None
        self.initial_prompts: list[str | None] = []
        self.is_initialized: bool = False
        self.is_warmed_up: bool = False
        self.is_shutdown: bool = False

    async def initialize(self) -> None:
        self.initialize_calls += 1
        self.is_initialized = True
        self.is_shutdown = False

    async def warmup(self) -> None:
        self.warmup_calls += 1
        self.is_warmed_up = True

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        initial_prompt: str | None = None,
    ) -> ASRResult:
        self.transcribe_calls += 1
        self.last_initial_prompt = initial_prompt
        self.initial_prompts.append(initial_prompt)
        # Yield control to event loop to prove non-blocking async execution
        await asyncio.sleep(0)

        # Empty audio returns empty result with confidence=None
        if not audio_bytes:
            return ASRResult(
                text="",
                language=language or self.language,
                confidence=None,
                duration_ms=0.0,
                words=(),
            )

        return ASRResult(
            text=self.canned_text,
            language=language or self.language,
            confidence=self.confidence,
            duration_ms=self.duration_ms,
            words=self.words,
        )

    async def stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[ASRPartialResult]:
        words = self.canned_text.split()
        collected = []
        idx = 0
        async for _chunk in audio_stream:
            if idx < len(words):
                collected.append(words[idx])
                idx += 1
                yield ASRPartialResult(text=" ".join(collected), is_final=False)
            await asyncio.sleep(0)

        yield ASRPartialResult(text=self.canned_text, is_final=True)

    async def shutdown(self) -> None:
        self.shutdown_calls += 1
        self.is_initialized = False
        self.is_shutdown = True
