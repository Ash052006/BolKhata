"""
Session state machine and transition table for push-to-talk interaction.
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from bolkhata.common.logging import get_logger

logger = get_logger(__name__)


class SessionState(str, enum.Enum):
    """The four core states of a push-to-talk session."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""

    def __init__(self, from_state: SessionState, to_state: SessionState, reason: str = "") -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(
            f"Invalid session state transition: cannot transition from {from_state.value} to {to_state.value}"
            + (f" ({reason})" if reason else "")
        )


# Valid transition map: from_state -> set of valid target states
VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.LISTENING},
    SessionState.LISTENING: {SessionState.THINKING, SessionState.IDLE},
    SessionState.THINKING: {SessionState.SPEAKING, SessionState.IDLE},
    SessionState.SPEAKING: {SessionState.IDLE, SessionState.LISTENING},
}


class SessionStateMachine:
    """
    State machine managing a single push-to-talk session.

    Enforces that illegal transitions raise InvalidStateTransitionError and are
    logged with structured context. Automatically issues generation_id when
    entering THINKING.
    """

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self._state: SessionState = SessionState.IDLE
        self._turn_id: str | None = None
        self._generation_id: str | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def turn_id(self) -> str | None:
        return self._turn_id

    @property
    def generation_id(self) -> str | None:
        return self._generation_id

    def transition_to(
        self,
        target_state: SessionState,
        turn_id: str | None = None,
        reason: str = "",
    ) -> tuple[SessionState, str | None]:
        """
        Attempt a state transition.

        Returns (new_state, generation_id).
        Raises InvalidStateTransitionError if the transition is illegal.
        """
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        if target_state not in valid_targets:
            logger.warning(
                "invalid_state_transition_attempted",
                session_id=self.session_id,
                current_state=self._state.value,
                target_state=target_state.value,
                turn_id=turn_id or self._turn_id,
                generation_id=self._generation_id,
                reason=reason,
            )
            raise InvalidStateTransitionError(self._state, target_state, reason)

        prev_state = self._state
        self._state = target_state

        if target_state == SessionState.LISTENING:
            self._turn_id = turn_id
            self._generation_id = None
        elif target_state == SessionState.THINKING:
            # Generate a new generation_id on entering THINKING
            if turn_id is not None:
                self._turn_id = turn_id
            self._generation_id = str(uuid.uuid4())
        elif target_state == SessionState.IDLE:
            self._turn_id = None
            self._generation_id = None

        logger.info(
            "session_state_transitioned",
            session_id=self.session_id,
            prev_state=prev_state.value,
            new_state=self._state.value,
            turn_id=self._turn_id,
            generation_id=self._generation_id,
            reason=reason,
        )

        return self._state, self._generation_id

    def reset_to_idle(self, reason: str = "reset") -> None:
        """Forcibly or gracefully reset state to IDLE."""
        prev_state = self._state
        self._state = SessionState.IDLE
        self._turn_id = None
        self._generation_id = None

        logger.info(
            "session_reset_to_idle",
            session_id=self.session_id,
            prev_state=prev_state.value,
            reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize current state."""
        return {
            "session_id": self.session_id,
            "state": self._state.value,
            "turn_id": self._turn_id,
            "generation_id": self._generation_id,
        }
