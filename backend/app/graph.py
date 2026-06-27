"""The swarm orchestrator, a LangGraph state machine.

Nodes are the agents; edges are conditional transitions on the risk score, the
verification verdict, and the scam classification. The negotiator↔educator loop is
bounded by `max_negotiation_turns` so a stuck conversation can never hang a case.

    START → digital_twin ─┬─(low risk)──────────────→ arbiter → END
                          ├─(already defrauded)─────→ recovery → END
                          └─(high risk)→ negotiator → educator ─┬─(loop)→ negotiator
                                              ↑                  ├─(verified)→ arbiter
                                              └──────────────────┘
                                            educator ─(scam / exhausted)→ guardian → arbiter
                                            arbiter ─(blocked)→ recovery → END
"""

from __future__ import annotations

from functools import lru_cache
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.arbiter import Arbiter
from app.agents.digital_twin import DigitalTwin
from app.agents.educator import Educator
from app.agents.guardian import Guardian
from app.agents.negotiator import VoiceNegotiator
from app.agents.recovery import RecoveryCoordinator
from app.domain.events import EventType, SwarmEvent
from app.runtime import Runtime
from app.schemas import (
    CustomerProfile,
    Decision,
    InterventionOutcome,
    ScamArchetype,
    TransactionRequest,
    TransactionStatus,
    VerificationStatus,
)
from app.state import SwarmState

_RECURSION_LIMIT = 60


class SwarmOrchestrator:
    def __init__(self, rt: Runtime | None = None) -> None:
        self.rt = rt or Runtime()
        self._twin = DigitalTwin(self.rt)
        self._negotiator = VoiceNegotiator(self.rt)
        self._educator = Educator(self.rt)
        self._guardian = Guardian(self.rt)
        self._arbiter = Arbiter(self.rt)
        self._recovery = RecoveryCoordinator(self.rt)
        self._compiled = self._build()

    # ── Graph assembly ─────────────────────────────────────────────────────────
    def _build(self):
        g: StateGraph = StateGraph(SwarmState)
        g.add_node("digital_twin", self._twin)
        g.add_node("negotiator", self._negotiator)
        g.add_node("educator", self._educator)
        g.add_node("guardian", self._guardian)
        g.add_node("arbiter", self._arbiter)
        g.add_node("recovery", self._recovery)

        g.add_edge(START, "digital_twin")
        g.add_conditional_edges(
            "digital_twin",
            self._route_after_twin,
            {"intervene": "negotiator", "settle": "arbiter", "recover": "recovery"},
        )
        g.add_edge("negotiator", "educator")
        g.add_conditional_edges(
            "educator",
            self._route_after_educator,
            {"escalate": "guardian", "continue": "negotiator", "settle": "arbiter"},
        )
        g.add_edge("guardian", "arbiter")
        g.add_conditional_edges(
            "arbiter", self._route_after_arbiter, {"recover": "recovery", "end": END}
        )
        g.add_edge("recovery", END)
        return g.compile()

    # ── Routers ────────────────────────────────────────────────────────────────
    def _route_after_twin(self, state: SwarmState) -> str:
        if state["transaction"].status == TransactionStatus.completed:
            return "recover"  # post-hoc fraud report, straight to evidence
        if state["risk"].score < self.rt.settings.intervention_threshold:
            return "settle"
        return "intervene"

    def _route_after_educator(self, state: SwarmState) -> str:
        classification = state.get("classification")
        verification = state.get("verification", VerificationStatus.unknown)
        turn_count = state.get("turn_count", 0)

        scam_confirmed = bool(
            classification
            and classification.archetype not in (ScamArchetype.none, ScamArchetype.unknown)
            and classification.confidence >= 0.6
        )
        if scam_confirmed:
            return "escalate"
        if verification == VerificationStatus.verified:
            return "settle"
        if turn_count >= self.rt.settings.max_negotiation_turns:
            return "escalate"
        return "continue"

    def _route_after_arbiter(self, state: SwarmState) -> str:
        return "recover" if state.get("decision") == Decision.block else "end"

    # ── Entry point ──────────────────────────────────────────────────────────────
    async def run(
        self,
        customer: CustomerProfile,
        txn: TransactionRequest,
        case_id: str | None = None,
    ) -> InterventionOutcome:
        case_id = case_id or f"HG-{uuid4().hex[:10].upper()}"
        if txn.status == TransactionStatus.pending:
            txn.status = TransactionStatus.intervening

        await self.rt.bus.publish(
            SwarmEvent(
                type=EventType.case_opened,
                case_id=case_id,
                payload={
                    "customer": customer.model_dump(mode="json"),
                    "transaction": txn.model_dump(mode="json"),
                    "capabilities": self.rt.settings.capability_report(),
                },
            )
        )

        initial: SwarmState = {
            "case_id": case_id,
            "customer": customer,
            "transaction": txn,
            "transcript": [],
            "turn_count": 0,
            "guardian_alerts": [],
            "verification": VerificationStatus.unknown,
        }
        final: SwarmState = await self._compiled.ainvoke(
            initial, config={"recursion_limit": _RECURSION_LIMIT}
        )
        outcome = self._assemble(case_id, final)
        await self.rt.store.save_outcome(case_id, customer, outcome)

        await self.rt.bus.publish(
            SwarmEvent(
                type=EventType.case_closed,
                case_id=case_id,
                payload={"outcome": outcome.model_dump(mode="json")},
            )
        )
        return outcome

    def _assemble(self, case_id: str, state: SwarmState) -> InterventionOutcome:
        decision = state.get("decision")
        if decision is None:
            # post-hoc recovery path never reaches the arbiter
            decision = Decision.block
        return InterventionOutcome(
            transaction_id=state["transaction"].id,
            decision=decision,
            verification=state.get("verification", VerificationStatus.unknown),
            risk=state["risk"],
            classification=state.get("classification"),
            transcript=list(state.get("transcript", [])),
            guardian_alerts=list(state.get("guardian_alerts", [])),
            evidence=state.get("evidence"),
            decided_at=self._twin.now(),
            narrative=state.get("narrative")
            or "Post-incident recovery package generated for a previously processed transfer.",
        )


@lru_cache
def get_orchestrator() -> SwarmOrchestrator:
    """Process-wide orchestrator. Shared by the scenario API and the wallet API so
    they emit onto the same bus the console and registry are listening to."""
    return SwarmOrchestrator()
