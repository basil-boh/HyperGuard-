"""The swarm's event vocabulary.

Agents never call the websocket directly. They emit `SwarmEvent`s onto a bus and
the API layer fans them out to connected consoles. This keeps the orchestration
testable and decouples "what happened" from "who is watching".
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    case_opened = "case.opened"
    risk_scored = "risk.scored"
    agent_engaged = "agent.engaged"
    agent_completed = "agent.completed"
    call_started = "call.started"
    transcript_turn = "transcript.turn"
    scam_classified = "scam.classified"
    guardian_alerted = "guardian.alerted"
    decision_made = "decision.made"
    evidence_built = "evidence.built"
    # Voice follow-up: the LLM's reasoning over the victim's real answers, and the
    # filed incident report.
    assessment_ready = "assessment.ready"
    report_filed = "report.filed"
    case_closed = "case.closed"


# Stable ordering of agents in the relay, used by the console to lay out the track.
AGENT_SEQUENCE = (
    "digital_twin",
    "voice_negotiator",
    "educator",
    "guardian",
    "recovery_coordinator",
)


class SwarmEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    type: EventType
    case_id: str
    agent: str | None = None
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)

    def envelope(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
