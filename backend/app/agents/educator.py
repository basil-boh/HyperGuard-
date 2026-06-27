"""Agent 3, The Educator.

Reads the conversation so far, classifies the scam narrative from its linguistic
fingerprints, and decides whether the customer has been verified as safe, is being
coerced, or whether the call needs another round. Its classification is what the
Negotiator reads back to the customer on the next turn.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.domain.events import EventType
from app.schemas import ScamArchetype, Speaker, VerificationStatus
from app.state import SwarmState

_SCAM_CONFIDENCE_FLOOR = 0.6


class Educator(Agent):
    name = "educator"

    async def __call__(self, state: SwarmState) -> dict:
        case_id = state["case_id"]
        transcript = state.get("transcript", [])
        turn_count = state.get("turn_count", 0)

        await self.emit(case_id, EventType.agent_engaged)

        customer_speech = " ".join(
            t.text for t in transcript if t.speaker == Speaker.customer
        )
        classification = self.rt.taxonomy.classify(customer_speech)

        if (
            classification.archetype != ScamArchetype.none
            and classification.confidence >= _SCAM_CONFIDENCE_FLOOR
        ):
            verification = VerificationStatus.coerced
        elif classification.archetype == ScamArchetype.none and turn_count >= 2:
            verification = VerificationStatus.verified
        else:
            verification = VerificationStatus.unknown

        await self.emit(
            case_id,
            EventType.scam_classified,
            payload={
                "classification": classification.model_dump(mode="json"),
                "verification": verification.value,
            },
        )
        await self.emit(case_id, EventType.agent_completed)
        return {"classification": classification, "verification": verification}
