"""
Proof of domain-agnostic architecture: creating a second dummy DomainPack.

Proves that the speech-and-reasoning pipeline functions with an arbitrary domain
(e.g., Task Tracker or Clinic Prescriptions) without altering core abstractions.
"""

from typing import Any

import pytest

from bolkhata.domains.base import (
    DomainAction,
    DomainIntent,
    DomainPack,
)


class DummyTaskIntent(DomainIntent):
    task_name: str | None = None
    priority: str = "normal"


class DummyTaskPack(DomainPack):
    """A minimal secondary domain pack for task reminders."""

    name = "task_tracker"
    version = "1.0.0"
    system_prompt = "Extract task reminders and priority."

    async def parse_rules(self, text: str) -> DummyTaskIntent | None:
        cleaned = text.lower()
        if "remind" in cleaned or "yaad dilana" in cleaned:
            return DummyTaskIntent(
                name="create_task",
                task_name=text.replace("remind", "").replace("yaad dilana", "").strip(),
                priority="high" if "urgent" in cleaned or "zaroori" in cleaned else "normal",
                confidence=0.9,
                provenance={"intent": "rules"},
            )
        return None

    def format_read_back(self, action: DomainAction) -> str:
        task = action.parameters.get("task_name", "Kaam")
        return f"Task set: {task}. Theek hai?"

    def create_action(self, intent: DomainIntent, **context: Any) -> DomainAction | None:
        if not isinstance(intent, DummyTaskIntent):
            return None
        return DomainAction(
            action_type=intent.name,
            parameters={"task_name": intent.task_name, "priority": intent.priority},
            requires_confirmation=True,
            idempotency_key=f"task_{intent.task_name}",
        )


@pytest.mark.asyncio
async def test_dummy_pack_conformance() -> None:
    pack = DummyTaskPack()
    assert pack.name == "task_tracker"
    assert pack.version == "1.0.0"

    intent = await pack.parse_rules("remind me to buy milk urgent")
    assert intent is not None
    assert intent.name == "create_task"
    assert intent.priority == "high"

    action = pack.create_action(intent)
    assert action is not None
    assert action.action_type == "create_task"
    assert action.requires_confirmation is True

    read_back = pack.format_read_back(action)
    assert "Task set: me to buy milk urgent. Theek hai?" in read_back
