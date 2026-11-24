"""
Domain pack dynamic discovery and dispatch framework.

Enforces the ADR 0002 / ADR 0004 boundary:
Nothing outside of bolkhata.domains may import directly from bolkhata.domains.ledger.
All application routes, pipelines, and services access active domain functionality
through this module.
"""

from __future__ import annotations

from fastapi import APIRouter

# Import active pack database models so Base.metadata is fully populated
import bolkhata.domains.ledger.db_models  # noqa: F401
from bolkhata.config.settings import settings
from bolkhata.domains.base import DomainAction, DomainIntent, DomainPack


def get_domain_pack(pack_name: str | None = None) -> DomainPack:
    """Instantiate and return the configured domain pack."""
    raw_name = pack_name or getattr(settings, "domain_pack", "ledger") or "ledger"
    name = str(raw_name).lower()
    if name == "ledger":
        from bolkhata.domains.ledger import LedgerDomainPack

        return LedgerDomainPack()
    else:
        raise ValueError(f"Unknown domain pack: '{name}'")


def get_domain_router(pack_name: str | None = None) -> APIRouter:
    """Return the FastAPI APIRouter for the configured domain pack."""
    raw_name = pack_name or getattr(settings, "domain_pack", "ledger") or "ledger"
    name = str(raw_name).lower()
    if name == "ledger":
        from bolkhata.domains.ledger import ledger_router

        return ledger_router
    else:
        raise ValueError(f"No router registered for domain pack: '{name}'")


__all__ = [
    "DomainAction",
    "DomainIntent",
    "DomainPack",
    "get_domain_pack",
    "get_domain_router",
]
