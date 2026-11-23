"""
Unit tests for the push-to-talk session state machine and illegal transition rejection.
"""

from __future__ import annotations

import pytest

from bolkhata.realtime.state import (
    InvalidStateTransitionError,
    SessionState,
    SessionStateMachine,
)


class TestSessionStateMachine:
    """Test transitions, state tracking, and illegal transition rejection."""

    def test_initial_state_is_idle(self) -> None:
        sm = SessionStateMachine()
        assert sm.state == SessionState.IDLE
        assert sm.turn_id is None
        assert sm.generation_id is None

    def test_full_turn_lifecycle_transitions(self) -> None:
        sm = SessionStateMachine(session_id="test-session")

        # 1. IDLE -> LISTENING
        new_state, gen_id = sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        assert new_state == SessionState.LISTENING
        assert sm.turn_id == "turn-1"
        assert gen_id is None
        assert sm.generation_id is None

        # 2. LISTENING -> THINKING (should issue unique generation_id)
        new_state, gen_id = sm.transition_to(SessionState.THINKING)
        assert new_state == SessionState.THINKING
        assert sm.turn_id == "turn-1"
        assert gen_id is not None
        assert sm.generation_id == gen_id

        # 3. THINKING -> SPEAKING
        new_state, gen_id_speaking = sm.transition_to(SessionState.SPEAKING)
        assert new_state == SessionState.SPEAKING
        assert sm.turn_id == "turn-1"
        assert sm.generation_id == gen_id

        # 4. SPEAKING -> IDLE
        new_state, gen_id_idle = sm.transition_to(SessionState.IDLE)
        assert new_state == SessionState.IDLE
        assert sm.turn_id is None
        assert sm.generation_id is None

    def test_cancel_during_listening_resets_to_idle(self) -> None:
        sm = SessionStateMachine()
        sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        assert sm.state == SessionState.LISTENING

        sm.transition_to(SessionState.IDLE)
        assert sm.state == SessionState.IDLE
        assert sm.turn_id is None

    def test_cancel_during_thinking_resets_to_idle(self) -> None:
        sm = SessionStateMachine()
        sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        sm.transition_to(SessionState.THINKING)
        assert sm.state == SessionState.THINKING

        sm.transition_to(SessionState.IDLE)
        assert sm.state == SessionState.IDLE
        assert sm.generation_id is None

    def test_barge_in_during_speaking_transitions_to_listening(self) -> None:
        sm = SessionStateMachine()
        sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        sm.transition_to(SessionState.THINKING)
        sm.transition_to(SessionState.SPEAKING)
        assert sm.state == SessionState.SPEAKING

        # Client presses push-to-talk while assistant is speaking
        new_state, gen_id = sm.transition_to(SessionState.LISTENING, turn_id="turn-2")
        assert new_state == SessionState.LISTENING
        assert sm.turn_id == "turn-2"
        assert sm.generation_id is None

    def test_illegal_transition_idle_to_thinking_rejected(self) -> None:
        sm = SessionStateMachine()
        with pytest.raises(
            InvalidStateTransitionError, match="cannot transition from IDLE to THINKING"
        ):
            sm.transition_to(SessionState.THINKING)
        assert sm.state == SessionState.IDLE

    def test_illegal_transition_idle_to_speaking_rejected(self) -> None:
        sm = SessionStateMachine()
        with pytest.raises(
            InvalidStateTransitionError, match="cannot transition from IDLE to SPEAKING"
        ):
            sm.transition_to(SessionState.SPEAKING)
        assert sm.state == SessionState.IDLE

    def test_illegal_transition_listening_to_speaking_rejected(self) -> None:
        sm = SessionStateMachine()
        sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        with pytest.raises(
            InvalidStateTransitionError, match="cannot transition from LISTENING to SPEAKING"
        ):
            sm.transition_to(SessionState.SPEAKING)
        assert sm.state == SessionState.LISTENING

    def test_illegal_transition_thinking_to_listening_rejected(self) -> None:
        sm = SessionStateMachine()
        sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        sm.transition_to(SessionState.THINKING)
        with pytest.raises(
            InvalidStateTransitionError, match="cannot transition from THINKING to LISTENING"
        ):
            sm.transition_to(SessionState.LISTENING)
        assert sm.state == SessionState.THINKING

    def test_reset_to_idle_from_any_state(self) -> None:
        sm = SessionStateMachine()
        sm.transition_to(SessionState.LISTENING, turn_id="turn-1")
        sm.transition_to(SessionState.THINKING)
        assert sm.state == SessionState.THINKING

        sm.reset_to_idle(reason="forced_reset")
        assert sm.state == SessionState.IDLE
        assert sm.turn_id is None
        assert sm.generation_id is None
