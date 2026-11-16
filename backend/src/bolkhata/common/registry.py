"""
Provider registry for voice, speech, and language model providers.

Responsible for:
- Constructing providers according to Pydantic Settings.
- Ensuring zero import-time side effects or model loading.
- Concurrency-safe, failure-safe, idempotent lifecycle management.
- Reverse-order cleanup on shutdown or initialization failure.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from bolkhata.asr.base import ASRProvider
from bolkhata.asr.mock import MockASRProvider
from bolkhata.asr.vad import MockVADProvider, VADProvider
from bolkhata.config.settings import Settings
from bolkhata.llm.base import LLMProvider
from bolkhata.llm.mock import MockLLMProvider
from bolkhata.tts.base import TTSProvider
from bolkhata.tts.mock import MockTTSProvider

logger = structlog.get_logger(__name__)


class ConfigurationError(ValueError):
    """Raised when an invalid or unconfigured provider is requested."""


class ProviderNotImplementedError(NotImplementedError):
    """Raised when a known future provider is selected before its implementation stage."""


class ProviderRegistry:
    """
    Central registry and lifecycle manager for all model providers.

    Guarantees:
    - Lazy construction without global mutable singletons.
    - Idempotent sequential initialization guarded by an asyncio.Lock.
    - Failure-safe rollback: if an error occurs during initialization,
      already-initialized providers are shut down in reverse order.
    - Reverse-order cleanup upon shutdown.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._asr: ASRProvider | None = None
        self._tts: TTSProvider | None = None
        self._llm: LLMProvider | None = None
        self._vad: VADProvider | None = None
        self._lock = asyncio.Lock()
        self._initialized: bool = False
        self._initialized_providers: list[Any] = []

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def asr(self) -> ASRProvider:
        if self._asr is None:
            self._asr = self._create_asr(self._settings.asr_provider)
        return self._asr

    @property
    def tts(self) -> TTSProvider:
        if self._tts is None:
            self._tts = self._create_tts(self._settings.tts_provider)
        return self._tts

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = self._create_llm(self._settings.llm_provider)
        return self._llm

    @property
    def vad(self) -> VADProvider | None:
        if self._vad is None and self._settings.vad_provider:
            self._vad = self._create_vad(self._settings.vad_provider)
        return self._vad

    def _create_asr(self, provider_name: str) -> ASRProvider:
        norm = provider_name.strip().lower()
        if norm == "mock":
            return MockASRProvider()
        if norm in ("faster_whisper", "mlx_whisper"):
            raise ProviderNotImplementedError(
                f"ASR provider '{provider_name}' is not yet implemented in Stage 1. "
                "Real engine adapters are scheduled for Stage 2."
            )
        raise ConfigurationError(f"Unknown ASR provider: {provider_name!r}")

    def _create_tts(self, provider_name: str) -> TTSProvider:
        norm = provider_name.strip().lower()
        if norm == "mock":
            return MockTTSProvider()
        if norm in ("piper", "edge"):
            raise ProviderNotImplementedError(
                f"TTS provider '{provider_name}' is not yet implemented in Stage 1. "
                "Real engine adapters are scheduled for Stage 2."
            )
        raise ConfigurationError(f"Unknown TTS provider: {provider_name!r}")

    def _create_llm(self, provider_name: str) -> LLMProvider:
        norm = provider_name.strip().lower()
        if norm == "mock":
            return MockLLMProvider()
        if norm in ("groq", "ollama"):
            raise ProviderNotImplementedError(
                f"LLM provider '{provider_name}' is not yet implemented in Stage 1. "
                "Real engine adapters are scheduled for Stage 2."
            )
        raise ConfigurationError(f"Unknown LLM provider: {provider_name!r}")

    def _create_vad(self, provider_name: str | None) -> VADProvider | None:
        if not provider_name or provider_name.strip().lower() in ("none", ""):
            return None
        norm = provider_name.strip().lower()
        if norm == "mock":
            return MockVADProvider()
        if norm == "silero":
            raise ProviderNotImplementedError(
                f"VAD provider '{provider_name}' is not yet implemented in Stage 1."
            )
        raise ConfigurationError(f"Unknown VAD provider: {provider_name!r}")

    async def initialize_all(self) -> None:
        """
        Sequentially initialize and warm up all configured providers.

        Guarded by an asyncio lock to be concurrency-safe.
        Failure-safe: tracks providers as soon as initialization is attempted,
        so partial initialization failures also receive reverse-order cleanup.
        Propagates original exception via bare raise while logging any cleanup issues.
        """
        async with self._lock:
            if self._initialized:
                return

            attempted_providers: list[Any] = []
            try:
                # 1. ASR
                asr_prov = self.asr
                attempted_providers.append(asr_prov)
                await asr_prov.initialize()
                await asr_prov.warmup()

                # 2. TTS
                tts_prov = self.tts
                attempted_providers.append(tts_prov)
                await tts_prov.initialize()
                await tts_prov.warmup()

                # 3. LLM
                llm_prov = self.llm
                attempted_providers.append(llm_prov)
                await llm_prov.initialize()
                await llm_prov.warmup()

                # 4. Optional VAD
                if self.vad is not None:
                    vad_prov = self.vad
                    attempted_providers.append(vad_prov)
                    await vad_prov.initialize()

                self._initialized_providers = attempted_providers
                self._initialized = True
            except BaseException:
                # Failure rollback: clean up all attempted providers in reverse order
                failed_cleanups: list[Any] = []
                for prov in reversed(attempted_providers):
                    try:
                        await prov.shutdown()
                    except Exception as clean_err:
                        failed_cleanups.append(prov)
                        logger.error(
                            "provider_rollback_failed",
                            provider=type(prov).__name__,
                            error=str(clean_err),
                        )
                # Retain any providers that failed shutdown for future retry
                self._initialized_providers = failed_cleanups
                self._initialized = False
                # Bare raise preserves the original initialization error and full traceback
                raise

    async def shutdown_all(self) -> None:
        """
        Shut down all initialized providers in reverse order.

        Idempotent and concurrency-safe.
        Tracks which providers succeed and retains failed providers so subsequent
        shutdown calls can retry them.
        """
        async with self._lock:
            if not self._initialized and not self._initialized_providers:
                return

            targets: list[Any] = []
            if self._initialized_providers:
                for p in reversed(self._initialized_providers):
                    if p not in targets:
                        targets.append(p)
            else:
                for p in (self._vad, self._llm, self._tts, self._asr):
                    if p is not None and p not in targets:
                        targets.append(p)

            if not targets:
                self._initialized = False
                return

            failed_providers: list[Any] = []
            errors: list[Exception] = []

            for provider in targets:
                try:
                    await provider.shutdown()
                except Exception as err:
                    failed_providers.append(provider)
                    errors.append(err)
                    logger.error(
                        "provider_shutdown_failed",
                        provider=type(provider).__name__,
                        error=str(err),
                    )

            # Retain providers that failed shutdown for retry
            self._initialized_providers = failed_providers
            if failed_providers:
                # Do not report successful shutdown if a provider failed to release its resources
                self._initialized = False
                raise errors[0]

            self._initialized = False
            self._initialized_providers = []
