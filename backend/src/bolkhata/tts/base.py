"""
TTS (Text-to-Speech) provider interfaces and result contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class TTSResult:
    """
    Complete synthesized speech result.

    Audio format contract:
      Headerless 16,000 Hz, 16-bit Signed Little-Endian Mono Linear PCM.
    """

    audio_bytes: bytes
    sample_rate: int = 16000
    encoding: str = "pcm_s16le"
    duration_ms: float = 0.0


@dataclass(frozen=True)
class TTSChunk:
    """A single sequential frame of synthesized PCM audio."""

    pcm_bytes: bytes
    sequence_number: int
    is_final: bool
    sample_rate: int = 16000


class TTSProvider(ABC):
    """
    Abstract interface for Text-to-Speech engines.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize models or runtime sessions. Idempotent."""
        pass

    @abstractmethod
    async def warmup(self) -> None:
        """Warm up synthesis pipeline."""
        pass

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> TTSResult:
        """Synthesize text to complete 16kHz mono PCM audio bytes."""
        pass

    @abstractmethod
    def stream(
        self, text_stream: AsyncIterator[str], voice: str | None = None
    ) -> AsyncIterator[TTSChunk]:
        """Stream synthesized PCM audio chunks as input text tokens/sentences arrive."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Release engine resources cleanly. Idempotent."""
        pass
