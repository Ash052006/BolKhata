"""
SQLAlchemy ORM models for the append-only Kirana Ledger event store.

Enforces:
- Append-only event immutability: transactions are never deleted or updated in place.
- Unique idempotency keys to eliminate double-posting on client retries.
- Compensating undo events for reversals.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bolkhata.common.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Customer(Base):
    """Customer entity with normalized search keys."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    events: Mapped[list[LedgerEvent]] = relationship(
        "LedgerEvent", back_populates="customer", cascade="all"
    )


class LedgerEvent(Base):
    """
    Append-only immutable transaction event.

    Types:
    - credit_sale (udhaar / credit purchase)
    - payment_received (jama / payment received)
    - cash_sale (nagad / immediate cash purchase)
    - expense (kharcha / store operating cost)
    - compensation_undo (compensating reversal of a previous event)
    """

    __tablename__ = "ledger_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    items: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_str: Mapped[str] = mapped_column(String(32), default="aaj", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Unique idempotency constraint preventing duplicate records
    idempotency_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # Audit & provenance metadata (rules vs llm)
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Reversal / compensation metadata
    compensated_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_compensated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )

    customer: Mapped[Customer | None] = relationship("Customer", back_populates="events")


# Composite indexes for high-speed balance and timeline queries
Index("ix_ledger_events_cust_created", LedgerEvent.customer_id, LedgerEvent.created_at)
