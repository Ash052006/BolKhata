"""
Deterministic Mock TTS provider for offline testing and CI.
"""

from __future__ import annotations

import asyncio
import math
import struct
from collections.abc import AsyncIterator

from bolkhata.tts.base import TTSChunk, TTSProvider, TTSResult


def generate_mock_pcm(duration_ms: float = 200.0, freq_hz: float = 440.0) -> bytes:
    """
    Generate deterministic, valid 16kHz mono 16-bit linear PCM samples.

    Does not produce speech; generates a pure sine wave in raw little-endian format.
    Each sample is a signed 16-bit integer [-32768, 32767].
    """
    sample_rate = 16000
    num_samples = int((duration_ms / 1000.0) * sample_rate)
    amplitude = 8000  # Conservative amplitude to avoid clipping
    pcm_chunks = bytearray(num_samples * 2)

    for i in range(num_samples):
        # Deterministic sine calculation
        val = int(amplitude * math.sin(2.0 * math.pi * freq_hz * (i / sample_rate)))
        struct.pack_into("<h", pcm_chunks, i * 2, val)

    return bytes(pcm_chunks)


class MockTTSProvider(TTSProvider):
    """
    Deterministic mock speech synthesis provider.

    Returns valid, well-formed 16-bit linear PCM audio samples.
    Does not attempt natural language synthesis.
    """

    def __init__(self, chunk_duration_ms: float = 100.0, num_chunks: int = 3) -> None:
        self.chunk_duration_ms = chunk_duration_ms
        self.num_chunks = num_chunks
        self.initialize_calls: int = 0
        self.warmup_calls: int = 0
        self.shutdown_calls: int = 0
        self.synthesize_calls: int = 0
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

    async def synthesize(self, text: str, voice: str | None = None) -> TTSResult:
        self.synthesize_calls += 1
        await asyncio.sleep(0)
        pcm_bytes = generate_mock_pcm(
            duration_ms=self.chunk_duration_ms * self.num_chunks,
            freq_hz=440.0,
        )
        return TTSResult(
            audio_bytes=pcm_bytes,
            sample_rate=16000,
            encoding="pcm_s16le",
            duration_ms=self.chunk_duration_ms * self.num_chunks,
        )

    async def stream(
        self, text_stream: AsyncIterator[str], voice: str | None = None
    ) -> AsyncIterator[TTSChunk]:
        # Consume any incoming text tokens
        async for _token in text_stream:
            await asyncio.sleep(0)

        chunk_pcm = generate_mock_pcm(duration_ms=self.chunk_duration_ms, freq_hz=440.0)
        for seq in range(self.num_chunks):
            is_final = seq == (self.num_chunks - 1)
            yield TTSChunk(
                pcm_bytes=chunk_pcm,
                sequence_number=seq,
                is_final=is_final,
                sample_rate=16000,
            )
            await asyncio.sleep(0)

    async def shutdown(self) -> None:
        self.shutdown_calls += 1
        self.is_initialized = False
        self.is_shutdown = True
