"""
API routes for the Kirana Ledger domain.

Provides endpoints for:
- POST /api/v1/ledger/utterance: Spoken utterance parsing, entity resolution, and read-back generation
- POST /api/v1/ledger/entries: Idempotent ledger entry recording and compensating undo
- GET /api/v1/ledger/entries: Transaction history listing
- GET /api/v1/ledger/customers: Customer directory with calculated balances
- GET /api/v1/ledger/customers/{id}/balance: Individual customer balance audit
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.pack import LedgerDomainPack
from bolkhata.domains.ledger.pipeline import extract_ledger_intent
from bolkhata.domains.ledger.resolver import CustomerRecord, normalize_customer_name

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------


class UtteranceRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw transcription text")
    client_turn_id: str | None = Field(
        default=None, description="Optional turn token for idempotency"
    )


class UtteranceResponse(BaseModel):
    intent: LedgerIntent
    action: dict[str, Any] | None
    resolution: dict[str, Any] | None
    read_back: str


class CreateEntryRequest(BaseModel):
    action_type: str
    amount: float
    currency: str = "INR"
    customer_id: str | None = None
    customer_name: str | None = None
    items: list[str] = Field(default_factory=list)
    quantity: float | None = None
    unit: str | None = None
    date: str = "aaj"
    notes: str | None = None
    idempotency_key: str
    provenance: dict[str, Any] = Field(default_factory=dict)


class LedgerEntryResponse(BaseModel):
    id: str
    event_type: str
    amount: float
    currency: str
    customer_id: str | None
    customer_name: str | None
    items: list[str] | None
    quantity: float | None
    unit: str | None
    date_str: str
    notes: str | None
    idempotency_key: str
    is_compensated: bool
    created_at: str


class CustomerSummaryResponse(BaseModel):
    id: str
    name: str
    phone: str | None
    balance: float
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_all_customers(session: AsyncSession) -> list[CustomerRecord]:
    result = await session.execute(select(Customer))
    rows = result.scalars().all()
    return [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in rows]


def _format_event_response(
    event: LedgerEvent, customer_name: str | None = None
) -> LedgerEntryResponse:
    c_name = customer_name
    if c_name is None:
        cust_obj = event.__dict__.get("customer")
        if cust_obj is not None and hasattr(cust_obj, "name"):
            c_name = str(cust_obj.name)
    return LedgerEntryResponse(
        id=event.id,
        event_type=event.event_type,
        amount=event.amount,
        currency=event.currency,
        customer_id=event.customer_id,
        customer_name=c_name,
        items=event.items,
        quantity=event.quantity,
        unit=event.unit,
        date_str=event.date_str,
        notes=event.notes,
        idempotency_key=event.idempotency_key,
        is_compensated=event.is_compensated,
        created_at=event.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/utterance", response_model=UtteranceResponse)
async def process_utterance(
    payload: UtteranceRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UtteranceResponse:
    """Process spoken utterance text through rules/LLM pipeline and generate read-back."""
    existing_customers = await _get_all_customers(session)
    pack = LedgerDomainPack(existing_customers)

    # Optional LLM from provider registry
    llm_provider = None
    if hasattr(request.app.state, "registry") and request.app.state.registry is not None:
        try:
            llm_provider = request.app.state.registry.get_llm_provider()
        except Exception:
            llm_provider = None

    intent = await extract_ledger_intent(payload.text, llm_provider)

    # Customer resolution
    resolution_data: dict[str, Any] | None = None
    resolved_cust_id: str | None = None

    if intent.customer:
        res = await pack.resolver.resolve(intent.customer)
        resolution_data = res.model_dump()
        if res.is_resolved:
            resolved_cust_id = res.resolved_id
            intent.customer = res.resolved_name

    turn_id = payload.client_turn_id or str(uuid.uuid4())[:8]
    action = pack.create_action(intent, customer_id=resolved_cust_id, client_turn_id=turn_id)
    read_back = (
        pack.format_read_back(action) if action else "Maaf kijiye, samajh nahi aaya. Dobara boliye?"
    )

    return UtteranceResponse(
        intent=intent,
        action=action.model_dump() if action else None,
        resolution=resolution_data,
        read_back=read_back,
    )


@router.post("/entries", response_model=LedgerEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_ledger_entry(
    payload: CreateEntryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LedgerEntryResponse:
    """
    Append an immutable ledger event.

    Guarantees idempotency: retrying with the same idempotency_key returns the existing event.
    Undo actions insert a compensating transaction rather than deleting.
    """
    # 1. Check idempotency
    existing_q = await session.execute(
        select(LedgerEvent).where(LedgerEvent.idempotency_key == payload.idempotency_key)
    )
    existing_event = existing_q.scalar_one_or_none()
    if existing_event is not None:
        # Idempotent match -> return immediately
        return _format_event_response(existing_event)

    # 2. Customer resolution / creation
    cust_id = payload.customer_id
    cust_name = payload.customer_name

    if cust_id is None and cust_name:
        # Check if customer already exists by normalized name
        norm_name = normalize_customer_name(cust_name)
        c_q = await session.execute(select(Customer).where(Customer.normalized_name == norm_name))
        existing_cust = c_q.scalar_one_or_none()
        if existing_cust:
            cust_id = existing_cust.id
            cust_name = existing_cust.name
        else:
            new_cust = Customer(name=cust_name.strip(), normalized_name=norm_name)
            session.add(new_cust)
            await session.flush()
            cust_id = new_cust.id
            cust_name = new_cust.name

    # 3. Handle Undo Actions as Compensating Events
    if payload.action_type == "undo_last":
        # Find latest uncompensated event
        query = select(LedgerEvent).where(LedgerEvent.is_compensated.is_(False))
        if cust_id:
            query = query.where(LedgerEvent.customer_id == cust_id)
        query = query.order_by(desc(LedgerEvent.created_at)).limit(1)

        target_q = await session.execute(query)
        target_event = target_q.scalar_one_or_none()

        if target_event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No previous transaction found to undo.",
            )

        # Mark original as compensated
        target_event.is_compensated = True

        # Insert compensating event (both are marked is_compensated=True so neither counts in active balance)
        comp_event = LedgerEvent(
            customer_id=target_event.customer_id,
            event_type="compensation_undo",
            amount=-target_event.amount,
            currency=target_event.currency,
            items=target_event.items,
            quantity=target_event.quantity,
            unit=target_event.unit,
            date_str=payload.date,
            notes=f"Compensating undo for event {target_event.id}",
            idempotency_key=payload.idempotency_key,
            provenance=payload.provenance,
            compensated_event_id=target_event.id,
            is_compensated=True,
        )
        session.add(comp_event)
        await session.commit()
        await session.refresh(comp_event)
        return _format_event_response(comp_event, cust_name)

    # 4. Standard Append-Only Event Insertion
    event = LedgerEvent(
        customer_id=cust_id,
        event_type=payload.action_type,
        amount=payload.amount,
        currency=payload.currency,
        items=payload.items,
        quantity=payload.quantity,
        unit=payload.unit,
        date_str=payload.date,
        notes=payload.notes,
        idempotency_key=payload.idempotency_key,
        provenance=payload.provenance,
        is_compensated=False,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return _format_event_response(event, cust_name)


@router.get("/entries", response_model=list[LedgerEntryResponse])
async def list_ledger_entries(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    customer_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LedgerEntryResponse]:
    """List recent ledger events ordered chronologically descending."""
    query = select(LedgerEvent)
    if customer_id:
        query = query.where(LedgerEvent.customer_id == customer_id)
    query = query.order_by(desc(LedgerEvent.created_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    events = result.scalars().all()
    return [_format_event_response(e) for e in events]


@router.get("/customers", response_model=list[CustomerSummaryResponse])
async def list_customers(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CustomerSummaryResponse]:
    """List all customers with calculated balances (credit sales minus payments)."""
    cust_q = await session.execute(select(Customer).order_by(Customer.name))
    customers = cust_q.scalars().all()

    summaries: list[CustomerSummaryResponse] = []
    for c in customers:
        # Calculate balance from uncompensated events
        evt_q = await session.execute(
            select(LedgerEvent).where(
                LedgerEvent.customer_id == c.id,
                LedgerEvent.is_compensated.is_(False),
            )
        )
        evts = evt_q.scalars().all()
        balance = 0.0
        for e in evts:
            if e.event_type == "add_credit_sale":
                balance += e.amount
            elif e.event_type == "payment_received":
                balance -= e.amount
            elif e.event_type == "compensation_undo":
                balance += e.amount  # amount is already negative for undo of credit sale

        summaries.append(
            CustomerSummaryResponse(
                id=c.id,
                name=c.name,
                phone=c.phone,
                balance=balance,
                created_at=c.created_at.isoformat(),
            )
        )

    return summaries


@router.get("/customers/{customer_id}/balance")
async def get_customer_balance(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Get detailed balance audit breakdown for a customer."""
    cust_q = await session.execute(select(Customer).where(Customer.id == customer_id))
    cust = cust_q.scalar_one_or_none()
    if cust is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found.",
        )

    evt_q = await session.execute(
        select(LedgerEvent)
        .where(LedgerEvent.customer_id == customer_id, LedgerEvent.is_compensated.is_(False))
        .order_by(desc(LedgerEvent.created_at))
    )
    events = evt_q.scalars().all()

    total_credit = sum(e.amount for e in events if e.event_type == "add_credit_sale")
    total_paid = sum(e.amount for e in events if e.event_type == "payment_received")
    balance = total_credit - total_paid

    return {
        "customer_id": cust.id,
        "customer_name": cust.name,
        "balance": balance,
        "total_credit": total_credit,
        "total_paid": total_paid,
        "uncompensated_event_count": len(events),
    }
