"""
Unit tests for Trust UX, Voice Correction, Risk Evaluation, and Confirmation Safety Invariant.
"""

from __future__ import annotations

import pytest

from bolkhata.domains.ledger.models import LedgerIntent
from bolkhata.domains.ledger.trust import (
    apply_voice_correction,
    confirm_pending_entry,
    create_pending_entry,
    evaluate_risk,
)


def test_standard_risk_evaluation() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Sharma",
        amount=250.0,
        items=["chawal"],
    )
    risk_level, reasons = evaluate_risk(
        intent,
        asr_confidence=0.95,
        customer_resolved=True,
    )
    assert risk_level == "standard"
    assert len(reasons) == 0

    pending = create_pending_entry(intent, customer_id="c1", asr_confidence=0.95)
    assert pending.risk_level == "standard"
    assert "Sharma ji, do sau pachaas rupaye udhaar" in pending.read_back_spoken


def test_high_risk_amount_threshold() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Gupta",
        amount=12500.0,
    )
    risk_level, reasons = evaluate_risk(intent, customer_resolved=True)
    assert risk_level == "high"
    assert any("exceeds risk limit" in r for r in reasons)

    pending = create_pending_entry(intent, customer_id="c2")
    assert pending.risk_level == "high"
    # Strict read-back must include digit-by-digit pronunciation
    assert "ek do panch shunya shunya" in pending.read_back_spoken


def test_high_risk_low_asr_confidence() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Verma",
        amount=200.0,
    )
    risk_level, reasons = evaluate_risk(intent, asr_confidence=0.65, customer_resolved=True)
    assert risk_level == "high"
    assert any("Low ASR acoustic confidence" in r for r in reasons)


def test_high_risk_unresolved_customer() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="UnknownPerson",
        amount=200.0,
    )
    risk_level, reasons = evaluate_risk(intent, customer_resolved=False)
    assert risk_level == "high"
    assert any("unrecognized or in gray-zone" in r for r in reasons)


def test_apply_voice_correction_amount_patch() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Sharma",
        amount=300.0,
    )
    pending = create_pending_entry(intent, customer_id="c1")
    assert pending.intent.amount == 300.0
    assert pending.correction_count == 0

    # User speaks: "nahi teen sau nahi, teen sau pachaas"
    updated = apply_voice_correction(pending, "nahi teen sau nahi, teen sau pachaas")
    assert updated.intent.amount == 350.0
    assert updated.correction_count == 1
    assert "teen sau pachaas rupaye" in updated.read_back_spoken
    assert len(updated.patch_history) == 1
    assert updated.patch_history[0]["field"] == "amount"
    assert updated.patch_history[0]["new"] == 350.0


def test_apply_voice_correction_customer_patch() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Sharma",
        amount=200.0,
    )
    pending = create_pending_entry(intent)
    assert pending.intent.customer == "Sharma"

    # User speaks: "customer Verma ji hai"
    updated = apply_voice_correction(pending, "customer Verma ji hai")
    assert updated.intent.customer == "Verma"
    assert "Verma ji" in updated.read_back_spoken


def test_apply_voice_correction_date_patch() -> None:
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Sharma",
        amount=200.0,
        date="aaj",
    )
    pending = create_pending_entry(intent)
    assert pending.intent.date == "aaj"

    # User speaks: "kal ka likho"
    updated = apply_voice_correction(pending, "kal ka likho")
    assert updated.intent.date == "kal"


def test_bounded_corrections_fallback_to_manual_edit() -> None:
    """Bounded number of correction rounds (3) before falling back to manual edit."""
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Sharma",
        amount=200.0,
    )
    pending = create_pending_entry(intent)
    pending.max_corrections = 2

    # Round 1
    apply_voice_correction(pending, "nahi 300")
    assert not pending.requires_manual_edit
    assert pending.correction_count == 1

    # Round 2
    apply_voice_correction(pending, "nahi 400")
    assert not pending.requires_manual_edit
    assert pending.correction_count == 2

    # Round 3: Exceeds max_corrections -> must fallback
    apply_voice_correction(pending, "nahi 500")
    assert pending.requires_manual_edit is True
    assert "manually theek karein" in pending.read_back_spoken


def test_hard_confirmation_safety_bypass_rejected() -> None:
    """
    Acceptance Criterion Proof:
    No entry is ever saved without an explicit confirmation (prove with a test that tries to bypass it).
    """
    intent = LedgerIntent(
        name="add_credit_sale",
        customer="Sharma",
        amount=250.0,
    )
    pending = create_pending_entry(intent, customer_id="c1")
    assert pending.is_confirmed is False

    # Attempting to commit without confirmation must raise ValueError
    with pytest.raises(ValueError, match="entry has not been explicitly confirmed"):
        confirm_pending_entry(pending)

    # When merchant confirms
    pending.is_confirmed = True
    action = confirm_pending_entry(pending)
    assert action is not None
    assert action.action_type == "add_credit_sale"
    assert action.parameters["amount"] == 250.0
