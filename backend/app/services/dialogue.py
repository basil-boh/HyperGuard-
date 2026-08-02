"""Conversation generation for the Voice Negotiator.

Two collaborators:

* `NegotiatorVoice` decides what HyperGuard says next. With an LLM it speaks
  naturally and in-context; without one it falls back to a calm, well-structured
  script. Either way it folds the Educator's live guidance into the call the moment
  a scam pattern is recognised.
* `VictimSimulator` stands in for the human on the line during hermetic demos,
  replaying the seeded archetype's script turn by turn.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas import (
    CustomerProfile,
    RiskAssessment,
    ScamClassification,
    TransactionRequest,
)
from app.services.llm import LLMClient
from app.services.model_policy import ModelUsage, tier_for

_SYSTEM = (
    "You are HyperGuard, a calm, warm fraud-prevention agent on a live phone call with "
    "a bank customer who is about to make a high-risk transfer. Your goals, in order: "
    "(1) keep them at ease, (2) understand who asked them to send the money and why, "
    "(3) gently surface the warning signs of a scam without lecturing, (4) never accuse "
    "the customer. Reply with ONE short spoken sentence (max 30 words). Return JSON "
    '{"line": "<what you say>"}.'
)


class NegotiatorVoice:
    def __init__(self, llm: LLMClient, settings: Settings | None = None) -> None:
        self._llm = llm
        self._settings = settings or get_settings()
        # Per-case usage ledger, set by the orchestrator for the life of a case.
        self._usage: ModelUsage | None = None

    def track(self, usage: ModelUsage | None) -> None:
        self._usage = usage

    def _tier(
        self, risk: RiskAssessment, classification: ScamClassification | None
    ) -> str:
        """Cheap while the call is still exploratory; deep once it has escalated.

        The customer is on the line, so an unescalated turn buys latency by staying
        on the small model — and an unescalated turn is, by definition, one where
        nothing has been confirmed yet.
        """
        return tier_for(
            risk_score=risk.score if risk else None,
            classification=classification.model_dump(mode="json") if classification else None,
            settings=self._settings,
        )

    async def opening(
        self, customer: CustomerProfile, txn: TransactionRequest, risk: RiskAssessment
    ) -> str:
        templated = (
            f"Hello {customer.name.split()[0]}, this is HyperGuard calling from your bank's "
            f"protection team. I've paused a {txn.currency} {txn.amount:,.0f} transfer to "
            f"{txn.payee_name} to check it's really you and that everything's okay. "
            "Can you tell me what this payment is for?"
        )
        if not self._llm.enabled:
            return templated
        out = await self._llm.complete_json(
            _SYSTEM,
            f"Open the call. Customer: {customer.name}. Transfer: {txn.currency} "
            f"{txn.amount:,.0f} to {txn.payee_name}. Risk drivers: {risk.rationale}",
            tier=self._tier(risk, None),
            purpose="negotiator.opening",
            usage=self._usage,
        )
        return (out or {}).get("line") or templated

    async def respond(
        self,
        history: list[str],
        risk: RiskAssessment,
        classification: ScamClassification | None,
    ) -> str:
        # Once the Educator has identified a pattern, deliver its guidance verbatim —
        # the safety wording is authored, not generated. No model call at all.
        if classification and classification.archetype.value not in ("none", "unknown"):
            return classification.guidance

        templated = (
            "I understand. Just so I can keep you safe, did someone contact you and ask "
            "you to make this transfer, or is this something you started yourself?"
        )
        if not self._llm.enabled:
            return templated
        joined = "\n".join(history[-6:])
        out = await self._llm.complete_json(
            _SYSTEM,
            f"Conversation so far:\n{joined}\n\nAsk your next single question.",
            tier=self._tier(risk, classification),
            purpose="negotiator.respond",
            usage=self._usage,
        )
        return (out or {}).get("line") or templated


class VictimSimulator:
    """Replays a scripted victim for demos. Returns None once the script is exhausted."""

    def next_line(self, script: tuple[str, ...] | list[str], turn_index: int) -> str | None:
        if 0 <= turn_index < len(script):
            return script[turn_index]
        return None
