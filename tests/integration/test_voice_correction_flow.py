"""
Integration test for full multi-turn scripted voice correction, confirmation, and undo flow.

Simulates the real Kirana dialogue:
Turn 1: "Sharma ji ko teen sau rupaye udhaar likho" -> PendingEntry (₹300)
Turn 2: "nahi teen sau nahi, teen sau pachaas" -> Voice Patch -> PendingEntry (₹350)
Turn 3: "haan theek hai" -> Confirmed -> Committed to SQLite WAL ledger
Turn 4: "galat likh diya, aakhiri entry hatao" -> Compensating undo -> Balance ₹0
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from bolkhata.api.app import create_app, lifespan
from bolkhata.common.base import Base
from bolkhata.domains.common.confirmation import (
    ConfirmationType,
    parse_confirmation_utterance,
)
from bolkhata.domains.ledger.db_models import Customer
from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.trust import (
    apply_voice_correction,
    confirm_pending_entry,
    create_pending_entry,
)


@pytest.mark.asyncio
async def test_full_scripted_voice_correction_and_undo_flow(tmp_path: Path) -> None:
    application = create_app()
    test_db = tmp_path / "voice_flow.db"
    application.state.database_url = f"sqlite+aiosqlite:///{test_db}"

    async with lifespan(application):
        async with application.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as client:
            # Setup initial customer in database
            async with application.state.session_factory() as session:
                cust = Customer(name="Sharma", normalized_name="sharma")
                session.add(cust)
                await session.commit()
                cust_id = cust.id

            # ---------------------------------------------------------------
            # Turn 1: Initial Utterance
            # ---------------------------------------------------------------
            turn1_text = "Sharma ji ko teen sau rupaye udhaar likho"
            res1 = await client.post("/api/v1/ledger/utterance", json={"text": turn1_text})
            assert res1.status_code == 200
            data1 = res1.json()
            intent1 = LedgerIntent(**data1["intent"])
            assert intent1.amount == 300.0
            assert intent1.customer == "Sharma"

            # Create PendingEntry awaiting confirmation
            pending = create_pending_entry(
                intent1,
                customer_id=cust_id,
                client_turn_id="turn_abc_1",
            )
            assert pending.is_confirmed is False
            assert "Sharma ji, teen sau rupaye udhaar" in pending.read_back_spoken

            # ---------------------------------------------------------------
            # Turn 2: Voice Correction ("nahi teen sau nahi, teen sau pachaas")
            # ---------------------------------------------------------------
            turn2_text = "nahi teen sau nahi, teen sau pachaas"
            conf2 = parse_confirmation_utterance(turn2_text)
            assert conf2.confirmation_type == ConfirmationType.CORRECTION
            assert conf2.is_correction is True
            assert conf2.correction_field == "amount"

            # Apply correction patch to pending entry
            pending = apply_voice_correction(pending, turn2_text)
            assert pending.intent.amount == 350.0
            assert pending.correction_count == 1
            assert "Theek hai, badal diya" in pending.read_back_spoken
            assert "teen sau pachaas rupaye" in pending.read_back_spoken

            # ---------------------------------------------------------------
            # Turn 3: Merchant Confirms ("haan theek hai")
            # ---------------------------------------------------------------
            turn3_text = "haan theek hai"
            conf3 = parse_confirmation_utterance(turn3_text)
            assert conf3.confirmation_type == ConfirmationType.CONFIRM

            pending.is_confirmed = True
            action = confirm_pending_entry(pending)
            assert action is not None

            # Commit entry to ledger API
            entry_payload = {
                "customer_id": cust_id,
                "action_type": action.action_type,
                "amount": action.parameters["amount"],
                "idempotency_key": action.idempotency_key,
                "notes": "Voice flow transaction",
            }
            res_commit = await client.post("/api/v1/ledger/entries", json=entry_payload)
            assert res_commit.status_code == 201
            entry_data = res_commit.json()
            assert entry_data["amount"] == 350.0

            # Verify customer balance is exactly ₹350.0
            res_bal = await client.get(f"/api/v1/ledger/customers/{cust_id}/balance")
            assert res_bal.status_code == 200
            assert res_bal.json()["balance"] == 350.0

            # ---------------------------------------------------------------
            # Turn 4: Voice Undo ("galat likh diya, aakhiri entry hatao")
            # ---------------------------------------------------------------
            turn4_text = "galat likh diya, aakhiri entry hatao"
            res_undo_parse = await client.post(
                "/api/v1/ledger/utterance", json={"text": turn4_text}
            )
            assert res_undo_parse.status_code == 200
            undo_action_data = res_undo_parse.json()["action"]
            assert undo_action_data["action_type"] == "undo_last"

            # Execute compensating undo
            undo_payload = {
                "customer_id": cust_id,
                "action_type": "undo_last",
                "amount": 0.0,
                "idempotency_key": undo_action_data["idempotency_key"],
                "notes": "Compensating voice undo",
            }
            res_undo = await client.post("/api/v1/ledger/entries", json=undo_payload)
            assert res_undo.status_code == 201
            assert res_undo.json()["event_type"] == "compensation_undo"

            # Verify balance is now reset to ₹0.0
            res_bal2 = await client.get(f"/api/v1/ledger/customers/{cust_id}/balance")
            assert res_bal2.status_code == 200
            assert res_bal2.json()["balance"] == 0.0
