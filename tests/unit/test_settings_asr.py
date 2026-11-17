"""
Unit tests for Apple Silicon MLX ASR configuration settings and validation rules.
"""

from __future__ import annotations

import sys

import pytest

from bolkhata.config.settings import Settings


class TestASRSettingsDefaultsAndOverrides:
    def test_default_asr_settings(self) -> None:
        s = Settings()
        assert s.asr_provider == "mock"
        assert s.asr_max_concurrency == 1
        assert s.asr_mlx_whisper_model_id == "mlx-community/whisper-small-mlx"
        assert (
            s.asr_mlx_whisper_model_revision
            == "45f3915923c7a79a5a5b5a7d909d39aeb0e5630e"  # pragma: allowlist secret
        )
        assert s.asr_model_dir is None
        assert s.asr_offline_mode is False
        assert s.asr_max_duration_seconds == 30.0

        # Verify no Faster-Whisper or CUDA/device settings remain
        assert not hasattr(s, "asr_faster_whisper_model_id")
        assert not hasattr(s, "asr_faster_whisper_model_revision")
        assert not hasattr(s, "asr_device")
        assert not hasattr(s, "asr_compute_type")

    def test_valid_overrides(self) -> None:
        s = Settings(
            asr_provider="mlx_whisper",
            asr_mlx_whisper_model_id="mlx-community/whisper-tiny-mlx",
            asr_mlx_whisper_model_revision="1111111111111111111111111111111111111111",  # pragma: allowlist secret
            asr_model_dir="/opt/models/whisper",
            asr_offline_mode=True,
            asr_max_duration_seconds=45.5,
            asr_max_concurrency=4,
        )
        assert s.asr_provider == "mlx_whisper"
        assert s.asr_mlx_whisper_model_id == "mlx-community/whisper-tiny-mlx"
        assert s.asr_mlx_whisper_model_revision == "1111111111111111111111111111111111111111"
        assert s.asr_model_dir == "/opt/models/whisper"
        assert s.asr_offline_mode is True
        assert s.asr_max_duration_seconds == 45.5
        assert s.asr_max_concurrency == 4

    def test_none_revision_and_blank_dir_normalization(self) -> None:
        s = Settings(
            asr_mlx_whisper_model_revision=None,
            asr_model_dir="   ",
        )
        assert s.asr_mlx_whisper_model_revision is None
        assert s.asr_model_dir is None

    @pytest.mark.parametrize(
        ("provider_input", "expected"),
        [
            ("mock", "mock"),
            ("mlx_whisper", "mlx_whisper"),
            (" MLX_WHISPER ", "mlx_whisper"),
        ],
    )
    def test_valid_asr_provider_values(self, provider_input: str, expected: str) -> None:
        s = Settings(asr_provider=provider_input)
        assert s.asr_provider == expected


class TestASRSettingsValidationErrors:
    @pytest.mark.parametrize(
        "invalid_provider",
        ["faster_whisper", "cuda", "whisper", "ctranslate2", ""],
    )
    def test_invalid_asr_provider_rejected(self, invalid_provider: str) -> None:
        with pytest.raises(ValueError, match="ASR_PROVIDER must be one of"):
            Settings(asr_provider=invalid_provider)

    @pytest.mark.parametrize(
        "invalid_rev",
        [
            "main",
            "45f3915",  # short hash rejected — must be full 40-char
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",  # non-hex
            "45f3915923c7a79a5a5b5a7d909d39aeb0e5630",  # 39 chars # pragma: allowlist secret
            "45f3915923c7a79a5a5b5a7d909d39aeb0e5630e0",  # 41 chars # pragma: allowlist secret
        ],
    )
    def test_invalid_revision_hash_rejected(self, invalid_rev: str) -> None:
        with pytest.raises(ValueError, match="Model revision must be a full 40-character hex"):
            Settings(asr_mlx_whisper_model_revision=invalid_rev)

    @pytest.mark.parametrize("blank_id", ["", "   "])
    def test_empty_mlx_model_id_rejected(self, blank_id: str) -> None:
        with pytest.raises(ValueError, match="ASR_MLX_WHISPER_MODEL_ID cannot be empty"):
            Settings(asr_mlx_whisper_model_id=blank_id)

    @pytest.mark.parametrize(
        "invalid_duration", [0.0, -1.0, -0.001, float("inf"), float("-inf"), float("nan")]
    )
    def test_invalid_max_duration_rejected(self, invalid_duration: float) -> None:
        with pytest.raises(ValueError, match="ASR_MAX_DURATION_SECONDS must be a positive finite"):
            Settings(asr_max_duration_seconds=invalid_duration)

    @pytest.mark.parametrize("invalid_concurrency", [0, -1, -50])
    def test_invalid_concurrency_rejected(self, invalid_concurrency: int) -> None:
        with pytest.raises(ValueError, match="ASR_MAX_CONCURRENCY must be at least 1"):
            Settings(asr_max_concurrency=invalid_concurrency)


class TestASRRuntimeImportIsolation:
    def test_package_imports_without_speech_runtimes(self) -> None:
        """
        Verify that importing core bolkhata modules never attempts to import
        optional heavy machine learning engines (mlx_whisper, mlx, ctranslate2).
        """
        import bolkhata.asr.base
        import bolkhata.asr.common
        import bolkhata.asr.mock
        import bolkhata.common.registry
        import bolkhata.config.settings

        assert bolkhata.config.settings.settings.asr_provider == "mock"
        # Confirm heavy optional libraries are not in sys.modules
        for forbidden in ("mlx_whisper", "mlx", "faster_whisper", "ctranslate2", "torch"):
            assert (
                forbidden not in sys.modules
            ), f"{forbidden} was imported during base package load!"

    def test_cuda_and_faster_whisper_not_in_settings_schema(self) -> None:
        """
        Confirm that Settings schema contains no deprecated Faster-Whisper
        or CUDA device/compute settings.
        """
        fields = Settings.model_fields
        assert "asr_faster_whisper_model_id" not in fields
        assert "asr_faster_whisper_model_revision" not in fields
        assert "asr_device" not in fields
        assert "asr_compute_type" not in fields
        assert "asr_mlx_whisper_model_id" in fields
        assert "asr_mlx_whisper_model_revision" in fields
        assert "asr_max_concurrency" in fields
        assert "asr_max_duration_seconds" in fields
        assert "asr_offline_mode" in fields
        assert "asr_model_dir" in fields
