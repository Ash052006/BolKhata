"""
VAD (Voice Activity Detection) interface and mock implementation.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VADDecision:
    """Decision for an individual audio frame."""

    is_speech: bool
    confidence: float


class VADProvider(ABC):
    """
    Abstract interface for Voice Activity Detection.

    If unconfigured in the pipeline, all audio captured between
    push-to-talk boundaries is treated as speech without silence trimming.
    """

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def process_frame(self, pcm_frame_30ms: bytes) -> VADDecision:
        """Process a 30ms 16kHz mono 16-bit PCM frame (960 bytes)."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass


class MockVADProvider(VADProvider):
    """Deterministic mock VAD for unit testing."""

    def __init__(self, default_is_speech: bool = True, default_confidence: float = 0.9) -> None:
        self.default_is_speech = default_is_speech
        self.default_confidence = default_confidence
        self.is_initialized: bool = False
        self.is_shutdown: bool = False

    async def initialize(self) -> None:
        self.is_initialized = True
        self.is_shutdown = False

    async def process_frame(self, pcm_frame_30ms: bytes) -> VADDecision:
        await asyncio.sleep(0)
        return VADDecision(is_speech=self.default_is_speech, confidence=self.default_confidence)

    async def shutdown(self) -> None:
        self.is_initialized = False
        self.is_shutdown = True
