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
from bolkhata.llm.mock import (
    MockFixtureMissingError,
    MockFixtureTypeMismatchError,
    MockLLMProvider,
)
from bolkhata.tts.base import TTSChunk, TTSProvider, TTSResult
from bolkhata.tts.mock import MockTTSProvider, generate_mock_pcm


# ---------------------------------------------------------------------------
# Test Schemas for Structured Output
# ---------------------------------------------------------------------------
class DummyEntry(BaseModel):
    customer: str
    amount: int
    note: str = Field(default="cash")


class ModelWithDefaults(BaseModel):
    status: str = "ok"
    count: int = 0


class FinancialTransaction(BaseModel):
    customer_name: str
    amount_inr: float
    transaction_type: str


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
        # Honest confidence: unavailable by default unless supplied by fixture
        assert result.confidence is None
        assert isinstance(result.words, tuple)
        assert len(result.words) > 0
        assert all(isinstance(w, WordTiming) for w in result.words)
        assert all(w.confidence is None for w in result.words)

    @pytest.mark.asyncio
    async def test_mock_asr_transcribe_with_explicit_confidence_fixture(self) -> None:
        provider = MockASRProvider(
            canned_text="Sharma ji do sau udhaar",
            confidence=0.95,
        )
        result = await provider.transcribe(b"\x00" * 3200)

        assert result.confidence == 0.95
        assert all(w.confidence == 0.95 for w in result.words)

    @pytest.mark.asyncio
    async def test_mock_asr_transcribe_empty_audio_returns_empty_result(self) -> None:
        provider = MockASRProvider(confidence=0.95)
        result = await provider.transcribe(b"")

        assert result.text == ""
        assert result.confidence is None
        assert result.duration_ms == 0.0
        assert result.words == ()

    @pytest.mark.asyncio
    async def test_mock_asr_transcribe_initial_prompt_pass_through(self) -> None:
        provider = MockASRProvider()
        test_prompt = "Sharma ji, udhaar, chawal, kirana"
        result = await provider.transcribe(
            b"\x00" * 1600,
            language="hi",
            initial_prompt=test_prompt,
        )

        assert isinstance(result, ASRResult)
        assert provider.last_initial_prompt == test_prompt
        assert provider.initial_prompts == [test_prompt]

    @pytest.mark.asyncio
    async def test_word_timing_and_asr_result_optional_confidence_semantics(self) -> None:
        # WordTiming with available and unavailable confidence
        wt_none = WordTiming(word="namaste", start_ms=0.0, end_ms=250.0)
        assert wt_none.confidence is None

        wt_val = WordTiming(word="sharma", start_ms=250.0, end_ms=500.0, confidence=0.88)
        assert wt_val.confidence == 0.88

        # ASRResult with available and unavailable confidence
        res_none = ASRResult(
            text="namaste",
            language="hi",
            confidence=None,
            duration_ms=250.0,
            words=(wt_none,),
        )
        assert res_none.confidence is None

        res_val = ASRResult(
            text="sharma",
            language="hi",
            confidence=0.88,
            duration_ms=250.0,
            words=(wt_val,),
        )
        assert res_val.confidence == 0.88
        assert res_val.words[0].confidence == 0.88

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
    async def test_mock_llm_complete_structured_with_defaults(self) -> None:
        provider = MockLLMProvider()
        messages = [ChatMessage(role="user", content="ping")]
        result = await provider.complete_structured(messages, ModelWithDefaults)

        assert isinstance(result, ModelWithDefaults)
        assert result.status == "ok"
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_mock_llm_complete_structured_missing_fixture_fails(self) -> None:
        provider = MockLLMProvider()
        messages = [ChatMessage(role="user", content="Verma 500")]
        with pytest.raises(
            MockFixtureMissingError,
            match="has required fields and no deterministic fixture was registered",
        ):
            await provider.complete_structured(messages, DummyEntry)

    @pytest.mark.asyncio
    async def test_mock_llm_complete_structured_financial_schema_fails_without_fixture(
        self,
    ) -> None:
        provider = MockLLMProvider()
        messages = [ChatMessage(role="user", content="Gupta 1200 udhaar")]
        with pytest.raises(MockFixtureMissingError, match="FinancialTransaction"):
            await provider.complete_structured(messages, FinancialTransaction)

    @pytest.mark.asyncio
    async def test_mock_llm_complete_structured_type_mismatch_rejected(self) -> None:
        # Fixture registered for DummyEntry is actually of an incompatible type
        provider = MockLLMProvider(
            structured_fixtures={DummyEntry: ModelWithDefaults()}  # type: ignore[dict-item]
        )
        messages = [ChatMessage(role="user", content="Verma 500")]
        with pytest.raises(
            MockFixtureTypeMismatchError,
            match="Fixture registered for DummyEntry is of type ModelWithDefaults",
        ):
            await provider.complete_structured(messages, DummyEntry)


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

    def test_asr_max_concurrency_settings(self) -> None:
        # Default is safe value 1
        s_default = Settings()
        assert s_default.asr_max_concurrency == 1

        # Valid override
        s_override = Settings(asr_max_concurrency=4)
        assert s_override.asr_max_concurrency == 4

        # Invalid value 0 rejected
        with pytest.raises(ValueError, match="ASR_MAX_CONCURRENCY must be at least 1"):
            Settings(asr_max_concurrency=0)

        # Invalid negative value rejected
        with pytest.raises(ValueError, match="ASR_MAX_CONCURRENCY must be at least 1"):
            Settings(asr_max_concurrency=-1)

    def test_future_provider_raises_not_implemented_in_stage1(self) -> None:
        settings_asr = Settings(asr_provider="mlx_whisper")
        reg_asr = ProviderRegistry(settings_asr)
        with pytest.raises(ProviderNotImplementedError, match="Stage 1"):
            _ = reg_asr.asr

        # Faster-Whisper is no longer a supported provider (Apple Silicon MLX only)
        with pytest.raises(ValueError, match="ASR_PROVIDER must be one of"):
            Settings(asr_provider="faster_whisper")

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

    @pytest.mark.asyncio
    async def test_asr_initialization_failure_after_partial_allocation(self) -> None:
        """
        Verify that if ASR initialization fails after allocating partial resources,
        ASR is tracked immediately and its shutdown() is called to release resources.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        class PartiallyAllocatingASR(MockASRProvider):
            def __init__(self) -> None:
                super().__init__()
                self.allocated_resource: bool = False

            async def initialize(self) -> None:
                self.allocated_resource = True
                raise RuntimeError("ASR failed after partial resource allocation")

            async def shutdown(self) -> None:
                await super().shutdown()
                self.allocated_resource = False

        failing_asr = PartiallyAllocatingASR()
        registry._asr = failing_asr

        with pytest.raises(RuntimeError, match="ASR failed after partial resource allocation"):
            await registry.initialize_all()

        assert not registry.is_initialized
        assert failing_asr.is_shutdown
        assert not failing_asr.allocated_resource
        assert failing_asr.shutdown_calls == 1

    @pytest.mark.asyncio
    async def test_asr_warmup_failure_after_successful_initialization(self) -> None:
        """
        Verify that if ASR initialize() succeeds but warmup() fails,
        ASR is cleaned up via shutdown() and the error is propagated.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        class FailingWarmupASR(MockASRProvider):
            async def warmup(self) -> None:
                raise RuntimeError("ASR warmup model weights verification failed")

        failing_asr = FailingWarmupASR()
        registry._asr = failing_asr

        with pytest.raises(RuntimeError, match="ASR warmup model weights verification failed"):
            await registry.initialize_all()

        assert not registry.is_initialized
        assert failing_asr.initialize_calls == 1
        assert failing_asr.is_shutdown
        assert failing_asr.shutdown_calls == 1

    @pytest.mark.asyncio
    async def test_tts_warmup_failure_after_asr_has_initialized(self) -> None:
        """
        Verify that if TTS warmup() fails after ASR has initialized & warmed up,
        both TTS and ASR are shut down in reverse order (TTS then ASR).
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        class FailingWarmupTTS(MockTTSProvider):
            async def warmup(self) -> None:
                raise RuntimeError("TTS voice synthesis warmup failed")

        failing_tts = FailingWarmupTTS()
        registry._tts = failing_tts

        shutdown_order: list[str] = []
        orig_asr_shutdown = registry.asr.shutdown
        orig_tts_shutdown = failing_tts.shutdown

        async def asr_sd() -> None:
            shutdown_order.append("asr")
            await orig_asr_shutdown()

        async def tts_sd() -> None:
            shutdown_order.append("tts")
            await orig_tts_shutdown()

        registry.asr.shutdown = asr_sd  # type: ignore[method-assign]
        failing_tts.shutdown = tts_sd  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="TTS voice synthesis warmup failed"):
            await registry.initialize_all()

        assert not registry.is_initialized
        assert shutdown_order == ["tts", "asr"]
        assert registry.asr.is_shutdown  # type: ignore[attr-defined]
        assert failing_tts.is_shutdown

    @pytest.mark.asyncio
    async def test_llm_warmup_failure_after_asr_and_tts_initialized(self) -> None:
        """
        Verify that if LLM warmup() fails after ASR and TTS have both initialized,
        all three are rolled back in reverse order: LLM -> TTS -> ASR.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        class FailingWarmupLLM(MockLLMProvider):
            async def warmup(self) -> None:
                raise RuntimeError("LLM context warmup failed")

        failing_llm = FailingWarmupLLM()
        registry._llm = failing_llm

        shutdown_order: list[str] = []
        orig_asr_shutdown = registry.asr.shutdown
        orig_tts_shutdown = registry.tts.shutdown
        orig_llm_shutdown = failing_llm.shutdown

        async def asr_sd() -> None:
            shutdown_order.append("asr")
            await orig_asr_shutdown()

        async def tts_sd() -> None:
            shutdown_order.append("tts")
            await orig_tts_shutdown()

        async def llm_sd() -> None:
            shutdown_order.append("llm")
            await orig_llm_shutdown()

        registry.asr.shutdown = asr_sd  # type: ignore[method-assign]
        registry.tts.shutdown = tts_sd  # type: ignore[method-assign]
        failing_llm.shutdown = llm_sd  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="LLM context warmup failed"):
            await registry.initialize_all()

        assert not registry.is_initialized
        assert shutdown_order == ["llm", "tts", "asr"]
        assert registry.asr.is_shutdown  # type: ignore[attr-defined]
        assert registry.tts.is_shutdown  # type: ignore[attr-defined]
        assert failing_llm.is_shutdown

    @pytest.mark.asyncio
    async def test_multiple_cleanup_failures_preserves_original_initialization_error(
        self,
    ) -> None:
        """
        Verify that if multiple providers raise exceptions during rollback,
        cleanup is still attempted for all providers, the original initialization
        exception is preserved and re-raised, and failed providers remain recorded.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        class CrashingTTS(MockTTSProvider):
            async def shutdown(self) -> None:
                raise RuntimeError("TTS failed to release audio device")

        class CrashingASR(MockASRProvider):
            async def shutdown(self) -> None:
                raise RuntimeError("ASR failed to release model handle")

        class FailingInitLLM(MockLLMProvider):
            async def initialize(self) -> None:
                raise ValueError("Original LLM initialization error")

        asr = CrashingASR()
        tts = CrashingTTS()
        llm = FailingInitLLM()

        registry._asr = asr
        registry._tts = tts
        registry._llm = llm

        with pytest.raises(ValueError, match="Original LLM initialization error"):
            await registry.initialize_all()

        assert not registry.is_initialized
        # Failed providers are retained in _initialized_providers in canonical startup order for retry
        assert [id(p) for p in registry._initialized_providers] == [
            id(asr),
            id(tts),
        ]

    @pytest.mark.asyncio
    async def test_shutdown_failure_followed_by_successful_retry(self) -> None:
        """
        Verify that if a provider fails shutdown, the failure is raised and the provider
        is retained so that a subsequent shutdown_all() retries and cleanly succeeds.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)
        await registry.initialize_all()

        fail_shutdown = True

        orig_asr_shutdown = registry.asr.shutdown

        async def flaky_asr_shutdown() -> None:
            if fail_shutdown:
                raise RuntimeError("Transient lock during ASR shutdown")
            await orig_asr_shutdown()

        registry.asr.shutdown = flaky_asr_shutdown  # type: ignore[method-assign]

        # First shutdown attempt fails due to ASR
        with pytest.raises(RuntimeError, match="Transient lock during ASR shutdown"):
            await registry.shutdown_all()

        # TTS and LLM succeeded shutdown, but ASR is retained for retry
        assert not registry.is_initialized
        assert registry.asr in registry._initialized_providers
        assert registry.tts not in registry._initialized_providers
        assert registry.llm not in registry._initialized_providers

        # Fix condition and retry shutdown
        fail_shutdown = False
        await registry.shutdown_all()

        assert not registry.is_initialized
        assert registry._initialized_providers == []
        assert registry.asr.is_shutdown  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_concurrent_initialize_and_shutdown_calls(self) -> None:
        """
        Verify that concurrent initialize_all and shutdown_all operations are
        serialized cleanly via lock without deadlock or inconsistent state.
        """
        settings = Settings()
        registry = ProviderRegistry(settings)

        # Interleave 10 initialize and shutdown operations
        tasks = []
        for i in range(10):
            if i % 2 == 0:
                tasks.append(registry.initialize_all())
            else:
                tasks.append(registry.shutdown_all())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # All tasks should complete without throwing unexpected exceptions
        for r in results:
            assert not isinstance(r, Exception), f"Concurrent task failed: {r}"

        # Clean final state via explicit shutdown
        await registry.shutdown_all()
        assert not registry.is_initialized
        assert registry._initialized_providers == []

    @pytest.mark.asyncio
    async def test_multiple_providers_fail_shutdown_retried_in_reverse_startup_order(
        self,
    ) -> None:
        """
        Verify that when multiple providers fail during normal shutdown:
        1. The initial shutdown attempts all providers in reverse startup order (VAD -> LLM -> TTS -> ASR).
        2. The successfully shut down providers are not retried.
        3. The retry attempts only the failed providers, in reverse startup order (not startup order).
        """
        settings = Settings(vad_provider="mock")
        registry = ProviderRegistry(settings)
        await registry.initialize_all()

        call_events: list[str] = []

        fail_llm = True
        fail_asr = True

        orig_asr_sd = registry.asr.shutdown
        orig_tts_sd = registry.tts.shutdown
        orig_llm_sd = registry.llm.shutdown
        orig_vad_sd = registry.vad.shutdown  # type: ignore[union-attr]

        async def logging_vad_sd() -> None:
            call_events.append("vad_1")
            await orig_vad_sd()

        async def logging_llm_sd() -> None:
            call_events.append("llm_1" if fail_llm else "llm_2")
            if fail_llm:
                raise RuntimeError("LLM shutdown transient failure")
            await orig_llm_sd()

        async def logging_tts_sd() -> None:
            call_events.append("tts_1")
            await orig_tts_sd()

        async def logging_asr_sd() -> None:
            call_events.append("asr_1" if fail_asr else "asr_2")
            if fail_asr:
                raise RuntimeError("ASR shutdown transient failure")
            await orig_asr_sd()

        registry.vad.shutdown = logging_vad_sd  # type: ignore[union-attr,method-assign]
        registry.llm.shutdown = logging_llm_sd  # type: ignore[method-assign]
        registry.tts.shutdown = logging_tts_sd  # type: ignore[method-assign]
        registry.asr.shutdown = logging_asr_sd  # type: ignore[method-assign]

        # 1. First shutdown attempt: all 4 are attempted in reverse startup order
        with pytest.raises(RuntimeError, match="LLM shutdown transient failure"):
            await registry.shutdown_all()

        # Observed order on first shutdown: VAD -> LLM -> TTS -> ASR
        assert call_events == ["vad_1", "llm_1", "tts_1", "asr_1"]

        # VAD and TTS succeeded and must NOT be retained
        # ASR and LLM failed and must be retained in canonical startup order: [ASR, LLM]
        assert [id(p) for p in registry._initialized_providers] == [
            id(registry.asr),
            id(registry.llm),
        ]
        assert not registry.is_initialized

        # 2. Retry shutdown: fix transient errors
        fail_llm = False
        fail_asr = False
        call_events.clear()

        await registry.shutdown_all()

        # Observed order on retry: LLM -> ASR (reverse startup order, NOT startup order!)
        assert call_events == ["llm_2", "asr_2"]
        # VAD and TTS were not retried
        assert "vad_1" not in call_events
        assert "vad_2" not in call_events
        assert "tts_1" not in call_events
        assert "tts_2" not in call_events

        # Clean final state
        assert registry._initialized_providers == []
        assert not registry.is_initialized

    @pytest.mark.asyncio
    async def test_multiple_providers_fail_startup_rollback_retried_in_reverse_startup_order(
        self,
    ) -> None:
        """
        Verify that when multiple providers fail during startup rollback:
        1. Initial rollback attempts all attempted providers in reverse startup order.
        2. Retained failed providers are stored in canonical startup order.
        3. A subsequent shutdown_all() retries them in reverse startup order.
        4. Successfully rolled-back providers are not retried.
        """
        settings = Settings(vad_provider="mock")
        registry = ProviderRegistry(settings)

        call_events: list[str] = []

        fail_llm_shutdown = True
        fail_asr_shutdown = True

        class FailingVAD(MockVADProvider):
            async def initialize(self) -> None:
                raise RuntimeError("VAD initialization failed")

        class LoggingASR(MockASRProvider):
            async def shutdown(self) -> None:
                call_events.append("asr_1" if fail_asr_shutdown else "asr_2")
                if fail_asr_shutdown:
                    raise RuntimeError("ASR rollback failure")
                await super().shutdown()

        class LoggingTTS(MockTTSProvider):
            async def shutdown(self) -> None:
                call_events.append("tts_1")
                await super().shutdown()

        class LoggingLLM(MockLLMProvider):
            async def shutdown(self) -> None:
                call_events.append("llm_1" if fail_llm_shutdown else "llm_2")
                if fail_llm_shutdown:
                    raise RuntimeError("LLM rollback failure")
                await super().shutdown()

        asr = LoggingASR()
        tts = LoggingTTS()
        llm = LoggingLLM()
        vad = FailingVAD()

        registry._asr = asr
        registry._tts = tts
        registry._llm = llm
        registry._vad = vad

        # 1. Startup fails at VAD
        with pytest.raises(RuntimeError, match="VAD initialization failed"):
            await registry.initialize_all()

        # VAD failed in initialize, so attempted_providers in startup order is: [asr, tts, llm, vad]
        # Rollback order is: vad -> llm -> tts -> asr
        # vad (MockVADProvider) shutdown succeeds
        # llm shutdown fails (appends llm_1)
        # tts shutdown succeeds (appends tts_1)
        # asr shutdown fails (appends asr_1)
        assert call_events == ["llm_1", "tts_1", "asr_1"]

        # Retained providers must be stored in canonical startup order: [asr, llm]
        assert [id(p) for p in registry._initialized_providers] == [
            id(asr),
            id(llm),
        ]
        assert not registry.is_initialized

        # 2. Retry shutdown
        fail_llm_shutdown = False
        fail_asr_shutdown = False
        call_events.clear()

        await registry.shutdown_all()

        # Retry must execute in reverse startup order: llm then asr
        assert call_events == ["llm_2", "asr_2"]

        assert registry._initialized_providers == []
        assert not registry.is_initialized
