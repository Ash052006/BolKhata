"""
Structured JSON logging with per-request context and recursive redaction.

Design decisions
----------------
* structlog is used for first-class JSON output and processor-chain composability.
* Redaction runs unconditionally on EVERY log level (not just INFO) so DEBUG
  output from noisy libraries never leaks sensitive data.
* Sanitization is RECURSIVE: nested dictionaries, mappings, lists, tuples, sets,
  Pydantic models, and raw audio bytes are sanitized at every nesting depth.
* Exception handling (exc_info) is sanitized so tracebacks and exception
  messages cannot leak customer names, phone numbers, or credentials.
* Circular references in nested objects are safely detected and replaced with [CIRCULAR].
* The redaction processor FAILS CLOSED: if an unexpected error occurs during redaction,
  the entire event dict is replaced with a safe sentinel value.
* Context fields (session_id, turn_id, generation_id) are stored in
  contextvars and automatically merged into every log record by
  structlog.contextvars.merge_contextvars.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

# ---------------------------------------------------------------------------
# Sensitive field names — redacted at every log level and nesting depth.
# ---------------------------------------------------------------------------
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "transcript",
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
    }
)

# Regex patterns for sensitive patterns inside strings.
_PHONE_RE = re.compile(r"\+?[0-9]{10,13}")
_JWT_RE = re.compile(r"\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\b")
_SECRET_KEY_RE = re.compile(
    r"(?i)\b(bearer\s+|token\s*[:=]\s*|api[_-]?key\s*[:=]\s*|secret\s*[:=]\s*|password\s*[:=]\s*)(['\"]?[^\s,'\"]+['\"]?)"
)
_CUSTOMER_RE = re.compile(
    r"(?i)\b(customer(?:\s+name)?(?:\s+is|\s*:|\s*=|\s+))([A-Za-z]+(?:\s+[A-Za-z]+)?)"
)
_URI_PASSWORD_RE = re.compile(r"://([^:]+):([^@]+)@")

_REDACTED = "[REDACTED]"
_CIRCULAR = "[CIRCULAR]"


def sanitize_string(val: str) -> str:
    """Sanitize sensitive patterns inside an arbitrary string."""
    s = _PHONE_RE.sub(_REDACTED, val)
    s = _JWT_RE.sub(_REDACTED, s)
    s = _SECRET_KEY_RE.sub(r"\1" + _REDACTED, s)
    s = _CUSTOMER_RE.sub(r"\1" + _REDACTED, s)
    s = _URI_PASSWORD_RE.sub(r"://\1:" + _REDACTED + "@", s)
    return s


def sanitize_recursively(obj: Any, seen: set[int] | None = None) -> Any:
    """
    Recursively sanitize objects, dictionaries, collections, and raw bytes.

    - Raw bytes, bytearrays, and memoryviews are always replaced with [REDACTED].
    - Mappings have sensitive keys redacted and remaining values sanitized recursively.
    - Collections (lists, tuples, sets) have elements sanitized recursively.
    - Pydantic models with model_dump() or dict() are dumped and sanitized.
    - Exceptions are stringified and sanitized.
    - Circular references are safely identified and broken.
    - Original objects are not modified in-place.
    """
    if seen is None:
        seen = set()

    # Raw bytes / audio chunks are never logged at any level.
    if isinstance(obj, bytes | bytearray | memoryview):
        return _REDACTED

    if isinstance(obj, str):
        return sanitize_string(obj)

    if isinstance(obj, int | float | bool) or obj is None:
        return obj

    # Pydantic models (v2 model_dump or v1 dict)
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return sanitize_recursively(obj.model_dump(), seen)
        except Exception:
            pass
    elif hasattr(obj, "dict") and callable(obj.dict):
        try:
            return sanitize_recursively(obj.dict(), seen)
        except Exception:
            pass

    obj_id = id(obj)
    if obj_id in seen:
        return _CIRCULAR

    if isinstance(obj, Mapping):
        seen_copy = seen | {obj_id}
        result_dict: dict[str, Any] = {}
        for k, v in obj.items():
            key_str = str(k)
            if key_str.lower() in _SENSITIVE_KEYS:
                result_dict[key_str] = _REDACTED
            else:
                result_dict[key_str] = sanitize_recursively(v, seen_copy)
        return result_dict

    if isinstance(obj, list | tuple | set | frozenset):
        seen_copy = seen | {obj_id}
        items = [sanitize_recursively(item, seen_copy) for item in obj]
        if isinstance(obj, tuple):
            return tuple(items)
        if isinstance(obj, set | frozenset):
            try:
                return type(obj)(items)
            except TypeError:
                return items
        return items

    if isinstance(obj, Exception):
        msg = sanitize_string(str(obj))
        return f"{type(obj).__name__}: {msg}"

    try:
        s = str(obj)
        sanitized = sanitize_string(s)
        return sanitized if sanitized != s else obj
    except Exception:
        return _REDACTED


def redact_processor(
    logger: WrappedLogger,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    structlog processor that scrubs sensitive data from every log record recursively.

    Fail-closed contract
    --------------------
    If ANY exception is raised during redaction, the entire event_dict is
    replaced with a safe sentinel and the error type recorded. Sensitive data
    never reaches any handler.
    """
    try:
        sanitized = sanitize_recursively(event_dict)
        if isinstance(sanitized, dict):
            return sanitized
        return {"event": str(sanitized)}
    except Exception as exc:
        return {
            "event": "[REDACTION_FAILED — original event suppressed]",
            "redaction_error": type(exc).__name__,
        }


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for JSON output. Call once at application startup.

    The processor chain:
      1. merge_contextvars   — injects session_id, turn_id, generation_id
      2. add_log_level       — adds "level" key
      3. add_logger_name     — adds "logger" key
      4. TimeStamper         — ISO-8601 timestamp
      5. format_exc_info     — formats exc_info into a traceback string
      6. redact_processor    — recursively scrubs sensitive data and tracebacks (fail-closed)
      7. JSONRenderer        — final JSON serialization
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        redact_processor,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for *name*."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


def bind_request_context(
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
    generation_id: str | None = None,
) -> None:
    """
    Bind per-request context into structlog's contextvars store.

    Call at the start of each request/session; these values are automatically
    merged into every subsequent log record for the life of the context.
    """
    ctx: dict[str, str] = {}
    if session_id is not None:
        ctx["session_id"] = session_id
    if turn_id is not None:
        ctx["turn_id"] = turn_id
    if generation_id is not None:
        ctx["generation_id"] = generation_id
    if ctx:
        structlog.contextvars.bind_contextvars(**ctx)


def clear_request_context() -> None:
    """Clear per-request context from structlog's contextvars store."""
    structlog.contextvars.clear_contextvars()
