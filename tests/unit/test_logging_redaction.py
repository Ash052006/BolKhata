"""
Unit tests for the structured-logging redaction processor and end-to-end structlog pipeline.

Coverage
--------
* Sensitive keys are redacted at DEBUG, INFO, WARNING, and ERROR levels.
* Phone numbers embedded in string values are redacted.
* Raw bytes values are redacted recursively.
* Non-sensitive keys are passed through unchanged.
* Redaction fails closed: if redaction itself raises, the event is replaced
  by a safe sentinel and no sensitive data escapes.
* Context fields (session_id, turn_id, generation_id) survive redaction.
* Recursive nested mappings, lists, tuples, sets, and circular references.
* Exception messages, tracebacks, nested exceptions, and credentials in exc_info.
* End-to-end verification through real structlog logger emitting JSON to stdout.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

import pytest

from bolkhata.common.logging import (
    configure_logging,
    get_logger,
    redact_processor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _call(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Invoke the redact_processor with dummy logger/method args."""
    return redact_processor(None, "info", event_dict)


def _capture_log(fn: Any, log_level: str = "DEBUG") -> dict[str, Any]:
    """Execute fn(logger) and capture the emitted JSON log line."""
    stream = io.StringIO()
    configure_logging(log_level)
    logging.getLogger().handlers[0].stream = stream
    logger = get_logger("test_capture")
    fn(logger)
    raw = stream.getvalue().strip()
    assert raw, "No log line was emitted!"
    # Grab the last JSON line if multiple were logged
    last_line = raw.splitlines()[-1]
    return json.loads(last_line)


# ---------------------------------------------------------------------------
# Sensitive key redaction — all log levels
# ---------------------------------------------------------------------------


class TestSensitiveKeyRedaction:
    @pytest.mark.parametrize(
        "level",
        ["debug", "info", "warning", "error"],
    )
    def test_transcript_redacted_at_all_levels(self, level: str) -> None:
        result = _call({"event": "turn", "level": level, "transcript": "Sharma ji ko 250 rupaye"})
        assert result["transcript"] == "[REDACTED]"
        assert result["event"] == "turn"

    @pytest.mark.parametrize(
        "sensitive_key",
        [
            "customer_name",
            "customer",
            "phone",
            "phone_number",
            "secret",
            "password",
            "api_key",
            "token",
            "authorization",
            "credit_card",
        ],
    )
    def test_sensitive_key_redacted(self, sensitive_key: str) -> None:
        result = _call({"event": "request", sensitive_key: "super-secret-value"})
        assert result[sensitive_key] == "[REDACTED]"

    def test_non_sensitive_key_passes_through(self) -> None:
        result = _call({"event": "entry_saved", "amount": 250, "shop_id": "shop-42"})
        assert result["amount"] == 250
        assert result["shop_id"] == "shop-42"

    def test_multiple_sensitive_keys_all_redacted(self) -> None:
        result = _call(
            {
                "event": "auth",
                "password": "synthetic-test-password",  # pragma: allowlist secret
                "token": "eyJhbGc...",
                "user_id": "u-1",
            }
        )
        assert result["password"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"
        assert result["user_id"] == "u-1"


# ---------------------------------------------------------------------------
# Phone number pattern redaction
# ---------------------------------------------------------------------------


class TestPhoneRedaction:
    @pytest.mark.parametrize(
        ("value", "expected_contains_phone"),
        [
            ("call me at 9876543210 ok", False),
            ("contact: +919876543210", False),
            ("no numbers here", True),  # value is NOT a phone — passes through
            ("1234", True),  # too short — not a phone
        ],
    )
    def test_phone_number_in_string_value(self, value: str, expected_contains_phone: bool) -> None:
        result = _call({"event": "log", "note": value})
        assert ("[REDACTED]" in result["note"]) is not expected_contains_phone

    def test_ten_digit_phone_in_message(self) -> None:
        result = _call({"event": "9876543210 called", "info": "data"})
        assert "[REDACTED]" in result["event"]


# ---------------------------------------------------------------------------
# Bytes redaction
# ---------------------------------------------------------------------------


class TestBytesRedaction:
    def test_bytes_value_redacted(self) -> None:
        raw_audio = b"\x00\xff" * 100
        result = _call({"event": "audio_chunk", "audio": raw_audio})
        assert result["audio"] == "[REDACTED]"

    def test_bytearray_and_memoryview_redacted(self) -> None:
        ba = bytearray(b"raw-bytes")
        mv = memoryview(b"raw-memory")
        result = _call({"event": "audio", "ba": ba, "mv": mv})
        assert result["ba"] == "[REDACTED]"
        assert result["mv"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# Context fields survive redaction
# ---------------------------------------------------------------------------


class TestContextFieldsSurvive:
    def test_session_turn_generation_ids_pass_through(self) -> None:
        result = _call(
            {
                "event": "entry_saved",
                "session_id": "s-abc",
                "turn_id": "t-001",
                "generation_id": "g-xyz",
                "transcript": "sensitive text",
            }
        )
        assert result["session_id"] == "s-abc"
        assert result["turn_id"] == "t-001"
        assert result["generation_id"] == "g-xyz"
        assert result["transcript"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# Recursive nested structures & circular references
# ---------------------------------------------------------------------------


class TestRecursiveSanitization:
    def test_nested_dictionaries(self) -> None:
        payload = {
            "event": "transaction",
            "payload": {
                "customer_name": "Ramesh Kumar",
                "phone": "+919876543210",
                "nested_inner": {
                    "transcript": "Sharma ji ko udhaar",
                    "safe_amount": 500,
                },
            },
        }
        res = _call(payload)
        inner = res["payload"]
        assert inner["customer_name"] == "[REDACTED]"
        assert inner["phone"] == "[REDACTED]"
        assert inner["nested_inner"]["transcript"] == "[REDACTED]"
        assert inner["nested_inner"]["safe_amount"] == 500

    def test_nested_lists_and_tuples(self) -> None:
        payload = {
            "event": "batch",
            "customers": ["customer Ramesh", "9876543210"],
            "audio_buffers": [b"chunk1", b"chunk2"],
            "meta": (b"raw", "normal_text"),
        }
        res = _call(payload)
        assert res["customers"] == ["customer [REDACTED]", "[REDACTED]"]
        assert res["audio_buffers"] == ["[REDACTED]", "[REDACTED]"]
        assert res["meta"] == ("[REDACTED]", "normal_text")

    def test_circular_reference_handled_safely(self) -> None:
        a: dict[str, Any] = {"name": "test"}
        b: dict[str, Any] = {"a": a}
        a["b"] = b
        payload = {"event": "circular", "data": a}
        res = _call(payload)
        assert res["data"]["b"]["a"] == "[CIRCULAR]"

    def test_original_object_not_mutated(self) -> None:
        original = {"event": "test", "customer_name": "Ramesh", "items": ["9876543210"]}
        _call(original)
        assert original["customer_name"] == "Ramesh"
        assert original["items"] == ["9876543210"]


# ---------------------------------------------------------------------------
# End-to-end structlog logger tests across all levels
# ---------------------------------------------------------------------------


class TestEndToEndLogger:
    @pytest.mark.parametrize("level", ["debug", "info", "warning", "error"])
    def test_end_to_end_logger_levels(self, level: str) -> None:
        def log_action(logger: Any) -> None:
            fn = getattr(logger, level)
            fn("test_event", customer_name="Ramesh", phone="9876543210", amount=100)

        record = _capture_log(log_action, log_level="DEBUG")
        assert record["level"] == level
        assert record["customer_name"] == "[REDACTED]"
        assert record["phone"] == "[REDACTED]"
        assert record["amount"] == 100

    def test_nested_audio_and_dict_via_logger(self) -> None:
        def log_action(logger: Any) -> None:
            logger.info(
                "voice_turn",
                payload={"transcript": "Sharma ji", "audio": [b"pcm_bytes"]},
            )

        record = _capture_log(log_action)
        assert record["payload"]["transcript"] == "[REDACTED]"
        assert record["payload"]["audio"] == ["[REDACTED]"]


# ---------------------------------------------------------------------------
# Exception & exc_info sanitization tests
# ---------------------------------------------------------------------------


class TestExceptionSanitization:
    def test_value_error_with_customer_and_phone(self) -> None:
        def log_action(logger: Any) -> None:
            try:
                raise ValueError("Failed for customer Ramesh Kumar with phone 9876543210")
            except Exception as e:
                logger.error("customer_failed", exc_info=e)

        record = _capture_log(log_action)
        raw_str = json.dumps(record)
        assert "Ramesh Kumar" not in raw_str
        assert "9876543210" not in raw_str
        assert "customer [REDACTED]" in record["exception"]
        assert "[REDACTED]" in record["exception"]

    def test_nested_exception_chain(self) -> None:
        def log_action(logger: Any) -> None:
            try:
                try:
                    raise KeyError("secret_key_1234567890")
                except KeyError as cause:
                    raise RuntimeError("Failed processing phone +919876543210") from cause
            except Exception as e:
                logger.error("nested_failure", exc_info=e)

        record = _capture_log(log_action)
        raw_str = json.dumps(record)
        assert "+919876543210" not in raw_str
        assert "[REDACTED]" in record["exception"]

    def test_logger_exception_call(self) -> None:
        def log_action(logger: Any) -> None:
            try:
                raise ValueError("phone 9988776655 failed")
            except Exception:
                logger.exception("exception_logged")

        record = _capture_log(log_action)
        raw_str = json.dumps(record)
        assert "9988776655" not in raw_str
        assert "[REDACTED]" in record["exception"]

    def test_logger_error_exc_info_true(self) -> None:
        def log_action(logger: Any) -> None:
            try:
                raise ValueError("customer Suresh with phone 9123456789")
            except Exception:
                logger.error("error_logged", exc_info=True)

        record = _capture_log(log_action)
        raw_str = json.dumps(record)
        assert "9123456789" not in raw_str
        assert "customer [REDACTED]" in record["exception"]

    def test_exception_with_api_tokens(self) -> None:
        # Synthetic JWT and API-key patterns to test logging redaction regex filters.
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakToken"  # pragma: allowlist secret
        api_key = "api_key=sk-secretKey999"  # pragma: allowlist secret

        def log_action(logger: Any) -> None:
            try:
                raise ValueError(f"Auth failure token: {token} and {api_key}")
            except Exception as e:
                logger.error("token_failed", exc_info=e)

        record = _capture_log(log_action)
        raw_str = json.dumps(record)
        assert "doNotLeakToken" not in raw_str
        assert "sk-secretKey999" not in raw_str
        assert "[REDACTED]" in record["exception"]


# ---------------------------------------------------------------------------
# Fail-closed: redaction error produces safe sentinel
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_redaction_failure_produces_sentinel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        When the redaction processor itself raises, sensitive data must not
        escape — the event dict is replaced by a safe sentinel.
        """
        from bolkhata.common import logging as log_mod

        # Patch sanitize_recursively so that it raises
        def _exploding(obj: Any, seen: Any = None) -> Any:
            raise RuntimeError("simulated redaction failure")

        monkeypatch.setattr(log_mod, "sanitize_recursively", _exploding)

        result = _call({"event": "turn", "transcript": "very sensitive data"})

        assert "very sensitive data" not in str(result)
        assert "REDACTION_FAILED" in result.get("event", "")
        assert "redaction_error" in result
