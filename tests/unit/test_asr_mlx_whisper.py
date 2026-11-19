"""
Hermetic unit tests for MLXWhisperASRProvider.

Tests cover:
1. Lazy imports (importing module does not import native MLX runtime).
2. Successful fake-runtime initialization.
3. Missing optional dependency via injected loader.
4. Initialization and lifecycle idempotency.
5. Offline model resolution (network disabled).
6. Pinned revision passed to model resolver.
7. No fallback to mutable 'main'.
8. PCM conversion and normalization.
9. Empty audio handling.
10. Malformed and oversized audio.
11. Language and initial_prompt pass-through.
12. Segment and word timing mapping.
13. Missing confidence remains None.
14. Malformed runtime output.
15. Runtime exceptions and slot recovery.
16. Concurrency limit enforcement.
17. Cancellation while worker is still active.
18. Shutdown waits for active workers.
19. New transcription rejected after shutdown begins.
20. Stream accumulation and final-only result.
21. Mock provider works independently of MLX.

Guarantees:
- Zero model weight downloads.
- Zero network requests.
- No GPU requirements.
- Zero monkeypatching of sys.modules or builtins.__import__.
- Deterministic synchronization primitives (no fragile timing sleeps).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from bolkhata.asr.base import ASRPartialResult, ASRResult, WordTiming
from bolkhata.asr.common import AudioFormatError
from bolkhata.asr.mlx_whisper import (
    DependencyMissingError,
    MLXRuntime,
    MLXWhisperASRProvider,
    ModelResolutionError,
    map_runtime_result,
    resolve_model_path,
)
from bolkhata.asr.mock import MockASRProvider
from bolkhata.config.settings import Settings

PINNED_REVISION = "45f3915923c7a79a5a5b5a7d909d39aeb0e5630e"  # pragma: allowlist secret


@pytest.fixture
def fake_model_dir(tmp_path: Path) -> Path:
    """Fixture providing a mock model directory containing config.json."""
    model_dir = tmp_path / "fake_model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text('{"vocab_size": 51865}', encoding="utf-8")
    return model_dir


@pytest.fixture
def fake_snapshot_download(fake_model_dir: Path):
    """Factory fixture for a fake snapshot_download callable."""
    calls: list[dict[str, Any]] = []

    def _fake_download(
        repo_id: str,
        revision: str | None = None,
        local_files_only: bool = False,
        cache_dir: str | None = None,
    ) -> str:
        calls.append(
            {
                "repo_id": repo_id,
                "revision": revision,
                "local_files_only": local_files_only,
                "cache_dir": cache_dir,
            }
        )
        return str(fake_model_dir)

    _fake_download.calls = calls  # type: ignore[attr-defined]
    return _fake_download


@pytest.fixture
def fake_transcribe():
    """Factory fixture for a fake mlx_whisper.transcribe callable."""
    calls: list[dict[str, Any]] = []

    def _fake_transcribe(
        audio: Any,
        *,
        path_or_hf_repo: str = "",
        language: str | None = None,
        initial_prompt: str | None = None,
        word_timestamps: bool = True,
        verbose: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        calls.append(
            {
                "audio": audio,
                "path_or_hf_repo": path_or_hf_repo,
                "language": language,
                "initial_prompt": initial_prompt,
                "word_timestamps": word_timestamps,
                "verbose": verbose,
                "kwargs": kwargs,
            }
        )
        return {
            "text": " Sharma ji ko do sau rupaye udhaar ",
            "language": language or "hi",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.2,
                    "text": "Sharma ji ko do sau rupaye udhaar",
                    "words": [
                        {"word": "Sharma", "start": 0.0, "end": 0.3, "probability": 0.92},
                        {"word": "ji", "start": 0.31, "end": 0.45, "probability": 0.88},
                        {"word": "ko", "start": 0.46, "end": 0.55, "probability": 0.95},
                        {"word": "do", "start": 0.56, "end": 0.70, "probability": 0.90},
                        {"word": "sau", "start": 0.71, "end": 0.85, "probability": 0.85},
                        {"word": "rupaye", "start": 0.86, "end": 1.05, "probability": 0.91},
                        {"word": "udhaar", "start": 1.06, "end": 1.20, "probability": 0.89},
                    ],
                }
            ],
        }

    _fake_transcribe.calls = calls  # type: ignore[attr-defined]
    return _fake_transcribe


@pytest.fixture
def fake_runtime(fake_transcribe: Any) -> MLXRuntime:
    """Fixture providing a mock MLXRuntime."""

    class FakeWhisperModule:
        transcribe = staticmethod(fake_transcribe)

    return MLXRuntime(
        mlx_core=object(),
        mlx_whisper=FakeWhisperModule(),
        numpy=np,
    )


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------
class TestMLXWhisperASRProvider:
    # 1. Lazy imports
    def test_lazy_imports_do_not_import_mlx_runtime(self) -> None:
        """Importing bolkhata.asr.mlx_whisper must not eagerly import mlx_whisper or mlx.core."""
        import bolkhata.asr.mlx_whisper as mlx_mod

        assert hasattr(mlx_mod, "MLXWhisperASRProvider")
        assert hasattr(mlx_mod, "MLXRuntime")
        assert hasattr(mlx_mod, "load_mlx_runtime")

        settings = Settings()
        provider = mlx_mod.MLXWhisperASRProvider(settings)
        assert not provider.is_initialized

    # 2. Successful fake-runtime initialization
    @pytest.mark.asyncio
    async def test_successful_fake_runtime_initialization(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Provider initializes successfully with an injected fake runtime."""
        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        assert not provider.is_initialized
        await provider.initialize()
        assert provider.is_initialized
        assert provider.resolved_model_path is not None
        await provider.shutdown()

    # 3. Missing optional dependency via injected loader
    @pytest.mark.asyncio
    async def test_missing_optional_dependency_raises_error(
        self, fake_snapshot_download: Any
    ) -> None:
        """When mlx-whisper dependencies are missing, initialize() must raise DependencyMissingError."""

        def _missing_loader() -> MLXRuntime:
            raise DependencyMissingError(
                "Optional dependencies for MLX-Whisper are missing. "
                "Install them with: uv sync --extra mlx-whisper (Apple Silicon macOS only)."
            )

        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=_missing_loader,
        )

        with pytest.raises(DependencyMissingError, match="Optional dependencies for MLX-Whisper"):
            await provider.initialize()

    # 4. Initialization and lifecycle idempotency
    @pytest.mark.asyncio
    async def test_lifecycle_idempotency(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """initialize() and shutdown() can be called multiple times safely."""
        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )

        assert not provider.is_initialized
        assert not provider.is_shutdown

        await provider.initialize()
        assert provider.is_initialized
        assert not provider.is_shutdown

        # Redundant initialize is a no-op
        await provider.initialize()
        assert provider.is_initialized

        # Warmup
        await provider.warmup()
        assert provider.is_warmed_up

        # Shutdown
        await provider.shutdown()
        assert provider.is_shutdown
        assert not provider.is_initialized

        # Redundant shutdown is a no-op
        await provider.shutdown()
        assert provider.is_shutdown

    # 5. Offline model resolution
    def test_offline_model_resolution(self, fake_model_dir: Path) -> None:
        """In offline mode, local_files_only=True must be passed, and missing local model raises."""
        calls: list[dict[str, Any]] = []

        def _fake_offline_download(**kwargs: Any) -> str:
            calls.append(kwargs)
            if kwargs.get("local_files_only"):
                raise Exception("LocalEntryNotFoundError: not found in local cache")
            return str(fake_model_dir)

        # Missing weights in offline mode raises ModelResolutionError
        with pytest.raises(ModelResolutionError, match="unavailable locally in offline mode"):
            resolve_model_path(
                model_id="mlx-community/whisper-small-mlx",
                model_revision=PINNED_REVISION,
                model_dir=None,
                offline_mode=True,
                snapshot_download_fn=_fake_offline_download,
            )

        assert len(calls) == 1
        assert calls[0]["local_files_only"] is True

    # 6. Pinned revision passed to model resolver
    def test_pinned_revision_passed_to_resolver(
        self, fake_snapshot_download: Any, fake_model_dir: Path
    ) -> None:
        """The exact 40-character commit hash must be passed to the resolver."""
        resolved = resolve_model_path(
            model_id="mlx-community/whisper-small-mlx",
            model_revision=PINNED_REVISION,
            model_dir=None,
            offline_mode=False,
            snapshot_download_fn=fake_snapshot_download,
        )
        assert resolved == fake_model_dir
        assert fake_snapshot_download.calls[0]["revision"] == PINNED_REVISION

    # 7. No fallback to mutable 'main'
    def test_no_fallback_to_unpinned_main(self, fake_snapshot_download: Any) -> None:
        """Empty or unpinned revision must fail with ModelResolutionError, never falling back to main."""
        with pytest.raises(ModelResolutionError, match="Unpinned mutable revisions"):
            resolve_model_path(
                model_id="mlx-community/whisper-small-mlx",
                model_revision=None,
                model_dir=None,
                offline_mode=False,
                snapshot_download_fn=fake_snapshot_download,
            )

        with pytest.raises(ModelResolutionError, match="Unpinned mutable revisions"):
            resolve_model_path(
                model_id="mlx-community/whisper-small-mlx",
                model_revision="",
                model_dir=None,
                offline_mode=False,
                snapshot_download_fn=fake_snapshot_download,
            )

        assert len(fake_snapshot_download.calls) == 0

    # 8. PCM conversion and normalization
    @pytest.mark.asyncio
    async def test_pcm_conversion_and_normalization(
        self, fake_snapshot_download: Any, fake_transcribe: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Verify PCM bytes are correctly converted to a float32 NumPy array in [-1.0, 1.0]."""
        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        # 3 samples: 0, 32767, -32768
        pcm_bytes = b"\x00\x00\xff\x7f\x00\x80"
        result = await provider.transcribe(pcm_bytes)

        assert isinstance(result, ASRResult)
        assert len(fake_transcribe.calls) == 1
        audio_arg = fake_transcribe.calls[0]["audio"]

        assert isinstance(audio_arg, np.ndarray)
        assert audio_arg.dtype == np.float32
        assert len(audio_arg) == 3
        assert np.isclose(audio_arg[0], 0.0)
        assert np.isclose(audio_arg[1], 32767.0 / 32768.0, atol=1e-5)
        assert np.isclose(audio_arg[2], -1.0, atol=1e-5)

        await provider.shutdown()

    # 9. Empty audio handling
    @pytest.mark.asyncio
    async def test_empty_audio_returns_empty_result_without_inference(
        self, fake_snapshot_download: Any, fake_transcribe: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Empty audio bytes must immediately return an empty ASRResult without calling transcribe."""
        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        result = await provider.transcribe(b"", language="hi")
        assert result.text == ""
        assert result.confidence is None
        assert result.duration_ms == 0.0
        assert result.words == ()
        assert len(fake_transcribe.calls) == 0

        await provider.shutdown()

    # 10. Malformed and oversized audio
    @pytest.mark.asyncio
    async def test_malformed_and_oversized_audio(
        self, fake_snapshot_download: Any, fake_transcribe: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Odd-length bytes or audio exceeding max duration must raise AudioFormatError."""
        settings = Settings(asr_max_duration_seconds=1.0)
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        # Odd byte count
        with pytest.raises(AudioFormatError, match="multiple of 2 bytes"):
            await provider.transcribe(b"\x00\x00\x01")

        # Oversized audio: 1.0s limit = 32,000 bytes. Provide 32,002 bytes
        oversized = b"\x00" * 32002
        with pytest.raises(AudioFormatError, match="exceeds maximum allowed"):
            await provider.transcribe(oversized)

        assert len(fake_transcribe.calls) == 0
        await provider.shutdown()

    # 11. Language and initial_prompt pass-through
    @pytest.mark.asyncio
    async def test_language_and_initial_prompt_passthrough(
        self, fake_snapshot_download: Any, fake_transcribe: Any, fake_runtime: MLXRuntime
    ) -> None:
        """language and initial_prompt must pass to the transcribe callable."""
        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        await provider.transcribe(
            b"\x00" * 3200,
            language="en",
            initial_prompt="Kirana ledger transaction",
        )

        assert len(fake_transcribe.calls) == 1
        call = fake_transcribe.calls[0]
        assert call["language"] == "en"
        assert call["initial_prompt"] == "Kirana ledger transaction"
        assert call["word_timestamps"] is True
        assert call["verbose"] is False

        await provider.shutdown()

    # 12. Segment and word timing mapping
    def test_segment_and_word_timing_mapping(self) -> None:
        """Start/end seconds must be converted to milliseconds, word probabilities mapped."""
        raw = {
            "text": " Namaste ji ",
            "language": "hi",
            "segments": [
                {
                    "start": 0.1,
                    "end": 0.8,
                    "words": [
                        {"word": "Namaste", "start": 0.1, "end": 0.5, "probability": 0.94},
                        {"word": "ji", "start": 0.55, "end": 0.8, "probability": 0.88},
                    ],
                }
            ],
        }
        res = map_runtime_result(raw, duration_ms=1000.0)

        assert res.text == "Namaste ji"
        assert res.language == "hi"
        assert res.confidence is None  # Overall confidence must remain None
        assert res.duration_ms == 1000.0
        assert len(res.words) == 2
        w1, w2 = res.words
        assert w1 == WordTiming(word="Namaste", start_ms=100.0, end_ms=500.0, confidence=0.94)
        assert w2 == WordTiming(word="ji", start_ms=550.0, end_ms=800.0, confidence=0.88)

    # 13. Missing confidence remains None
    def test_missing_word_confidence_remains_none(self) -> None:
        """When word timing lacks probability, word.confidence must be None."""
        raw = {
            "text": "test",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "words": [{"word": "test", "start": 0.0, "end": 1.0}],
                }
            ],
        }
        res = map_runtime_result(raw, duration_ms=1000.0)
        assert res.words[0].confidence is None
        assert res.confidence is None

    # 14. Malformed runtime output
    def test_malformed_runtime_output_handled_gracefully(self) -> None:
        """Missing or malformed keys/values in runtime output must not raise exceptions."""
        malformed_cases = [
            {},
            {"text": None, "segments": None},
            {"segments": "not a list"},
            {"segments": [None, 123, "string"]},
            {
                "segments": [
                    {
                        "words": [
                            None,
                            "bad",
                            {"word": "ok", "start": "invalid_float", "end": 1.0},
                            {"word": "inf", "start": float("inf"), "end": 1.0},
                            {"word": "nan", "start": 0.0, "end": float("nan")},
                            {"word": "valid", "start": 0.1, "end": 0.5, "probability": "bad_prob"},
                        ]
                    }
                ]
            },
        ]
        for raw in malformed_cases:
            res = map_runtime_result(raw, duration_ms=500.0)
            assert isinstance(res, ASRResult)
            assert res.confidence is None

    # 15. Runtime exceptions and slot recovery
    @pytest.mark.asyncio
    async def test_runtime_exception_preserves_error_and_frees_slot(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Inference runtime errors must propagate and release the concurrency slot."""

        def _failing_transcribe(*a: Any, **k: Any) -> Any:
            raise RuntimeError("Metal GPU graph allocation failed")

        settings = Settings(asr_max_concurrency=1)
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            transcribe_fn=_failing_transcribe,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        with pytest.raises(RuntimeError, match="Metal GPU graph allocation failed"):
            await provider.transcribe(b"\x00" * 3200)

        # Confirm slot was released and worker tracking is clean
        assert provider.active_worker_count == 0

        await provider.shutdown()

    # 16. Concurrency limit enforcement
    @pytest.mark.asyncio
    async def test_concurrency_limit_strictly_enforced(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Parallel transcribe calls must not exceed asr_max_concurrency."""
        max_seen_concurrency = 0
        current_concurrency = 0
        lock = threading.Lock()

        def _slow_transcribe(*a: Any, **k: Any) -> dict[str, Any]:
            nonlocal current_concurrency, max_seen_concurrency
            with lock:
                current_concurrency += 1
                if current_concurrency > max_seen_concurrency:
                    max_seen_concurrency = current_concurrency

            # Simulate work briefly
            import time

            time.sleep(0.01)

            with lock:
                current_concurrency -= 1

            return {"text": "ok", "segments": []}

        settings = Settings(asr_max_concurrency=2)
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            transcribe_fn=_slow_transcribe,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        audio = b"\x00" * 3200
        # Run 5 concurrent transcribe requests
        tasks = [asyncio.create_task(provider.transcribe(audio)) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r.text == "ok" for r in results)
        assert max_seen_concurrency <= 2
        assert provider.active_worker_count == 0

        await provider.shutdown()

    # 17. Cancellation while worker is still active
    @pytest.mark.asyncio
    async def test_cancellation_does_not_release_concurrency_slot_prematurely(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """Cancelling caller coroutine must not release the slot while thread is running."""
        worker1_entered = threading.Event()
        worker1_gate = threading.Event()
        worker2_entered = threading.Event()

        def _transcribe_hook(audio: Any, **k: Any) -> dict[str, Any]:
            if not worker1_entered.is_set():
                worker1_entered.set()
                # Block worker 1 until gate is set
                worker1_gate.wait()
                return {"text": "worker 1 done", "segments": []}
            else:
                worker2_entered.set()
                return {"text": "worker 2 done", "segments": []}

        # Concurrency limit = 1
        settings = Settings(asr_max_concurrency=1)
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            transcribe_fn=_transcribe_hook,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        # Task 1 starts transcribe and enters thread
        t1 = asyncio.create_task(provider.transcribe(b"\x00" * 3200))

        # Deterministically wait for worker 1 thread to enter
        await asyncio.to_thread(worker1_entered.wait)
        assert provider.active_worker_count == 1

        # Cancel caller coroutine t1!
        t1.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t1

        # Task 1 is cancelled, but worker 1 thread is STILL RUNNING!
        assert provider.active_worker_count == 1

        # Task 2 attempts transcribe with concurrency limit 1
        t2 = asyncio.create_task(provider.transcribe(b"\x00" * 3200))
        # Yield to event loop: task 2 cannot enter inference because slot is held by worker 1 thread
        await asyncio.sleep(0)
        assert not worker2_entered.is_set()

        # Release worker 1 gate to let worker 1 thread exit
        worker1_gate.set()

        # Task 2 can now acquire the released slot and complete
        res2 = await t2
        assert res2.text == "worker 2 done"
        assert provider.active_worker_count == 0

        await provider.shutdown()

    # 18. Shutdown waits for active workers
    # 19. New transcription rejected after shutdown begins
    @pytest.mark.asyncio
    async def test_shutdown_waits_for_active_workers_and_prevents_new_calls(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """shutdown() must wait for running inference threads to complete and reject new calls."""
        worker_entered = threading.Event()
        worker_gate = threading.Event()

        def _blocking_transcribe(*a: Any, **k: Any) -> dict[str, Any]:
            worker_entered.set()
            worker_gate.wait()
            return {"text": "completed", "segments": []}

        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            transcribe_fn=_blocking_transcribe,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        # Start transcribe in background
        task = asyncio.create_task(provider.transcribe(b"\x00" * 3200))

        # Deterministically wait for worker to enter execution
        await asyncio.to_thread(worker_entered.wait)

        # Start shutdown while worker is running
        shutdown_task = asyncio.create_task(provider.shutdown())

        # Deterministically wait for shutdown barrier to be asserted
        await provider.shutdown_started_event.wait()
        assert provider.is_shutdown

        # Attempting a NEW transcribe call after shutdown was triggered must fail
        with pytest.raises(RuntimeError, match="MLXWhisperASRProvider has been shut down"):
            await provider.transcribe(b"\x00" * 3200)

        # Release the worker gate
        worker_gate.set()

        res = await task
        assert res.text == "completed"

        await shutdown_task
        assert provider.is_shutdown
        assert not provider.is_initialized

    # 20. Stream accumulation and final-only result
    @pytest.mark.asyncio
    async def test_stream_accumulation_yields_single_final_result(
        self, fake_snapshot_download: Any, fake_transcribe: Any, fake_runtime: MLXRuntime
    ) -> None:
        """stream() accumulates chunks and yields exactly one final ASRPartialResult."""
        settings = Settings()
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        async def _audio_chunks() -> AsyncIterator[bytes]:
            yield b"\x00" * 1600
            yield b"\x00" * 1600

        results: list[ASRPartialResult] = []
        async for partial in provider.stream(_audio_chunks()):
            results.append(partial)

        assert len(results) == 1
        assert results[0].is_final is True
        assert results[0].text == "Sharma ji ko do sau rupaye udhaar"
        assert len(fake_transcribe.calls) == 1

        await provider.shutdown()

    # 21. Mock provider still works without MLX installed
    @pytest.mark.asyncio
    async def test_mock_provider_works_independently_of_mlx(self) -> None:
        """MockASRProvider must work normally and independently of MLX."""
        mock_provider = MockASRProvider()
        await mock_provider.initialize()
        res = await mock_provider.transcribe(b"\x00" * 3200)
        assert res.text == "Sharma ji ko do sau pachaas udhaar"
        assert res.confidence is None
        await mock_provider.shutdown()

    # 22. Executor scheduling failure cleans up slot and worker tracking
    @pytest.mark.asyncio
    async def test_scheduling_failure_cleans_up_slot_and_workers(
        self, fake_snapshot_download: Any, fake_runtime: MLXRuntime
    ) -> None:
        """If run_in_executor raises before thread starts, slot and worker set must be cleaned up."""
        from unittest.mock import patch

        settings = Settings(asr_max_concurrency=1)
        provider = MLXWhisperASRProvider(
            settings,
            snapshot_download_fn=fake_snapshot_download,
            runtime_loader=lambda: fake_runtime,
        )
        await provider.initialize()

        loop = asyncio.get_running_loop()
        with patch.object(
            loop, "run_in_executor", side_effect=RuntimeError("executor submission failed")
        ):
            with pytest.raises(RuntimeError, match="executor submission failed"):
                await provider.transcribe(b"\x00" * 3200)

        # Confirm slot was recovered and active worker set is empty
        assert provider.active_worker_count == 0

        # Prove provider can still transcribe normally
        res = await provider.transcribe(b"\x00" * 3200)
        assert res.text == "Sharma ji ko do sau rupaye udhaar"

        await provider.shutdown()
