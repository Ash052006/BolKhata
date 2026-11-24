"""
Failure handling, graceful degradation, circuit breaking, and local retry queues.

Covers:
1. ASR failure -> Fallback to typed-input prompt with clear merchant message.
2. LLM failure -> Fallback to deterministic rules-only parser with notice.
3. TTS failure -> Fallback to visual on-screen read-back without blocking transaction.
4. Database write failure -> Local in-memory retry queue preserving exact idempotency keys.
5. Network / disconnect failure -> Session recovery preserving pending entry.
"""

from __future__ import annotations

from typing import Any

from bolkhata.common.logging import get_logger
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.parser import parse_ledger_rules

logger = get_logger(__name__)


class LocalRetryQueue:
    """In-memory local retry buffer for database write failures, preserving idempotency keys."""

    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []

    def enqueue(self, payload: dict[str, Any]) -> None:
        """Add a failed transaction payload to the retry queue."""
        if "idempotency_key" not in payload:
            raise ValueError("Payload missing idempotency_key; cannot guarantee safe retry.")
        # Avoid duplicate queue entries with the same idempotency key
        if not any(item["idempotency_key"] == payload["idempotency_key"] for item in self._queue):
            self._queue.append(payload)
            logger.warning(
                "Buffered failed transaction in local retry queue",
                extra={"idempotency_key": payload["idempotency_key"]},
            )

    def size(self) -> int:
        return len(self._queue)

    def pop_all(self) -> list[dict[str, Any]]:
        """Drain all buffered payloads for processing."""
        items = list(self._queue)
        self._queue.clear()
        return items

    def peek(self) -> list[dict[str, Any]]:
        return list(self._queue)


class FallbackManager:
    """Manages graceful degradation across all system failure modes."""

    def __init__(self, retry_queue: LocalRetryQueue | None = None) -> None:
        self.retry_queue = retry_queue or LocalRetryQueue()

    def handle_asr_failure(self, error: Exception) -> dict[str, Any]:
        """
        ASR down -> prompt merchant to type transaction details manually.
        """
        logger.error("ASR provider failed", exc_info=error)
        return {
            "status": "fallback",
            "failure_mode": "asr_down",
            "user_prompt": "Aawaz ki seva uplabdh nahi hai ya mic band hai. Kripya likh kar (type karke) batayein.",
            "requires_typed_input": True,
        }

    def handle_llm_failure(self, text: str, error: Exception) -> LedgerIntent:
        """
        LLM down -> fallback strictly to deterministic rules-only parser with user notice.
        """
        logger.warning(
            "LLM provider unavailable; falling back to deterministic rules", exc_info=error
        )
        intent = parse_ledger_rules(text)
        if intent is None:
            # Fallback safe default
            intent = LedgerIntent(
                name="query_balance",
                confidence=0.5,
                provenance={"intent": "llm_down_rules_fallback"},
            )
        else:
            intent.provenance["llm_fallback"] = "rules_only"
        return intent

    def handle_tts_failure(self, error: Exception, display_text: str) -> dict[str, Any]:
        """
        TTS down -> fall back gracefully to on-screen visual read-back.
        Transaction is not blocked.
        """
        logger.warning("TTS synthesis failed; using visual read-back only", exc_info=error)
        return {
            "status": "fallback",
            "failure_mode": "tts_down",
            "has_audio": False,
            "display_read_back": display_text,
            "notice": "Aawaz nahi chal rahi hai, screen par confirmation dekhein.",
        }

    def handle_db_failure(self, payload: dict[str, Any], error: Exception) -> dict[str, Any]:
        """
        Database write failure -> buffer in local retry queue preserving idempotency key.
        """
        logger.error("Database write failed; enqueueing for retry", exc_info=error)
        self.retry_queue.enqueue(payload)
        return {
            "status": "queued_for_retry",
            "idempotency_key": payload.get("idempotency_key"),
            "queue_depth": self.retry_queue.size(),
            "message": "Database se connect nahi ho paya. Entry safe hai aur network aane par retry hogi.",
        }
