"""Agent 5, The Recovery Coordinator.

Runs when a transfer is confirmed fraudulent, either blocked mid-flight (evidence
to report the scammer) or reported after the fact (evidence to claw funds back). It
assembles a single, investigator-ready package: the risk rationale, the full call
transcript, the scam classification, every guardian action, and a chronological
timeline, plus a recommended-action checklist for the bank and police.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.domain.events import EventType
from app.schemas import EvidencePackage, Speaker, TimelineEntry
from app.state import SwarmState


class RecoveryCoordinator(Agent):
    name = "recovery_coordinator"

    async def __call__(self, state: SwarmState) -> dict:
        case_id = state["case_id"]
        txn = state["transaction"]
        risk = state["risk"]
        classification = state.get("classification")
        transcript = list(state.get("transcript", []))
        alerts = list(state.get("guardian_alerts", []))

        await self.emit(case_id, EventType.agent_engaged)

        timeline = self._build_timeline(state)
        pattern = classification.title if classification else "Unclassified high-risk transfer"
        summary = (
            f"Case {case_id}: an attempted {txn.currency} {txn.amount:,.0f} transfer to "
            f"'{txn.payee_name}' (account {txn.payee_account}) was identified as {pattern} "
            f"at risk {risk.score:.0%}. {len(transcript)} conversation turns and "
            f"{len(alerts)} guardian action(s) are on file."
        )

        package = EvidencePackage(
            case_id=case_id,
            transaction=txn,
            risk=risk,
            classification=classification,
            transcript=transcript,
            guardian_alerts=alerts,
            timeline=timeline,
            generated_at=self.now(),
            executive_summary=summary,
            recommended_actions=self._recommended_actions(txn),
        )

        await self.emit(
            case_id,
            EventType.evidence_built,
            payload={"evidence": package.model_dump(mode="json")},
        )
        await self.emit(case_id, EventType.agent_completed)
        return {"evidence": package}

    def _build_timeline(self, state: SwarmState) -> list[TimelineEntry]:
        txn = state["transaction"]
        risk = state["risk"]
        entries = [
            TimelineEntry(at=txn.requested_at, actor="customer", event=(
                f"Initiated {txn.currency} {txn.amount:,.0f} transfer to {txn.payee_name}"
            )),
            TimelineEntry(at=self.now(), actor="digital_twin", event=(
                f"Scored risk at {risk.score:.0%} ({risk.band.value})"
            )),
        ]
        for turn in state.get("transcript", []):
            speaker = "HyperGuard" if turn.speaker == Speaker.agent else "Customer"
            entries.append(TimelineEntry(at=turn.ts, actor=speaker, event=turn.text))
        for alert in state.get("guardian_alerts", []):
            entries.append(TimelineEntry(at=self.now(), actor="guardian", event=(
                f"Alerted {alert.contact.name} ({alert.contact.relationship}) via {alert.channel}"
            )))
        return sorted(entries, key=lambda e: e.at)

    @staticmethod
    def _recommended_actions(txn) -> list[str]:
        return [
            f"Place an immediate recall/hold on transfer {txn.id} with the beneficiary bank.",
            f"Freeze and flag beneficiary account {txn.payee_account} for the receiving institution.",
            "File a police report citing this evidence package and case reference.",
            "Report the beneficiary account to the national anti-scam centre.",
            "Enrol the customer in step-up verification for outbound transfers for 30 days.",
        ]
