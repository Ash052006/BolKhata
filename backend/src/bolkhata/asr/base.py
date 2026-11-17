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
    confidence: float | None = None


@dataclass(frozen=True)
class ASRResult:
    """
    Immutable result of speech transcription.

    Words is an immutable tuple of WordTiming objects.
    Confidence is an optional float in [0.0, 1.0] when supplied by a documented
    runtime probability field; None indicates confidence is unavailable.
    """

    text: str
    language: str
    confidence: float | None
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
      * Sequence-to-sequence Whisper engines (such as MLX-Whisper on Apple Silicon)
        operate on chunked sliding windows rather than native causal streaming.
      * transcribe() is the primary push-to-talk method, operating on the
        complete buffer after speech ends.
      * stream() accepts an AsyncIterator of raw audio chunks and yields
        interim partial transcripts.
      * Cancellation: Cancelling the awaiting coroutine stops the caller
        from awaiting the result, but native synchronous inference already
        executing in a worker thread may continue until completion. Concrete
        providers must use bounded worker execution and cooperative
        cancellation where supported. If hard cancellation is required for a
        future model runtime, a dedicated process boundary must be used
        rather than expecting asyncio cancellation to abort OS threads.
        Providers must release any resources they can safely release and
        re-raise asyncio.CancelledError.
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
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        initial_prompt: str | None = None,
    ) -> ASRResult:
        """
        Transcribe a complete 16kHz mono PCM buffer.

        Args:
            audio_bytes: Raw 16kHz mono signed 16-bit little-endian PCM bytes.
            language: Optional language code (e.g. 'hi', 'en'). If None, the engine
                will perform automatic language detection where supported.
            initial_prompt: Optional contextual vocabulary prompt to bias transcription
                (e.g. kirana items, customer names). Does not alter audio semantics.

        Returns:
            ASRResult containing transcription text, language, optional confidence,
            duration in milliseconds, and word timings.
        """
        pass

    @abstractmethod
    def stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[ASRPartialResult]:
        """Stream transcription over incoming audio chunks."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Release GPU/CPU resources cleanly. Must be idempotent."""
        pass
