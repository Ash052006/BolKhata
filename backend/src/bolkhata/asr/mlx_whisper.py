"""
MLX-Whisper Automatic Speech Recognition provider for Apple Silicon macOS.

Executes local Whisper inference on Apple Silicon (M-series) unified memory
via Apple MLX and mlx-whisper.

Requirements:
- Apple Silicon macOS (Darwin arm64).
- Optional dependency extra: mlx-whisper (mlx-whisper==0.4.3).
- Zero network downloads in offline mode; explicit pinned commit hash revision.
- Bounded thread pool with cancellation-safe concurrency tracking.
- Honest confidence semantics: None unless a calibrated probability is supplied.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import math
import sys
import threading
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from bolkhata.asr.base import ASRPartialResult, ASRProvider, ASRResult, WordTiming
from bolkhata.asr.common import (
    BYTES_PER_SAMPLE,
    AudioFormatError,
    compute_duration_ms,
    pcm_to_float32,
)
from bolkhata.config.settings import Settings

logger = structlog.get_logger(__name__)


class DependencyMissingError(ImportError):
    """Raised when optional runtime dependencies for MLX-Whisper are unavailable."""


class ModelResolutionError(RuntimeError):
    """Raised when model weights cannot be resolved locally or safely downloaded."""


@dataclass(frozen=True)
class MLXRuntime:
    """Loaded runtime dependencies for MLX-Whisper."""

    mlx_core: Any
    mlx_whisper: Any
    numpy: Any


def load_mlx_runtime() -> MLXRuntime:
    """
    Lazily import and return the MLX and NumPy runtime dependencies.

    Raises:
        DependencyMissingError: If optional mlx-whisper dependencies are missing.
    """
    if sys.platform != "darwin":
        raise DependencyMissingError(
            f"MLXWhisperASRProvider requires Apple Silicon macOS (darwin). "
            f"Current platform: {sys.platform!r}."
        )

    try:
        import mlx.core as mx
        import mlx_whisper  # type: ignore[import-untyped]
        import numpy as np

        return MLXRuntime(mlx_core=mx, mlx_whisper=mlx_whisper, numpy=np)
    except ImportError as err:
        raise DependencyMissingError(
            "Optional dependencies for MLX-Whisper are missing. "
            "Install them with: uv sync --extra mlx-whisper (Apple Silicon macOS only)."
        ) from err


def resolve_model_path(
    model_id: str,
    model_revision: str | None,
    model_dir: str | None,
    offline_mode: bool,
    snapshot_download_fn: Any = None,
) -> Path:
    """
    Resolve the local directory for the configured MLX-Whisper model.

    Guarantees:
    - Requires an explicit, full immutable 40-character commit hash revision.
    - Never falls back to mutable 'main' or unpinned revisions.
    - In offline mode, strictly forbids network requests.
    - If model_dir points directly to a complete model directory (contains config.json),
      returns it immediately without invoking snapshot_download.
    - If model_dir does not contain config.json, treats it as the local cache_dir.

    Args:
        model_id: Hugging Face repository ID (e.g. 'mlx-community/whisper-small-mlx').
        model_revision: Full 40-character hexadecimal commit hash.
        model_dir: Optional path to a local directory or cache root.
        offline_mode: If True, only allow local files; never touch network.
        snapshot_download_fn: Optional injected snapshot_download callable for testing.

    Returns:
        Path to the resolved local model directory containing config.json.
    """
    if not model_id or not model_id.strip():
        raise ModelResolutionError("Model ID cannot be empty.")

    if not model_revision or not model_revision.strip():
        raise ModelResolutionError(
            "An explicit full immutable model revision hash is required. "
            "Unpinned mutable revisions (such as 'main') are strictly prohibited."
        )

    revision = model_revision.strip().lower()
    if len(revision) != 40 or not all(c in "0123456789abcdef" for c in revision):
        raise ModelResolutionError(
            f"Model revision must be a full 40-character hex commit hash. Got: {model_revision!r}"
        )

    # Check if model_dir points directly to an existing model directory with config.json
    cache_dir: Path | None = None
    if model_dir:
        model_dir_path = Path(model_dir).expanduser().resolve()
        if (model_dir_path / "config.json").is_file():
            return model_dir_path
        cache_dir = model_dir_path

    if snapshot_download_fn is None:
        try:
            from huggingface_hub import snapshot_download as hf_snapshot_download
            from huggingface_hub.errors import (
                HfHubHTTPError,
                LocalEntryNotFoundError,
                OfflineModeIsEnabled,
            )

            snapshot_download_fn = hf_snapshot_download
            local_not_found_errors: tuple[type[Exception], ...] = (
                LocalEntryNotFoundError,
                OfflineModeIsEnabled,
                HfHubHTTPError,
            )
        except ImportError as err:
            raise DependencyMissingError(
                "Optional dependency 'huggingface_hub' is required for model resolution. "
                "Install it with: uv sync --extra mlx-whisper"
            ) from err
    else:
        local_not_found_errors = (Exception,)

    try:
        resolved_str = snapshot_download_fn(
            repo_id=model_id,
            revision=revision,
            local_files_only=offline_mode,
            cache_dir=str(cache_dir) if cache_dir else None,
        )
    except local_not_found_errors as err:
        if offline_mode:
            raise ModelResolutionError(
                f"Model '{model_id}' revision '{revision}' is unavailable locally in offline mode: {err}"
            ) from err
        raise ModelResolutionError(
            f"Failed to download model '{model_id}' revision '{revision}': {err}"
        ) from err
    except Exception as err:
        raise ModelResolutionError(
            f"Unexpected error resolving model '{model_id}' revision '{revision}': {err}"
        ) from err

    resolved_path = Path(resolved_str).resolve()
    if not (resolved_path / "config.json").is_file():
        raise ModelResolutionError(
            f"Resolved model directory '{resolved_path}' does not contain 'config.json'."
        )

    return resolved_path


def map_runtime_result(
    raw_output: dict[str, Any],
    duration_ms: float,
    fallback_language: str = "hi",
) -> ASRResult:
    """
    Map MLX-Whisper raw dictionary output to the BolKhata ASRResult contract.

    Semantics:
    - Convert seconds to milliseconds (start_ms, end_ms).
    - Map word-level probability if documented and valid (0.0 <= p <= 1.0); else None.
    - Overall confidence is strictly None (avg_logprob is uncalibrated).
    - Handle missing or malformed word/segment structures safely without raising.
    - Preserve punctuation in word tokens as returned by the runtime.
    """
    text = str(raw_output.get("text", "")).strip()
    language = str(raw_output.get("language") or fallback_language)

    # MLX-Whisper does not provide a calibrated overall probability
    confidence: float | None = None

    words: list[WordTiming] = []
    segments = raw_output.get("segments")
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            seg_words = segment.get("words")
            if not isinstance(seg_words, list):
                continue
            for w in seg_words:
                if not isinstance(w, dict):
                    continue
                w_text = str(w.get("word", ""))
                try:
                    start_s = float(w.get("start", 0.0))
                    end_s = float(w.get("end", 0.0))
                    if not (math.isfinite(start_s) and math.isfinite(end_s)):
                        continue
                except (ValueError, TypeError):
                    continue

                raw_prob = w.get("probability")
                word_conf: float | None = None
                if raw_prob is not None:
                    try:
                        p_float = float(raw_prob)
                        if math.isfinite(p_float) and 0.0 <= p_float <= 1.0:
                            word_conf = p_float
                    except (ValueError, TypeError):
                        word_conf = None

                words.append(
                    WordTiming(
                        word=w_text,
                        start_ms=round(start_s * 1000.0, 2),
                        end_ms=round(end_s * 1000.0, 2),
                        confidence=word_conf,
                    )
                )

    return ASRResult(
        text=text,
        language=language,
        confidence=confidence,
        duration_ms=duration_ms,
        words=tuple(words),
    )


class MLXWhisperASRProvider(ASRProvider):
    """
    Speech recognition provider using MLX-Whisper on Apple Silicon macOS.

    Attributes & Guarantees:
    - Lazy loading: dependencies are imported only on initialize(), not module import.
    - Concurrency bounding: respects asr_max_concurrency without unbounded thread creation.
    - Cancellation safety: cancelling the awaiting coroutine does NOT release the
      concurrency slot while the underlying synchronous thread is still executing.
    - Clean shutdown: marks shutdown synchronously before awaiting, rejects new requests,
      and waits for running worker threads before releasing thread pool resources.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        snapshot_download_fn: Any = None,
        transcribe_fn: Any = None,
        runtime_loader: Callable[[], MLXRuntime] | None = None,
    ) -> None:
        self._settings = settings
        self._snapshot_download_fn = snapshot_download_fn
        self._transcribe_fn = transcribe_fn
        self._runtime_loader = runtime_loader or load_mlx_runtime
        self._runtime: MLXRuntime | None = None

        # State tracking
        self._is_initialized: bool = False
        self._is_warmed_up: bool = False
        self._is_shutdown: bool = False
        self._shutdown_started_event: asyncio.Event = asyncio.Event()
        self._resolved_model_path: Path | None = None

        # Concurrency & thread management
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._worker_counter: int = 0
        self._active_workers: set[int] = set()
        self._worker_lock: threading.Lock = threading.Lock()
        self._all_workers_done: threading.Event = threading.Event()
        self._all_workers_done.set()

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def is_warmed_up(self) -> bool:
        return self._is_warmed_up

    @property
    def is_shutdown(self) -> bool:
        return self._is_shutdown

    @property
    def shutdown_started_event(self) -> asyncio.Event:
        return self._shutdown_started_event

    @property
    def active_worker_count(self) -> int:
        with self._worker_lock:
            return len(self._active_workers)

    @property
    def resolved_model_path(self) -> Path | None:
        return self._resolved_model_path

    async def initialize(self) -> None:
        """
        Verify runtime dependencies, resolve model path, and allocate worker pool.

        Idempotent: redundant calls return immediately.
        """
        if self._is_initialized:
            return

        # Load runtime dependencies via injectable loader
        self._runtime = self._runtime_loader()
        if self._transcribe_fn is None:
            self._transcribe_fn = self._runtime.mlx_whisper.transcribe

        # Resolve pinned model directory
        self._resolved_model_path = resolve_model_path(
            model_id=self._settings.asr_mlx_whisper_model_id,
            model_revision=self._settings.asr_mlx_whisper_model_revision,
            model_dir=self._settings.asr_model_dir,
            offline_mode=self._settings.asr_offline_mode,
            snapshot_download_fn=self._snapshot_download_fn,
        )

        # Set up bounded worker pool and concurrency semaphore
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._settings.asr_max_concurrency,
            thread_name_prefix="bolkhata-asr-mlx",
        )
        self._semaphore = asyncio.Semaphore(self._settings.asr_max_concurrency)
        self._shutdown_started_event = asyncio.Event()

        self._is_initialized = True
        self._is_shutdown = False
        logger.info(
            "mlx_whisper_provider_initialized",
            model_id=self._settings.asr_mlx_whisper_model_id,
            revision=self._settings.asr_mlx_whisper_model_revision,
            model_path=str(self._resolved_model_path),
            concurrency=self._settings.asr_max_concurrency,
        )

    async def warmup(self) -> None:
        """
        Warm up execution graphs.

        Warmup with real weights is explicitly deferred to hardware smoke testing
        to prevent unintended weight downloads or heavy graph generation at startup.
        """
        if not self._is_initialized:
            raise RuntimeError("MLXWhisperASRProvider is not initialized.")
        if self._is_shutdown:
            raise RuntimeError("MLXWhisperASRProvider has been shut down.")
        self._is_warmed_up = True

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        initial_prompt: str | None = None,
    ) -> ASRResult:
        """
        Transcribe a complete 16kHz mono signed 16-bit little-endian PCM buffer.

        Guarantees:
        - Rejects uninitialized or shut-down invocation.
        - Empty audio returns empty result with confidence=None immediately.
        - Audio exceeding asr_max_duration_seconds is rejected.
        - Cancelling coroutine does NOT release the concurrency slot while thread runs.
        """
        if not self._is_initialized:
            raise RuntimeError("MLXWhisperASRProvider is not initialized.")
        if self._is_shutdown:
            raise RuntimeError("MLXWhisperASRProvider has been shut down.")

        # Empty audio optimization: do not invoke inference
        if not audio_bytes:
            return ASRResult(
                text="",
                language=language or "hi",
                confidence=None,
                duration_ms=0.0,
                words=(),
            )

        if len(audio_bytes) % BYTES_PER_SAMPLE != 0:
            raise AudioFormatError(
                f"Audio buffer byte count must be a multiple of {BYTES_PER_SAMPLE} bytes, "
                f"got {len(audio_bytes)} bytes."
            )

        duration_ms = compute_duration_ms(len(audio_bytes))
        max_duration_ms = self._settings.asr_max_duration_seconds * 1000.0
        if duration_ms > max_duration_ms:
            raise AudioFormatError(
                f"Audio duration {duration_ms:.1f}ms exceeds maximum allowed {max_duration_ms:.1f}ms"
            )

        # Standard conversion to float32 samples in [-1.0, 1.0]
        float32_array = pcm_to_float32(audio_bytes)
        np_module = self._runtime.numpy if self._runtime is not None else None
        if np_module is None:
            import numpy as np

            np_module = np
        assert np_module is not None
        audio_np = np_module.frombuffer(float32_array, dtype=np_module.float32)

        # Bounded concurrency acquisition
        sem = self._semaphore
        executor = self._executor
        assert sem is not None
        assert executor is not None
        await sem.acquire()

        # Re-check shutdown status after acquiring semaphore slot
        if self._is_shutdown:
            sem.release()
            raise RuntimeError("MLXWhisperASRProvider has been shut down.")

        loop = asyncio.get_running_loop()

        with self._worker_lock:
            self._worker_counter += 1
            worker_id = self._worker_counter
            self._active_workers.add(worker_id)
            self._all_workers_done.clear()

        slot_owned_by_thread = False
        target_path = str(self._resolved_model_path)
        transcribe_fn = self._transcribe_fn

        def _run_sync_inference() -> ASRResult:
            try:
                raw = transcribe_fn(
                    audio_np,
                    path_or_hf_repo=target_path,
                    language=language,
                    initial_prompt=initial_prompt,
                    word_timestamps=True,
                    verbose=False,
                )
                return map_runtime_result(raw, duration_ms, fallback_language=language or "hi")
            finally:
                with self._worker_lock:
                    self._active_workers.discard(worker_id)
                    if not self._active_workers:
                        self._all_workers_done.set()
                # Concurrency slot is released ONLY after thread completion
                loop.call_soon_threadsafe(sem.release)

        try:
            fut = loop.run_in_executor(executor, _run_sync_inference)
            slot_owned_by_thread = True
            return await fut
        finally:
            if not slot_owned_by_thread:
                with self._worker_lock:
                    self._active_workers.discard(worker_id)
                    if not self._active_workers:
                        self._all_workers_done.set()
                sem.release()

    async def stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[ASRPartialResult]:
        """
        Push-to-talk stream accumulation for sequence-to-sequence Whisper.

        Whisper is not a causal streaming recognizer. Chunks are accumulated
        during speech, and a single final batch transcription is executed at stream end.
        """
        if not self._is_initialized:
            raise RuntimeError("MLXWhisperASRProvider is not initialized.")
        if self._is_shutdown:
            raise RuntimeError("MLXWhisperASRProvider has been shut down.")

        buffer = bytearray()
        max_bytes = int(self._settings.asr_max_duration_seconds * 16000 * BYTES_PER_SAMPLE)

        async for chunk in audio_stream:
            buffer.extend(chunk)
            if len(buffer) > max_bytes:
                raise AudioFormatError(
                    f"Accumulated stream audio exceeds maximum duration limit of "
                    f"{self._settings.asr_max_duration_seconds}s."
                )

        if not buffer:
            yield ASRPartialResult(text="", is_final=True)
            return

        result = await self.transcribe(bytes(buffer))
        yield ASRPartialResult(text=result.text, is_final=True)

    async def shutdown(self) -> None:
        """
        Shut down provider cleanly.

        Idempotent: marks shutdown immediately before any suspension point,
        signals shutdown_started_event, and waits for running worker threads
        before releasing thread pool resources.
        """
        if self._is_shutdown or not self._is_initialized:
            self._is_shutdown = True
            self._shutdown_started_event.set()
            self._is_initialized = False
            return

        # Synchronously mark shutdown and signal barrier before any suspension point
        self._is_shutdown = True
        self._shutdown_started_event.set()

        # Wait for all running worker threads to finish and clean up executor off-loop
        executor = self._executor
        self._executor = None
        if executor is not None:
            await asyncio.to_thread(self._cleanup_executor, executor, self._all_workers_done)

        self._semaphore = None
        self._is_initialized = False
        logger.info("mlx_whisper_provider_shutdown")

    @staticmethod
    def _cleanup_executor(
        executor: concurrent.futures.ThreadPoolExecutor,
        all_workers_done: threading.Event,
    ) -> None:
        """Wait for active workers to complete and cleanly shut down the thread pool off-loop."""
        all_workers_done.wait()
        executor.shutdown(wait=True)
