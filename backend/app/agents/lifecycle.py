"""
HospitalOps AI — Agent Orchestration Lifecycle States (Milestone 5, Chunk 5.3).

Defines:
- OrchestrationState: Explicit, typed lifecycle progression for agent execution.
- StateTransitionRecord: Auditable record of every state transition.
- OrchestrationStateTracker: Deterministic state machine enforcing valid transitions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.models.base import HospitalOpsBaseModel, utc_now

logger = logging.getLogger(__name__)


class OrchestrationState(str, Enum):
    """
    Explicit lifecycle states for the Agent Orchestration Engine.

    Normal Execution Flow:
    PENDING -> UNDERSTANDING -> PLANNING -> TOOL_SELECTION ->
    TOOL_EXECUTION -> EVIDENCE_REVIEW -> (loop to PLANNING if needed) ->
    RESPONSE_GENERATION -> COMPLETED

    Terminal Failure / Rejection States:
    REJECTED (e.g. clinical query or unregistered agent)
    FAILED (e.g. unrecoverable tool or planner error)
    CANCELLED (e.g. aborted by caller)
    TIMED_OUT (exceeded orchestration execution deadline)
    MAX_STEPS_REACHED (exhausted maximum reasoning iterations)
    INSUFFICIENT_EVIDENCE (unable to find needed evidence after investigation)
    """

    PENDING = "PENDING"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    TOOL_SELECTION = "TOOL_SELECTION"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"
    COMPLETED = "COMPLETED"

    # Terminal failure states
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


TERMINAL_STATES: frozenset[OrchestrationState] = frozenset(
    {
        OrchestrationState.COMPLETED,
        OrchestrationState.REJECTED,
        OrchestrationState.FAILED,
        OrchestrationState.CANCELLED,
        OrchestrationState.TIMED_OUT,
        OrchestrationState.MAX_STEPS_REACHED,
        OrchestrationState.INSUFFICIENT_EVIDENCE,
    }
)

VALID_TRANSITIONS: dict[OrchestrationState, frozenset[OrchestrationState]] = {
    OrchestrationState.PENDING: frozenset(
        {
            OrchestrationState.UNDERSTANDING,
            OrchestrationState.REJECTED,
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.UNDERSTANDING: frozenset(
        {
            OrchestrationState.PLANNING,
            OrchestrationState.RESPONSE_GENERATION,  # Direct no-tool answer path
            OrchestrationState.REJECTED,
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.PLANNING: frozenset(
        {
            OrchestrationState.TOOL_SELECTION,
            OrchestrationState.RESPONSE_GENERATION,  # Final answer ready or no tools needed
            OrchestrationState.MAX_STEPS_REACHED,
            OrchestrationState.INSUFFICIENT_EVIDENCE,
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.TOOL_SELECTION: frozenset(
        {
            OrchestrationState.TOOL_EXECUTION,
            OrchestrationState.RESPONSE_GENERATION,  # No valid tools available
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.TOOL_EXECUTION: frozenset(
        {
            OrchestrationState.EVIDENCE_REVIEW,
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.EVIDENCE_REVIEW: frozenset(
        {
            OrchestrationState.PLANNING,  # Next step in multi-tool loop
            OrchestrationState.RESPONSE_GENERATION,  # Evidence sufficient
            OrchestrationState.INSUFFICIENT_EVIDENCE,
            OrchestrationState.MAX_STEPS_REACHED,
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.RESPONSE_GENERATION: frozenset(
        {
            OrchestrationState.COMPLETED,
            OrchestrationState.INSUFFICIENT_EVIDENCE,
            OrchestrationState.MAX_STEPS_REACHED,
            OrchestrationState.FAILED,
            OrchestrationState.TIMED_OUT,
            OrchestrationState.CANCELLED,
        }
    ),
}


class StateTransitionRecord(HospitalOpsBaseModel):
    """Immutable audit entry for an orchestration state transition."""

    from_state: OrchestrationState
    to_state: OrchestrationState
    timestamp: datetime = Field(default_factory=utc_now)
    reason: str = Field(default="", description="Operational rationale for this state transition")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Contextual telemetry")


class OrchestrationStateTracker:
    """
    Deterministic state machine for agent execution.
    Enforces valid transitions and rejects illegal or posthumous transitions.
    """

    def __init__(self, initial_state: OrchestrationState = OrchestrationState.PENDING) -> None:
        self._current_state = initial_state
        self._history: list[StateTransitionRecord] = []
        self._created_at = utc_now()

    @property
    def current_state(self) -> OrchestrationState:
        return self._current_state

    @property
    def is_terminal(self) -> bool:
        return self._current_state in TERMINAL_STATES

    @property
    def history(self) -> list[StateTransitionRecord]:
        return list(self._history)

    def transition_to(
        self,
        new_state: OrchestrationState,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StateTransitionRecord:
        """
        Transition the state machine to a new state if valid.
        Raises ValueError if the transition is illegal or if already terminal.
        """
        if self.is_terminal:
            msg = (
                f"Cannot transition from terminal state '{self._current_state.value}' "
                f"to '{new_state.value}'."
            )
            logger.error(msg)
            raise ValueError(msg)

        allowed = VALID_TRANSITIONS.get(self._current_state, frozenset())
        if new_state not in allowed:
            msg = (
                f"Illegal state transition from '{self._current_state.value}' "
                f"to '{new_state.value}'. Allowed targets: {[s.value for s in allowed]}."
            )
            logger.error(msg)
            raise ValueError(msg)

        record = StateTransitionRecord(
            from_state=self._current_state,
            to_state=new_state,
            timestamp=utc_now(),
            reason=reason,
            metadata=metadata or {},
        )
        self._history.append(record)
        self._current_state = new_state
        logger.debug(
            "Agent state transition: %s -> %s (reason: %s)",
            record.from_state,
            record.to_state,
            reason,
        )
        return record
