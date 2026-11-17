"""
Unit tests for ASR configuration settings and validation rules.
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
        assert s.asr_faster_whisper_model_id == "Systran/faster-whisper-small"
        assert (
            s.asr_faster_whisper_model_revision
            == "536b0662742c02347bc0e980a01041f333bce120"  # pragma: allowlist secret
        )
        assert s.asr_mlx_whisper_model_id == "mlx-community/whisper-small-mlx"
        assert (
            s.asr_mlx_whisper_model_revision
            == "45f3915923c7a79a5a5b5a7d909d39aeb0e5630e"  # pragma: allowlist secret
        )
        assert s.asr_device == "auto"
        assert s.asr_compute_type == "auto"
        assert s.asr_model_dir is None
        assert s.asr_offline_mode is False
        assert s.asr_max_duration_seconds == 30.0

    def test_valid_overrides(self) -> None:
        s = Settings(
            asr_faster_whisper_model_id="Systran/faster-whisper-tiny",
            asr_faster_whisper_model_revision="1111111111111111111111111111111111111111",
            asr_mlx_whisper_model_id="mlx-community/whisper-tiny-mlx",
            asr_mlx_whisper_model_revision=None,
            asr_device="cuda",
            asr_compute_type="int8_float16",
            asr_model_dir="/opt/models/whisper",
            asr_offline_mode=True,
            asr_max_duration_seconds=45.5,
            asr_max_concurrency=4,
        )
        assert s.asr_faster_whisper_model_id == "Systran/faster-whisper-tiny"
        assert s.asr_faster_whisper_model_revision == "1111111111111111111111111111111111111111"
        assert s.asr_mlx_whisper_model_id == "mlx-community/whisper-tiny-mlx"
        assert s.asr_mlx_whisper_model_revision is None
        assert s.asr_device == "cuda"
        assert s.asr_compute_type == "int8_float16"
        assert s.asr_model_dir == "/opt/models/whisper"
        assert s.asr_offline_mode is True
        assert s.asr_max_duration_seconds == 45.5
        assert s.asr_max_concurrency == 4

    @pytest.mark.parametrize("device", ["auto", "cpu", "cuda", " AUTO ", "CPU"])
    def test_valid_device_values(self, device: str) -> None:
        s = Settings(asr_device=device)
        assert s.asr_device == device.strip().lower()

    @pytest.mark.parametrize(
        "compute_type", ["auto", "int8", "float16", "int8_float16", " FLOAT16 "]
    )
    def test_valid_compute_type_values(self, compute_type: str) -> None:
        s = Settings(asr_compute_type=compute_type)
        assert s.asr_compute_type == compute_type.strip().lower()


class TestASRSettingsValidationErrors:
    @pytest.mark.parametrize("invalid_device", ["gpu", "tpu", "directml", "rocm", ""])
    def test_invalid_device_rejected(self, invalid_device: str) -> None:
        with pytest.raises(ValueError, match="ASR_DEVICE must be one of"):
            Settings(asr_device=invalid_device)

    @pytest.mark.parametrize("invalid_compute", ["fp32", "bfloat16", "int4", "invalid"])
    def test_invalid_compute_type_rejected(self, invalid_compute: str) -> None:
        with pytest.raises(ValueError, match="ASR_COMPUTE_TYPE must be one of"):
            Settings(asr_compute_type=invalid_compute)

    @pytest.mark.parametrize(
        "invalid_rev",
        [
            "main",
            "536b066",  # short hash rejected — must be full 40-char
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",  # non-hex
            "536b0662742c02347bc0e980a01041f333bce12",  # 39 chars # pragma: allowlist secret
            "536b0662742c02347bc0e980a01041f333bce1200",  # 41 chars # pragma: allowlist secret
        ],
    )
    def test_invalid_revision_hash_rejected(self, invalid_rev: str) -> None:
        with pytest.raises(ValueError, match="Model revision must be a full 40-character hex"):
            Settings(asr_faster_whisper_model_revision=invalid_rev)

        with pytest.raises(ValueError, match="Model revision must be a full 40-character hex"):
            Settings(asr_mlx_whisper_model_revision=invalid_rev)

    def test_empty_model_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="ASR_FASTER_WHISPER_MODEL_ID cannot be empty"):
            Settings(asr_faster_whisper_model_id="   ")

        with pytest.raises(ValueError, match="ASR_MLX_WHISPER_MODEL_ID cannot be empty"):
            Settings(asr_mlx_whisper_model_id="")

    @pytest.mark.parametrize(
        "invalid_duration", [0.0, -1.0, -0.001, float("inf"), float("-inf"), float("nan")]
    )
    def test_invalid_max_duration_rejected(self, invalid_duration: float) -> None:
        with pytest.raises(ValueError, match="ASR_MAX_DURATION_SECONDS must be a positive finite"):
            Settings(asr_max_duration_seconds=invalid_duration)


class TestASRRuntimeImportIsolation:
    def test_package_imports_without_speech_runtimes(self) -> None:
        """
        Verify that importing core bolkhata modules never attempts to import
        optional heavy machine learning engines (faster_whisper, mlx_whisper).
        """
        import bolkhata.asr.base
        import bolkhata.asr.common
        import bolkhata.asr.mock
        import bolkhata.common.registry
        import bolkhata.config.settings

        assert bolkhata.config.settings.settings.asr_provider == "mock"
        # Confirm heavy optional libraries are not in sys.modules
        for forbidden in ("faster_whisper", "mlx_whisper", "ctranslate2", "mlx", "torch"):
            assert (
                forbidden not in sys.modules
            ), f"{forbidden} was imported during base package load!"
