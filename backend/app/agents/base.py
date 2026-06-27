"""Shared agent scaffolding.

Agents are callables over `SwarmState`. The base class gives them a clock and an
`emit` helper so every node narrates itself onto the bus the same way.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.domain.events import EventType, SwarmEvent
from app.runtime import Runtime

# Events worth lingering on, so the console renders as a live operation in demo mode.
_PACED_EVENTS = {
    EventType.agent_engaged,
    EventType.risk_scored,
    EventType.transcript_turn,
    EventType.scam_classified,
    EventType.guardian_alerted,
    EventType.decision_made,
    EventType.evidence_built,
}


class Agent:
    #: stable identifier used in events and on the console relay track.
    name: str = "agent"

    def __init__(self, rt: Runtime) -> None:
        self.rt = rt

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    async def emit(
        self,
        case_id: str,
        event_type: EventType,
        *,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.rt.bus.publish(
            SwarmEvent(
                type=event_type,
                case_id=case_id,
                agent=self.name,
                payload=payload or {},
            )
        )
        if self.rt.settings.demo_mode and event_type in _PACED_EVENTS:
            delay = self.rt.settings.demo_step_delay
            if delay > 0:
                await asyncio.sleep(delay)

    async def __call__(self, state):  # pragma: no cover - interface
        raise NotImplementedError
