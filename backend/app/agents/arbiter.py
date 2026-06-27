"""The decision point.

Not one of the five public agents, this is the swarm's adjudicator. It folds the
risk score, the verification verdict, and the scam classification into a single
approve/block decision, biased toward customer safety when the picture is
inconclusive on a high-risk transfer.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.domain.events import EventType
from app.schemas import (
    Decision,
    ScamArchetype,
    TransactionStatus,
    VerificationStatus,
)
from app.state import SwarmState


class Arbiter(Agent):
    name = "arbiter"

    async def __call__(self, state: SwarmState) -> dict:
        case_id = state["case_id"]
        txn = state["transaction"]
        risk = state["risk"]
        classification = state.get("classification")
        verification = state.get("verification", VerificationStatus.unknown)
        settings = self.rt.settings

        is_scam = bool(
            classification
            and classification.archetype not in (ScamArchetype.none, ScamArchetype.unknown)
            and classification.confidence >= 0.6
        )

        if risk.score < settings.intervention_threshold:
            decision = Decision.approve
        elif verification == VerificationStatus.verified and risk.score < settings.hard_block_threshold:
            decision = Decision.approve
        elif is_scam or verification in (VerificationStatus.failed, VerificationStatus.coerced):
            decision = Decision.block
        elif risk.score >= settings.hard_block_threshold:
            decision = Decision.block
        else:
            decision = Decision.block  # inconclusive on a high-risk transfer → protect first

        txn.status = (
            TransactionStatus.approved if decision == Decision.approve else TransactionStatus.blocked
        )
        narrative = self._narrative(state, decision, is_scam)

        await self.emit(
            case_id,
            EventType.decision_made,
            payload={
                "decision": decision.value,
                "status": txn.status.value,
                "narrative": narrative,
            },
        )
        return {"decision": decision, "narrative": narrative, "transaction": txn}

    @staticmethod
    def _narrative(state: SwarmState, decision: Decision, is_scam: bool) -> str:
        txn = state["transaction"]
        risk = state["risk"]
        classification = state.get("classification")
        alerts = state.get("guardian_alerts", [])
        amount = f"{txn.currency} {txn.amount:,.0f}"

        if decision == Decision.approve and risk.score < 0.58:
            return (
                f"Approved. The {amount} transfer to {txn.payee_name} matched "
                f"{state['customer'].name.split()[0]}'s established behaviour with no scam "
                "indicators, released without interruption."
            )
        if decision == Decision.approve:
            return (
                f"Approved after verification. The customer clearly explained the purpose of the "
                f"{amount} transfer to {txn.payee_name} and no coercion was detected on the call."
            )

        pattern = classification.title if (classification and is_scam) else "a high-risk pattern"
        contact = f"; {alerts[0].contact.name} was alerted" if alerts else ""
        return (
            f"Blocked. The {amount} transfer to {txn.payee_name} was halted after the call "
            f"surfaced {pattern}{contact}. The money never left the account, and a recovery "
            "evidence package was prepared for reporting the beneficiary."
        )
