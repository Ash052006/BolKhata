"""
Unit tests for shared audio utilities and PCM conversion.
"""

from __future__ import annotations

import array
import struct
import sys

import pytest

from bolkhata.asr.common import (
    BYTES_PER_SAMPLE,
    CHANNELS,
    SAMPLE_RATE_HZ,
    AudioFormatError,
    compute_duration_ms,
    pcm_to_float32,
)


class TestAudioContractConstants:
    def test_constants_match_contract(self) -> None:
        assert SAMPLE_RATE_HZ == 16000
        assert CHANNELS == 1
        assert BYTES_PER_SAMPLE == 2


class TestPCMToFloat32:
    def test_positive_and_negative_samples(self) -> None:
        # Pack known signed 16-bit values: [16384, -16384, 8192, -8192]
        raw = struct.pack("<4h", 16384, -16384, 8192, -8192)
        result = pcm_to_float32(raw)

        assert isinstance(result, array.array)
        assert result.typecode == "f"
        assert len(result) == 4
        assert result[0] == pytest.approx(0.5, abs=1e-6)
        assert result[1] == pytest.approx(-0.5, abs=1e-6)
        assert result[2] == pytest.approx(0.25, abs=1e-6)
        assert result[3] == pytest.approx(-0.25, abs=1e-6)

    def test_little_endian_interpretation(self) -> None:
        # In little-endian:
        # b"\x01\x00" -> 1
        # b"\x00\x01" -> 256
        raw = b"\x01\x00\x00\x01"
        result = pcm_to_float32(raw)

        assert len(result) == 2
        assert result[0] == pytest.approx(1.0 / 32768.0, abs=1e-7)
        assert result[1] == pytest.approx(256.0 / 32768.0, abs=1e-7)

    def test_normalization_boundaries(self) -> None:
        # Boundaries: -32768, 0, 32767
        raw = struct.pack("<3h", -32768, 0, 32767)
        result = pcm_to_float32(raw)

        assert len(result) == 3
        # -32768 / 32768.0 == -1.0 exactly
        assert result[0] == -1.0
        # 0 / 32768.0 == 0.0 exactly
        assert result[1] == 0.0
        # 32767 / 32768.0 ~= 0.99996948...
        assert result[2] == pytest.approx(32767.0 / 32768.0, abs=1e-6)
        assert -1.0 <= result[2] <= 1.0

    def test_empty_input(self) -> None:
        result = pcm_to_float32(b"")
        assert isinstance(result, array.array)
        assert result.typecode == "f"
        assert len(result) == 0

    def test_odd_length_input_rejection(self) -> None:
        # 1 byte (odd)
        with pytest.raises(AudioFormatError, match="multiple of 2 bytes"):
            pcm_to_float32(b"\x00")

        # 3 bytes (odd)
        with pytest.raises(AudioFormatError, match="multiple of 2 bytes"):
            pcm_to_float32(b"\x00\x00\x01")

        # 5 bytes (odd)
        with pytest.raises(AudioFormatError, match="multiple of 2 bytes"):
            pcm_to_float32(b"\x00\x00\x01\x02\x03")

    def test_caller_input_bytes_not_modified(self) -> None:
        orig = b"\x00\x10\x00\x20"
        immutable_copy = bytes(orig)
        _ = pcm_to_float32(orig)
        assert orig == immutable_copy


class TestComputeDurationMs:
    def test_duration_half_second_and_full_second(self) -> None:
        # 16,000 Hz * 1 channel * 2 bytes/sample = 32,000 bytes/sec
        # 0.5s = 16,000 bytes -> 500 ms
        assert compute_duration_ms(16000) == pytest.approx(500.0)

        # 1.0s = 32,000 bytes -> 1000 ms
        assert compute_duration_ms(32000) == pytest.approx(1000.0)

        # Zero bytes -> 0.0 ms
        assert compute_duration_ms(0) == 0.0

    def test_custom_positive_sample_rate(self) -> None:
        # 8,000 Hz * 1 channel * 2 bytes/sample = 16,000 bytes/sec
        # 16,000 bytes at 8,000 Hz = 1000 ms
        assert compute_duration_ms(16000, sample_rate=8000) == pytest.approx(1000.0)

    def test_invalid_negative_byte_count(self) -> None:
        with pytest.raises(AudioFormatError, match="byte_count must be non-negative"):
            compute_duration_ms(-1)

        with pytest.raises(AudioFormatError, match="byte_count must be non-negative"):
            compute_duration_ms(-32000)

    def test_invalid_sample_rate(self) -> None:
        with pytest.raises(AudioFormatError, match="sample_rate must be positive"):
            compute_duration_ms(32000, sample_rate=0)

        with pytest.raises(AudioFormatError, match="sample_rate must be positive"):
            compute_duration_ms(32000, sample_rate=-16000)

    def test_misaligned_byte_count_rejected(self) -> None:
        with pytest.raises(AudioFormatError, match="aligned to 2-byte sample size"):
            compute_duration_ms(1)

        with pytest.raises(AudioFormatError, match="aligned to 2-byte sample size"):
            compute_duration_ms(32001)


class TestIndependenceFromOptionalEngines:
    def test_common_utility_imports_without_numpy_or_engines(self) -> None:
        # Verify that bolkhata.asr.common only depends on stdlib
        import bolkhata.asr.common as common_mod

        # Inspect non-stdlib modules that might have been accidentally imported
        assert "array" in sys.modules
        # Verify neither faster_whisper nor mlx_whisper were required by common
        assert not hasattr(common_mod, "np")
        assert not hasattr(common_mod, "numpy")
        assert not hasattr(common_mod, "faster_whisper")
        assert not hasattr(common_mod, "mlx_whisper")
