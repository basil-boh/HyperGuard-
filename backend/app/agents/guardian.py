"""Agent 4, The Guardian.

When the call confirms coercion (or stalls inconclusively on a high-risk transfer),
the Guardian pulls a human into the loop: it alerts the customer's highest-priority
trusted contact with the case context and asks them to corroborate. For vulnerable
customers this second pair of eyes is often what actually stops the transfer.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.domain.events import EventType
from app.state import SwarmState


class Guardian(Agent):
    name = "guardian"

    async def __call__(self, state: SwarmState) -> dict:
        case_id = state["case_id"]
        customer = state["customer"]
        txn = state["transaction"]
        classification = state.get("classification")
        risk = state["risk"]

        await self.emit(case_id, EventType.agent_engaged)

        contacts = sorted(customer.trusted_contacts, key=lambda c: c.priority)
        alerts = list(state.get("guardian_alerts", []))

        if not contacts:
            await self.emit(
                case_id, EventType.agent_completed, payload={"alerted": 0, "reason": "no_contacts"}
            )
            return {"guardian_alerts": alerts}

        pattern = classification.title if classification else "a high-risk transfer"
        target = contacts[0]
        message = (
            f"HyperGuard alert: {customer.name} is on a call attempting a "
            f"{txn.currency} {txn.amount:,.0f} transfer to {txn.payee_name}. "
            f"Our risk score is {risk.score:.0%} and the pattern matches {pattern}. "
            f"Please reach them now to confirm this is genuinely intended."
        )

        alert = await self.rt.notify.send_sms(target, message)
        # In a hermetic demo the trusted contact corroborates immediately; live SMS
        # acknowledgement arrives asynchronously and flips this later.
        if not self.rt.notify.is_live:
            alert.acknowledged = True
            alert.status = "acknowledged"
        alerts.append(alert)

        await self.emit(
            case_id,
            EventType.guardian_alerted,
            payload={"alert": alert.model_dump(mode="json")},
        )
        await self.emit(case_id, EventType.agent_completed, payload={"alerted": len(alerts)})
        return {"guardian_alerts": alerts}
