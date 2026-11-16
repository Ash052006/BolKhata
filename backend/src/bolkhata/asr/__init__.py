"""
ASR package contracts and mock implementation.
"""

from __future__ import annotations

from bolkhata.asr.base import (
    ASRPartialResult,
    ASRProvider,
    ASRResult,
    WordTiming,
)
from bolkhata.asr.mock import MockASRProvider
from bolkhata.asr.vad import MockVADProvider, VADDecision, VADProvider

__all__ = [
    "ASRPartialResult",
    "ASRProvider",
    "ASRResult",
    "MockASRProvider",
    "MockVADProvider",
    "VADDecision",
    "VADProvider",
    "WordTiming",
]
