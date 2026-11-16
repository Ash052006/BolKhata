"""
TTS package contracts and mock implementation.
"""

from __future__ import annotations

from bolkhata.tts.base import TTSChunk, TTSProvider, TTSResult
from bolkhata.tts.mock import MockTTSProvider, generate_mock_pcm

__all__ = [
    "MockTTSProvider",
    "TTSChunk",
    "TTSProvider",
    "TTSResult",
    "generate_mock_pcm",
]
