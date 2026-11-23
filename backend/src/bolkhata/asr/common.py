"""
Common audio processing utilities and constants for BolKhata ASR providers.

Standard audio format contract:
- Sample rate: 16,000 Hz
- Channels: 1 (mono)
- Sample format: signed 16-bit little-endian PCM
- Headerless raw PCM bytes
"""

from __future__ import annotations

import array
import sys

# Fixed audio contract constants
SAMPLE_RATE_HZ: int = 16000
CHANNELS: int = 1
BYTES_PER_SAMPLE: int = 2
BYTES_PER_SECOND: int = SAMPLE_RATE_HZ * CHANNELS * BYTES_PER_SAMPLE


class AudioFormatError(ValueError):
    """Raised when audio bytes or parameters violate the expected format contract."""


def pcm_to_float32(audio_bytes: bytes) -> array.array[float]:
    """
    Convert raw 16kHz mono signed 16-bit little-endian PCM bytes to float32 samples.

    Normalized to the range [-1.0, 1.0].
    -32768 maps exactly to -1.0.
    32767 maps to 32767 / 32768.0 (~0.99997).
    Empty bytes input returns an empty float32 array.
    Odd-length bytes input raises AudioFormatError.

    Returns:
        array.array of type 'f' (32-bit floating point).
    """
    if not audio_bytes:
        return array.array("f")

    if len(audio_bytes) % BYTES_PER_SAMPLE != 0:
        raise AudioFormatError(
            f"Audio buffer byte count must be a multiple of {BYTES_PER_SAMPLE} bytes, "
            f"got {len(audio_bytes)} bytes."
        )

    raw_samples = array.array("h")
    raw_samples.frombytes(audio_bytes)

    if sys.byteorder != "little":
        raw_samples.byteswap()

    return array.array("f", (s / 32768.0 for s in raw_samples))


def compute_duration_ms(byte_count: int, sample_rate: int = SAMPLE_RATE_HZ) -> float:
    """
    Compute duration in milliseconds for a mono 16-bit PCM byte count.

    Args:
        byte_count: Number of raw PCM bytes (must be non-negative and 2-byte aligned).
        sample_rate: Audio sample rate in Hz (must be positive).

    Returns:
        Duration in milliseconds.
    """
    if byte_count < 0:
        raise AudioFormatError(f"byte_count must be non-negative, got {byte_count}.")

    if sample_rate <= 0:
        raise AudioFormatError(f"sample_rate must be positive, got {sample_rate}.")

    if byte_count % BYTES_PER_SAMPLE != 0:
        raise AudioFormatError(
            f"byte_count must be aligned to {BYTES_PER_SAMPLE}-byte sample size, "
            f"got {byte_count} bytes."
        )

    if byte_count == 0:
        return 0.0

    bytes_per_second = sample_rate * CHANNELS * BYTES_PER_SAMPLE
    return (byte_count / bytes_per_second) * 1000.0
