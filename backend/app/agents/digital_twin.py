"""Agent 1, The Digital Twin.

Scores the transaction against the customer's behavioural baseline and publishes
an explainable risk assessment. It is the gate: everything downstream only runs
because the Twin said the moment was worth interrupting.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.domain.events import EventType
from app.state import SwarmState


class DigitalTwin(Agent):
    name = "digital_twin"

    async def __call__(self, state: SwarmState) -> dict:
        case_id = state["case_id"]
        customer = state["customer"]
        txn = state["transaction"]

        await self.emit(case_id, EventType.agent_engaged)
        risk = self.rt.risk.assess(customer, txn)
        await self.emit(
            case_id, EventType.risk_scored, payload={"risk": risk.model_dump(mode="json")}
        )
        await self.emit(
            case_id,
            EventType.agent_completed,
            payload={"score": risk.score, "band": risk.band.value},
        )
        return {"risk": risk}
