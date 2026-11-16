"""
ASR (Automatic Speech Recognition) provider interfaces and result contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class WordTiming:
    """Word-level timing information."""

    word: str
    start_ms: float
    end_ms: float
    confidence: float = 1.0


@dataclass(frozen=True)
class ASRResult:
    """
    Immutable result of speech transcription.

    Words is an immutable tuple of WordTiming objects.
    """

    text: str
    language: str
    confidence: float
    duration_ms: float
    words: tuple[WordTiming, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.words, tuple):
            object.__setattr__(self, "words", tuple(self.words))


@dataclass(frozen=True)
class ASRPartialResult:
    """Interim partial result during streaming transcription."""

    text: str
    is_final: bool


class ASRProvider(ABC):
    """
    Abstract interface for Automatic Speech Recognition engines.

    Audio format contract:
      Headerless 16,000 Hz, 16-bit Signed Little-Endian Mono Linear PCM.

    Streaming and cancellation semantics:
      * Sequence-to-sequence Whisper engines (Faster-Whisper, MLX-Whisper)
        operate on chunked sliding windows rather than native causal streaming.
      * transcribe() is the primary push-to-talk method, operating on the
        complete buffer after speech ends.
      * stream() accepts an AsyncIterator of raw audio chunks and yields
        interim partial transcripts.
      * Cancellation: Cancelling the awaiting coroutine immediately halts
        processing. Implementations must catch asyncio.CancelledError, release
        any active compute resources, and re-raise.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize models or resources. Must be idempotent."""
        pass

    @abstractmethod
    async def warmup(self) -> None:
        """Prime execution graphs with a minimal dummy inference."""
        pass

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> ASRResult:
        """Transcribe a complete 16kHz mono PCM buffer."""
        pass

    @abstractmethod
    def stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[ASRPartialResult]:
        """Stream transcription over incoming audio chunks."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Release GPU/CPU resources cleanly. Must be idempotent."""
        pass
