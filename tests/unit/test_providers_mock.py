"""
Unit tests for ASR, TTS, and LLM provider contracts, mocks, and registry lifecycle.
"""

from __future__ import annotations

import asyncio
import struct
from collections.abc import AsyncIterator

import pytest
from pydantic import BaseModel, Field

from bolkhata.asr.base import ASRPartialResult, ASRProvider, ASRResult, WordTiming
from bolkhata.asr.mock import MockASRProvider
from bolkhata.asr.vad import MockVADProvider, VADDecision, VADProvider
from bolkhata.common.registry import (
    ConfigurationError,
    ProviderNotImplementedError,
    ProviderRegistry,
)
from bolkhata.config.settings import Settings
from bolkhata.llm.base import ChatMessage, LLMProvider
from bolkhata.llm.mock import MockLLMProvider
from bolkhata.tts.base import TTSChunk, TTSProvider, TTSResult
from bolkhata.tts.mock import MockTTSProvider, generate_mock_pcm


# ---------------------------------------------------------------------------
# Test Schemas for Structured Output
# ---------------------------------------------------------------------------
class DummyEntry(BaseModel):
    customer: str
    amount: int
    note: str = Field(default="cash")


# ---------------------------------------------------------------------------
# ASR Provider & Mock Tests
# ---------------------------------------------------------------------------
class TestASRProviderContract:
    @pytest.mark.asyncio
    async def test_mock_asr_implements_interface(self) -> None:
        provider: ASRProvider = MockASRProvider()
        assert isinstance(provider, ASRProvider)

    @pytest.mark.asyncio
    async def test_mock_asr_transcribe_deterministic(self) -> None:
        provider = MockASRProvider(canned_text="Sharma ji do sau udhaar")
        result = await provider.transcribe(b"\x00" * 3200)

        assert isinstance(result, ASRResult)
        assert result.text == "Sharma ji do sau udhaar"
        assert result.language == "hi"
        assert result.confidence > 0.0
        assert isinstance(result.words, tuple)
        assert len(result.words) > 0
        assert all(isinstance(w, WordTiming) for w in result.words)

    @pytest.mark.asyncio
    async def test_asr_result_immutable_and_coerces_tuple(self) -> None:
        timings = [WordTiming(word="test", start_ms=0, end_ms=100)]
        # Passing list should coerce to immutable tuple in post_init
        result = ASRResult(
            text="test",
            language="en",
            confidence=1.0,
            duration_ms=100.0,
            words=timings,  # type: ignore[arg-type]
        )
        assert isinstance(result.words, tuple)
        with pytest.raises(AttributeError):
            result.text = "modified"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_mock_asr_streaming(self) -> None:
        provider = MockASRProvider(canned_text="ek do teen")

        async def audio_chunks() -> AsyncIterator[bytes]:
            for _ in range(4):
                yield b"\x00" * 800

        partials: list[ASRPartialResult] = []
        async for partial in provider.stream(audio_chunks()):
            partials.append(partial)

        assert len(partials) >= 2
        assert not partials[0].is_final
        assert partials[-1].is_final
        assert partials[-1].text == "ek do teen"

    @pytest.mark.asyncio
    async def test_mock_asr_lifecycle_state(self) -> None:
        provider = MockASRProvider()
        assert not provider.is_initialized

        await provider.initialize()
        assert provider.is_initialized
        assert provider.initialize_calls == 1

        await provider.warmup()
        assert provider.is_warmed_up
        assert provider.warmup_calls == 1

        await provider.shutdown()
        assert not provider.is_initialized
        assert provider.is_shutdown
        assert provider.shutdown_calls == 1


# ---------------------------------------------------------------------------
# TTS Provider & Mock Tests
# ---------------------------------------------------------------------------
class TestTTSProviderContract:
    @pytest.mark.asyncio
    async def test_mock_tts_implements_interface(self) -> None:
        provider: TTSProvider = MockTTSProvider()
        assert isinstance(provider, TTSProvider)

    @pytest.mark.asyncio
    async def test_mock_tts_synthesize_valid_pcm(self) -> None:
        provider = MockTTSProvider(chunk_duration_ms=100.0, num_chunks=2)
        result: TTSResult = await provider.synthesize("Sharma ji")

        assert result.sample_rate == 16000
        assert result.encoding == "pcm_s16le"
        assert result.duration_ms == 200.0

        # Duration 200ms at 16000Hz = 3200 samples = 6400 bytes
        expected_bytes = int((200.0 / 1000.0) * 16000 * 2)
        assert len(result.audio_bytes) == expected_bytes

        # Verify bytes are valid signed 16-bit integers
        num_samples = len(result.audio_bytes) // 2
        samples = struct.unpack(f"<{num_samples}h", result.audio_bytes)
        assert len(samples) == num_samples
        assert all(-32768 <= s <= 32767 for s in samples)

    @pytest.mark.asyncio
    async def test_mock_tts_stream(self) -> None:
        provider = MockTTSProvider(chunk_duration_ms=50.0, num_chunks=3)

        async def text_tokens() -> AsyncIterator[str]:
            for token in ["Hello ", "world"]:
                yield token

        chunks: list[TTSChunk] = []
        async for chunk in provider.stream(text_tokens()):
            chunks.append(chunk)

        assert len(chunks) == 3
        for i, c in enumerate(chunks):
            assert c.sequence_number == i
            assert c.sample_rate == 16000
            assert len(c.pcm_bytes) == int((50.0 / 1000.0) * 16000 * 2)
            if i < 2:
                assert not c.is_final
            else:
                assert c.is_final

    def test_generate_mock_pcm_deterministic(self) -> None:
        pcm1 = generate_mock_pcm(duration_ms=50.0, freq_hz=440.0)
        pcm2 = generate_mock_pcm(duration_ms=50.0, freq_hz=440.0)
        assert pcm1 == pcm2
        assert len(pcm1) == 1600  # 50ms * 16 samples/ms * 2 bytes/sample


# ---------------------------------------------------------------------------
# LLM Provider & Mock Tests
# ---------------------------------------------------------------------------
class TestLLMProviderContract:
    @pytest.mark.asyncio
    async def test_mock_llm_implements_interface(self) -> None:
        provider: LLMProvider = MockLLMProvider()
        assert isinstance(provider, LLMProvider)

    @pytest.mark.asyncio
    async def test_mock_llm_stream_chat(self) -> None:
        tokens = ["Haan, ", "Sharma ji ka ", "khata."]
        provider = MockLLMProvider(canned_tokens=tokens)
        messages = [
            ChatMessage(role="system", content="You are a kirana assistant."),
            ChatMessage(role="user", content="Sharma ji ka khata dikhao"),
        ]

        received: list[str] = []
        async for delta in provider.stream_chat(messages):
            received.append(delta)

        assert received == tokens
        assert provider.stream_chat_calls == 1

    @pytest.mark.asyncio
    async def test_mock_llm_complete_structured_with_fixture(self) -> None:
        fixture = DummyEntry(customer="Verma", amount=500, note="cash")
        provider = MockLLMProvider(structured_fixtures={DummyEntry: fixture})

        messages = [ChatMessage(role="user", content="Verma 500")]
        result = await provider.complete_structured(messages, DummyEntry)

        assert result.customer == "Verma"
        assert result.amount == 500
        assert result.note == "cash"
        assert provider.structured_calls == 1

    @pytest.mark.asyncio
    async def test_mock_llm_complete_structured_dynamic_fallback(self) -> None:
        provider = MockLLMProvider()
        messages = [ChatMessage(role="user", content="generate")]
        result = await provider.complete_structured(messages, DummyEntry)

        assert isinstance(result, DummyEntry)
        assert result.customer == "mock_value"
        assert result.amount == 1


# ---------------------------------------------------------------------------
# VAD Provider & Mock Tests
# ---------------------------------------------------------------------------
class TestVADProviderContract:
    @pytest.mark.asyncio
    async def test_mock_vad_interface(self) -> None:
        vad: VADProvider = MockVADProvider(default_is_speech=True, default_confidence=0.88)
        assert isinstance(vad, VADProvider)

        await vad.initialize()
        decision: VADDecision = await vad.process_frame(b"\x00" * 960)
        assert decision.is_speech is True
        assert decision.confidence == 0.88
        await vad.shutdown()


# ---------------------------------------------------------------------------
# Provider Registry Lifecycle & Error Handling Tests
# ---------------------------------------------------------------------------
class TestProviderRegistry:
    def test_default_mock_selection(self) -> None:
        settings = Settings(asr_provider="mock", tts_provider="mock", llm_provider="mock")
        registry = ProviderRegistry(settings)

        assert isinstance(registry.asr, MockASRProvider)
        assert isinstance(registry.tts, MockTTSProvider)
        assert isinstance(registry.llm, MockLLMProvider)
        assert registry.vad is None
        assert not registry.is_initialized

    def test_vad_optional_instantiation(self) -> None:
        settings = Settings(vad_provider="mock")
        registry = ProviderRegistry(settings)
        assert isinstance(registry.vad, MockVADProvider)

        settings_none = Settings(vad_provider=None)
        assert ProviderRegistry(settings_none).vad is None

    def test_unknown_provider_raises_configuration_error(self) -> None:
        # Settings validator catches it at config level
        with pytest.raises(ValueError, match="ASR_PROVIDER must be one of"):
            Settings(asr_provider="invalid_asr")

        with pytest.raises(ValueError, match="TTS_PROVIDER must be one of"):
            Settings(tts_provider="invalid_tts")

        with pytest.raises(ValueError, match="LLM_PROVIDER must be one of"):
            Settings(llm_provider="invalid_llm")

        # Direct registry factory methods raise ConfigurationError on unknown names
        registry = ProviderRegistry(Settings())
        with pytest.raises(ConfigurationError, match="Unknown ASR provider"):
            registry._create_asr("unknown_engine")
        with pytest.raises(ConfigurationError, match="Unknown TTS provider"):
            registry._create_tts("unknown_engine")
        with pytest.raises(ConfigurationError, match="Unknown LLM provider"):
            registry._create_llm("unknown_engine")
        with pytest.raises(ConfigurationError, match="Unknown VAD provider"):
            registry._create_vad("unknown_engine")

    def test_future_provider_raises_not_implemented_in_stage1(self) -> None:
        settings_asr = Settings(asr_provider="faster_whisper")
        reg_asr = ProviderRegistry(settings_asr)
        with pytest.raises(ProviderNotImplementedError, match="Stage 1"):
            _ = reg_asr.asr

        settings_tts = Settings(tts_provider="piper")
        reg_tts = ProviderRegistry(settings_tts)
        with pytest.raises(ProviderNotImplementedError, match="Stage 1"):
            _ = reg_tts.tts

        settings_llm = Settings(llm_provider="groq")
        reg_llm = ProviderRegistry(settings_llm)
        with pytest.raises(ProviderNotImplementedError, match="Stage 1"):
            _ = reg_llm.llm

    @pytest.mark.asyncio
    async def test_registry_lifecycle_idempotent_and_non_blocking(self) -> None:
        settings = Settings(
            asr_provider="mock",
            tts_provider="mock",
            llm_provider="mock",
            vad_provider="mock",
        )
        registry = ProviderRegistry(settings)

        # 1. Initialize
        await registry.initialize_all()
        assert registry.is_initialized
        assert registry.asr.is_initialized  # type: ignore[attr-defined]
        assert registry.tts.is_initialized  # type: ignore[attr-defined]
        assert registry.llm.is_initialized  # type: ignore[attr-defined]
        assert registry.vad.is_initialized  # type: ignore[union-attr]

        # 2. Repeated initialize is idempotent no-op
        await registry.initialize_all()
        assert registry.asr.initialize_calls == 1  # type: ignore[attr-defined]

        # 3. Shutdown
        await registry.shutdown_all()
        assert not registry.is_initialized
        assert registry.asr.is_shutdown  # type: ignore[attr-defined]
        assert registry.tts.is_shutdown  # type: ignore[attr-defined]
        assert registry.llm.is_shutdown  # type: ignore[attr-defined]

        # 4. Repeated shutdown is idempotent
        await registry.shutdown_all()
        assert registry.asr.shutdown_calls == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_registry_concurrency_safe_initialization(self) -> None:
        settings = Settings()
        registry = ProviderRegistry(settings)

        # Launch 5 concurrent initialization tasks
        await asyncio.gather(*(registry.initialize_all() for _ in range(5)))
        assert registry.is_initialized
        assert registry.asr.initialize_calls == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_registry_initialization_failure_rollback(self) -> None:
        """
        Verify that if provider initialization fails midway, already-initialized
        providers are rolled back in reverse order.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        # Pre-instantiate ASR and inject a failing TTS provider
        _ = registry.asr

        class FailingTTSProvider(MockTTSProvider):
            async def initialize(self) -> None:
                raise RuntimeError("Simulated TTS initialization failure")

        registry._tts = FailingTTSProvider()

        with pytest.raises(RuntimeError, match="Simulated TTS initialization failure"):
            await registry.initialize_all()

        # ASR should have been rolled back cleanly
        assert not registry.is_initialized
        assert registry.asr.is_shutdown  # type: ignore[attr-defined]
        assert registry.asr.shutdown_calls == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_registry_shutdown_reverse_order(self) -> None:
        """
        Verify providers are shut down in reverse order: VAD -> LLM -> TTS -> ASR.
        """
        settings = Settings(vad_provider="mock")
        registry = ProviderRegistry(settings)
        await registry.initialize_all()

        shutdown_order: list[str] = []

        # Hook into shutdown calls
        orig_asr_shutdown = registry.asr.shutdown
        orig_tts_shutdown = registry.tts.shutdown
        orig_llm_shutdown = registry.llm.shutdown
        orig_vad_shutdown = registry.vad.shutdown  # type: ignore[union-attr]

        async def asr_sd() -> None:
            shutdown_order.append("asr")
            await orig_asr_shutdown()

        async def tts_sd() -> None:
            shutdown_order.append("tts")
            await orig_tts_shutdown()

        async def llm_sd() -> None:
            shutdown_order.append("llm")
            await orig_llm_shutdown()

        async def vad_sd() -> None:
            shutdown_order.append("vad")
            await orig_vad_shutdown()

        registry.asr.shutdown = asr_sd  # type: ignore[method-assign]
        registry.tts.shutdown = tts_sd  # type: ignore[method-assign]
        registry.llm.shutdown = llm_sd  # type: ignore[method-assign]
        registry.vad.shutdown = vad_sd  # type: ignore[union-attr,method-assign]

        await registry.shutdown_all()

        # Reverse of [asr, tts, llm, vad] is [vad, llm, tts, asr]
        assert shutdown_order == ["vad", "llm", "tts", "asr"]
