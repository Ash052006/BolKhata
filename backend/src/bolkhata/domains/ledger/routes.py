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

import csv
import io
import uuid
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bolkhata.common.db import get_db_session
from bolkhata.domains.ledger.ageing import (
    get_all_customers_ageing,
    query_customer_debt_age,
    query_overdue_customers,
)
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent
from bolkhata.domains.ledger.explainability import get_entry_explanation
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.pack import LedgerDomainPack
from bolkhata.domains.ledger.parser import parse_ledger_rules
from bolkhata.domains.ledger.pipeline import extract_ledger_intent
from bolkhata.domains.ledger.queries import (
    query_customer_balance,
    query_last_payment,
    query_today_collection,
    query_today_udhaar,
    query_top_debtors,
)
from bolkhata.domains.ledger.reminders import draft_customer_reminder
from bolkhata.domains.ledger.resolver import (
    CustomerRecord,
    CustomerResolver,
    normalize_customer_name,
)

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------


class UtteranceRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw transcription text")
    client_turn_id: str | None = Field(
        default=None, description="Optional turn token for idempotency"
    )


class LedgerQueryRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Query text")
    quiet_mode: bool = Field(
        default=False, description="Whether to suppress spoken audio for privacy"
    )


class ReminderDraftRequest(BaseModel):
    tone: str = Field(default="neutral", description="Reminder tone: gentle, neutral, or firm")
    language: str = Field(default="hi", description="Message language: hi or en")
    cooldown_days: int = Field(default=3, description="Cooldown days for repeat reminder warning")


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


@router.post("/query")
async def execute_voice_query(
    payload: LedgerQueryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Execute a voice query against the ledger (balance, today's totals, top debtors, last payment).
    Answers are computed deterministically via SQL. LLM is never used for arithmetic.
    """
    rule_intent = parse_ledger_rules(payload.text)
    intent_name = rule_intent.name if rule_intent else "query_balance"

    if intent_name == "query_today_udhaar":
        return await query_today_udhaar(session, quiet_mode=payload.quiet_mode)
    elif intent_name == "query_today_collection":
        return await query_today_collection(session, quiet_mode=payload.quiet_mode)
    elif intent_name == "query_top_debtors":
        return await query_top_debtors(session, quiet_mode=payload.quiet_mode)
    elif intent_name == "query_last_payment":
        target_cust = (rule_intent.customer if rule_intent else None) or payload.text.replace(
            "last payment", ""
        ).strip()
        return await query_last_payment(session, target_cust, quiet_mode=payload.quiet_mode)
    elif intent_name == "query_debt_age":
        target_cust = (rule_intent.customer if rule_intent else None) or payload.text
        return await query_customer_debt_age(session, target_cust, quiet_mode=payload.quiet_mode)
    elif intent_name == "query_overdue_list":
        return await query_overdue_customers(session, min_days=30, quiet_mode=payload.quiet_mode)
    elif intent_name == "set_do_not_remind":
        target_name = (rule_intent.customer if rule_intent else None) or payload.text
        all_cust_q = await session.execute(select(Customer))
        db_customers = all_cust_q.scalars().all()
        records = [CustomerRecord(id=c.id, name=c.name, phone=c.phone) for c in db_customers]
        resolver = CustomerResolver(records)
        res = await resolver.resolve(target_name)
        if res.is_resolved and res.resolved_id:
            target_c = next(c for c in db_customers if c.id == res.resolved_id)
            target_c.do_not_remind = True
            await session.commit()
            return {
                "query_type": "set_do_not_remind",
                "status": "success",
                "customer_name": target_c.name,
                "display_text": f"{target_c.name} ke liye payment reminder band kar diya gaya.",
                "spoken_text": None
                if payload.quiet_mode
                else f"Theek hai, {target_c.name} ko aage se koi reminder nahi jayega.",
                "quiet_mode": payload.quiet_mode,
            }
        return {
            "query_type": "set_do_not_remind",
            "status": "not_found",
            "display_text": f"Customer '{target_name}' nahi mila.",
            "spoken_text": None
            if payload.quiet_mode
            else f"{target_name} naam ka customer nahi mila.",
            "quiet_mode": payload.quiet_mode,
        }
    else:
        target_cust = (rule_intent.customer if rule_intent else None) or payload.text.replace(
            "balance", ""
        ).strip()
        return await query_customer_balance(session, target_cust, quiet_mode=payload.quiet_mode)


@router.get("/ageing")
async def get_ledger_ageing_report(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    """Return FIFO debt ageing report across all customers."""
    ageing_list = await get_all_customers_ageing(session)
    return [
        {
            "customer_id": a.customer_id,
            "customer_name": a.customer_name,
            "total_balance": a.total_balance,
            "bucket_0_7": a.bucket_0_7,
            "bucket_8_30": a.bucket_8_30,
            "bucket_31_60": a.bucket_31_60,
            "bucket_60_plus": a.bucket_60_plus,
            "oldest_due_days": a.oldest_due_days,
        }
        for a in ageing_list
    ]


# ---------------------------------------------------------------------------
# Feature F4: WhatsApp Reminder Drafts & Guardrails
# ---------------------------------------------------------------------------


@router.post("/customers/{customer_id}/reminder")
async def create_whatsapp_reminder(
    customer_id: str,
    payload: ReminderDraftRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Draft a pre-filled WhatsApp click-to-chat reminder link.
    The app generates a draft only and never sends messages automatically.
    """
    try:
        return await draft_customer_reminder(
            session=session,
            customer_id=customer_id,
            tone=payload.tone,
            language=payload.language,
            cooldown_days=payload.cooldown_days,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/customers/{customer_id}/do-not-remind")
async def toggle_do_not_remind(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    enabled: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    """Toggle the per-customer 'do_not_remind' opt-out flag."""
    cust_q = await session.execute(select(Customer).where(Customer.id == customer_id))
    cust = cust_q.scalar_one_or_none()
    if cust is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found.",
        )
    cust.do_not_remind = enabled
    await session.commit()
    return {
        "customer_id": customer_id,
        "customer_name": cust.name,
        "do_not_remind": cust.do_not_remind,
    }


# ---------------------------------------------------------------------------
# Feature F5: Explainability Panel & Redacted Diagnostics
# ---------------------------------------------------------------------------


@router.get("/entries/{entry_id}/explain")
async def explain_ledger_entry(
    entry_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Retrieve stage-by-stage explainability breakdown for a ledger event."""
    try:
        exp = await get_entry_explanation(session, entry_id)
        return asdict(exp)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/entries/{entry_id}/explain/redacted")
async def export_redacted_explanation(
    entry_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Export PII-redacted JSON diagnostics for bug tracking and review."""
    try:
        exp = await get_entry_explanation(session, entry_id)
        return exp.to_redacted_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# ---------------------------------------------------------------------------
# Feature F6: Data Ownership, Export & Privacy Erasure
# ---------------------------------------------------------------------------


@router.get("/export/csv")
async def export_ledger_csv(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """Export the entire ledger as a standard CSV file."""
    events_q = await session.execute(
        select(LedgerEvent, Customer.name.label("customer_name"))
        .outerjoin(Customer, LedgerEvent.customer_id == Customer.id)
        .order_by(LedgerEvent.created_at)
    )
    rows = events_q.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Event ID",
            "Date",
            "Event Type",
            "Customer Name",
            "Amount (INR)",
            "Items",
            "Notes",
            "Is Compensated",
            "Idempotency Key",
        ]
    )

    for ev, cust_name in rows:
        writer.writerow(
            [
                ev.id,
                ev.created_at.isoformat(),
                ev.event_type,
                cust_name or "N/A",
                f"{ev.amount:.2f}",
                ", ".join(ev.items) if ev.items else "",
                ev.notes or "",
                ev.is_compensated,
                ev.idempotency_key,
            ]
        )

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bolkhata_ledger.csv"'},
    )


@router.get("/export/json")
async def export_ledger_json(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Export complete ledger data backup in JSON format."""
    cust_q = await session.execute(select(Customer).order_by(Customer.created_at))
    customers = cust_q.scalars().all()

    evt_q = await session.execute(select(LedgerEvent).order_by(LedgerEvent.created_at))
    events = evt_q.scalars().all()

    return {
        "version": "1.0",
        "exported_at": uuid.uuid4().hex[:8],
        "customers": [
            {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "created_at": c.created_at.isoformat(),
            }
            for c in customers
        ],
        "events": [
            {
                "id": e.id,
                "customer_id": e.customer_id,
                "event_type": e.event_type,
                "amount": e.amount,
                "currency": e.currency,
                "items": e.items,
                "quantity": e.quantity,
                "unit": e.unit,
                "notes": e.notes,
                "is_compensated": e.is_compensated,
                "idempotency_key": e.idempotency_key,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/customers/{customer_id}/statement")
async def get_customer_statement(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Generate printable statement of account for a specific customer."""
    cust_q = await session.execute(select(Customer).where(Customer.id == customer_id))
    cust = cust_q.scalar_one_or_none()
    if cust is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found.",
        )

    evt_q = await session.execute(
        select(LedgerEvent)
        .where(LedgerEvent.customer_id == customer_id)
        .order_by(LedgerEvent.created_at)
    )
    events = evt_q.scalars().all()

    running_bal = 0.0
    transactions: list[dict[str, Any]] = []

    for e in events:
        if not e.is_compensated:
            if e.event_type in ("add_credit_sale", "credit_sale"):
                running_bal += e.amount
            elif e.event_type == "payment_received":
                running_bal -= e.amount
            elif e.event_type == "compensation_undo":
                running_bal += e.amount

        transactions.append(
            {
                "id": e.id,
                "date": e.created_at.strftime("%Y-%m-%d %H:%M"),
                "event_type": e.event_type,
                "amount": e.amount,
                "items": e.items,
                "is_compensated": e.is_compensated,
                "running_balance": round(running_bal, 2),
            }
        )

    return {
        "statement_title": f"BolKhata Statement - {cust.name}",
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "phone": cust.phone,
        },
        "total_outstanding_balance": round(running_bal, 2),
        "total_transactions": len(transactions),
        "transactions": transactions,
    }


@router.delete("/customers/{customer_id}", status_code=status.HTTP_200_OK)
async def delete_customer_data(
    customer_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Erase customer personal data per DPDP Act Right to Erasure (ADR 0006).
    Scrubs name and phone number in place while preserving append-only financial audit records.
    """
    cust_q = await session.execute(select(Customer).where(Customer.id == customer_id))
    cust = cust_q.scalar_one_or_none()
    if cust is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found.",
        )

    # Anonymize PII
    cust.name = "Deleted Customer"
    cust.normalized_name = f"deleted_{cust.id[:8]}"
    cust.phone = None

    # Scrub notes on associated ledger events
    evts_q = await session.execute(
        select(LedgerEvent).where(LedgerEvent.customer_id == customer_id)
    )
    for ev in evts_q.scalars().all():
        ev.notes = "[Customer PII erased per DPDP Act]"

    await session.commit()
    return {
        "status": "anonymized",
        "message": f"Customer '{customer_id}' personal data has been erased. Financial audit ledger preserved.",
        "customer_id": customer_id,
    }


@router.delete("/data", status_code=status.HTTP_200_OK)
async def wipe_all_data(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    confirm: Annotated[
        bool, Query(description="Explicit confirmation flag required to wipe all data")
    ] = False,
) -> dict[str, Any]:
    """
    Wipe all ledger transactions and customer records.
    Requires explicit confirm=True query parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safety guard: confirm=true must be explicitly passed to wipe all data.",
        )

    await session.execute(delete(LedgerEvent))
    await session.execute(delete(Customer))
    await session.commit()

    return {
        "status": "wiped",
        "message": "All customer records and ledger events have been permanently deleted.",
    }
