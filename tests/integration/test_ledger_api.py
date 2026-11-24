"""
Integration tests for the Kirana Ledger API endpoints.

Tests:
- POST /api/v1/ledger/utterance: Spoken utterance parsing and read-back generation
- POST /api/v1/ledger/entries: Idempotent ledger entry creation
- Duplicate request prevention: Retrying with same idempotency_key returns identical record
- Compensating undo: Reversing a transaction inserts an undo event and adjusts balance to zero
- GET /api/v1/ledger/customers: Real-time balance calculations across credit and payments
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_process_utterance_endpoint(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/ledger/utterance",
        json={"text": "Ramesh ji ko dhai sau rupaye udhaar likho", "client_turn_id": "turn_001"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"]["name"] == "add_credit_sale"
    assert data["intent"]["amount"] == 250.0
    assert data["intent"]["customer"] == "Ramesh"
    assert "250 rupaye udhaar" in data["read_back"]
    assert data["action"]["action_type"] == "add_credit_sale"
    assert data["action"]["idempotency_key"] is not None


@pytest.mark.asyncio
async def test_create_ledger_entry_and_idempotency(client: AsyncClient) -> None:
    payload = {
        "action_type": "add_credit_sale",
        "customer_name": "Ramesh Sharma",
        "amount": 250.0,
        "currency": "INR",
        "items": ["dal", "chini"],
        "idempotency_key": "idemp_test_001",
        "provenance": {"intent": "rules", "amount": "rules"},
    }

    # First attempt: Created
    res1 = await client.post("/api/v1/ledger/entries", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    entry_id = data1["id"]
    cust_id = data1["customer_id"]
    assert data1["amount"] == 250.0
    assert data1["customer_name"] == "Ramesh Sharma"

    # Second attempt with exact same idempotency_key: must return existing record
    res2 = await client.post("/api/v1/ledger/entries", json=payload)
    assert res2.status_code == 200 or res2.status_code == 201
    data2 = res2.json()
    assert data2["id"] == entry_id
    assert data2["customer_id"] == cust_id

    # Verify only one event exists in the database
    res_list = await client.get("/api/v1/ledger/entries", params={"customer_id": cust_id})
    assert res_list.status_code == 200
    entries = res_list.json()
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_customer_balance_calculation(client: AsyncClient) -> None:
    # 1. Credit sale of 500 for Suresh
    await client.post(
        "/api/v1/ledger/entries",
        json={
            "action_type": "add_credit_sale",
            "customer_name": "Suresh Kumar",
            "amount": 500.0,
            "idempotency_key": "idemp_suresh_credit_1",
        },
    )

    # 2. Payment received of 200 from Suresh
    await client.post(
        "/api/v1/ledger/entries",
        json={
            "action_type": "payment_received",
            "customer_name": "Suresh Kumar",
            "amount": 200.0,
            "idempotency_key": "idemp_suresh_pay_1",
        },
    )

    # 3. Check customer balance: 500 - 200 = 300
    res_cust = await client.get("/api/v1/ledger/customers")
    assert res_cust.status_code == 200
    customers = res_cust.json()
    suresh = next(c for c in customers if c["name"] == "Suresh Kumar")
    assert suresh["balance"] == 300.0

    # 4. Check detailed balance audit endpoint
    res_audit = await client.get(f"/api/v1/ledger/customers/{suresh['id']}/balance")
    assert res_audit.status_code == 200
    audit = res_audit.json()
    assert audit["balance"] == 300.0
    assert audit["total_credit"] == 500.0
    assert audit["total_paid"] == 200.0


@pytest.mark.asyncio
async def test_undo_last_as_compensating_event(client: AsyncClient) -> None:
    # 1. Post a credit sale for Verma of 350
    post_res = await client.post(
        "/api/v1/ledger/entries",
        json={
            "action_type": "add_credit_sale",
            "customer_name": "Verma Ji",
            "amount": 350.0,
            "idempotency_key": "idemp_verma_credit_1",
        },
    )
    assert post_res.status_code == 201
    cust_id = post_res.json()["customer_id"]

    # 2. Post undo_last
    undo_res = await client.post(
        "/api/v1/ledger/entries",
        json={
            "action_type": "undo_last",
            "customer_id": cust_id,
            "amount": 0.0,
            "idempotency_key": "idemp_verma_undo_1",
        },
    )
    assert undo_res.status_code == 201
    undo_data = undo_res.json()
    assert undo_data["event_type"] == "compensation_undo"
    assert undo_data["amount"] == -350.0

    # 3. Verify balance is now 0.0
    res_audit = await client.get(f"/api/v1/ledger/customers/{cust_id}/balance")
    assert res_audit.status_code == 200
    audit = res_audit.json()
    assert audit["balance"] == 0.0
