"""Which model to spend on, and what it cost.

Most transfers never reach an LLM at all — the Digital Twin's risk score is a
deterministic logistic function, so the cheap path is *free*, not merely cheaper.
Of the cases that do reach a model, the great majority are ordinary verification
calls that a small model handles perfectly well. Reserving the expensive model for
cases that have actually escalated keeps both the bill and the time-to-first-word
down where it matters: the customer is on the phone, waiting.

The rule, deliberately a single readable predicate:

    deep  ⟸  a scam pattern has been confirmed
              OR risk has crossed the hard-block threshold
    fast  ⟸  everything else

Written outputs — the post-call assessment and the incident report — always use the
deep model. Nobody is waiting on them, and they are the artefacts a human reads.

`ModelUsage` records what was actually spent per case so the saving is measurable
rather than asserted. Token counts always; dollars only when per-model prices are
configured, because inventing a price is worse than showing none.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.config import Settings

logger = logging.getLogger("hyperguard.model")

FAST = "fast"
DEEP = "deep"


def tier_for(
    *,
    risk_score: float | None,
    classification: dict | None,
    settings: Settings,
    escalated: bool = False,
) -> str:
    """The tier a call should run on, given what the swarm knows so far."""
    if escalated:
        return DEEP
    if _scam_confirmed(classification):
        return DEEP
    if risk_score is not None and risk_score >= settings.hard_block_threshold:
        return DEEP
    return FAST


def _scam_confirmed(classification: dict | None) -> bool:
    if not classification:
        return False
    archetype = classification.get("archetype")
    if archetype in (None, "none", "unknown"):
        return False
    try:
        return float(classification.get("confidence") or 0) >= 0.6
    except (TypeError, ValueError):
        return False


# ── Usage accounting ───────────────────────────────────────────────────────────
@dataclass
class ModelCall:
    purpose: str  # "negotiator.opening", "assessment", …
    tier: str
    model: str
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ok: bool = True

    def json(self) -> dict:
        return {
            "purpose": self.purpose,
            "tier": self.tier,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "ok": self.ok,
        }


@dataclass
class ModelUsage:
    """Every model call made for one case."""

    calls: list[ModelCall] = field(default_factory=list)

    def record(self, call: ModelCall) -> None:
        self.calls.append(call)

    def summary(self, settings: Settings | None = None) -> dict:
        by_tier: dict[str, dict] = {}
        for call in self.calls:
            bucket = by_tier.setdefault(
                call.tier,
                {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0},
            )
            bucket["calls"] += 1
            bucket["prompt_tokens"] += call.prompt_tokens
            bucket["completion_tokens"] += call.completion_tokens
            bucket["latency_ms"] += call.latency_ms

        total_tokens = sum(c.prompt_tokens + c.completion_tokens for c in self.calls)
        deep_tokens = sum(
            c.prompt_tokens + c.completion_tokens for c in self.calls if c.tier == DEEP
        )
        failed = [c for c in self.calls if not c.ok]

        payload = {
            "calls": [c.json() for c in self.calls],
            "total_calls": len(self.calls),
            "by_tier": by_tier,
            "total_latency_ms": sum(c.latency_ms for c in self.calls),
            "promoted": any(c.tier == DEEP for c in self.calls),
            # Price-free saving evidence. Dollars need a configured rate and we refuse to
            # guess one, but "what share of this case's tokens avoided the expensive model"
            # is measurable from the ledger alone — so the tiering claim is backed by a
            # number even when no price table exists.
            "total_tokens": total_tokens,
            "deep_token_share": round(deep_tokens / total_tokens, 4) if total_tokens else None,
            "fast_token_share": (
                round((total_tokens - deep_tokens) / total_tokens, 4) if total_tokens else None
            ),
            # Surfaced so a dead tier can never hide behind a healthy-looking capability
            # report again — see the gpt-5.5-mini incident in FUNCTIONALITY.md.
            "failed_calls": len(failed),
            "degraded": bool(failed),
        }
        cost = self._cost(settings) if settings else None
        if cost is not None:
            payload["estimated_cost_usd"] = cost
        return payload

    def _cost(self, settings: Settings) -> dict | None:
        """Dollars, but only if prices were configured. Never a guessed rate."""
        prices = {
            FAST: (settings.llm_price_fast_input, settings.llm_price_fast_output),
            DEEP: (settings.llm_price_deep_input, settings.llm_price_deep_output),
        }
        if not any(p for pair in prices.values() for p in pair):
            return None

        actual = 0.0
        as_if_all_deep = 0.0
        deep_in, deep_out = prices[DEEP]
        for call in self.calls:
            price_in, price_out = prices.get(call.tier, (0.0, 0.0))
            actual += (
                call.prompt_tokens * (price_in or 0) + call.completion_tokens * (price_out or 0)
            ) / 1_000_000
            as_if_all_deep += (
                call.prompt_tokens * (deep_in or 0) + call.completion_tokens * (deep_out or 0)
            ) / 1_000_000

        return {
            "actual": round(actual, 6),
            "if_all_deep": round(as_if_all_deep, 6),
            "saved": round(max(0.0, as_if_all_deep - actual), 6),
        }


# ── Per-case ledgers ───────────────────────────────────────────────────────────
# The voice follow-up runs *after* the graph closes the case, so its deep-tier
# written outputs need to land on the same ledger the in-call turns used. Keyed by
# case id and bounded, in the same spirit as the intervention registry.
_MAX_CASES = 200
_usage_by_case: dict[str, ModelUsage] = {}
_usage_order: list[str] = []


def get_usage(case_id: str) -> ModelUsage:
    """The ledger for `case_id`, created on first use."""
    usage = _usage_by_case.get(case_id)
    if usage is None:
        usage = ModelUsage()
        _usage_by_case[case_id] = usage
        _usage_order.append(case_id)
        while len(_usage_order) > _MAX_CASES:
            _usage_by_case.pop(_usage_order.pop(0), None)
    return usage


def peek_usage(case_id: str) -> ModelUsage | None:
    """The ledger for `case_id`, or None if nothing was ever spent on it."""
    return _usage_by_case.get(case_id)


def reset_usage() -> None:
    """Drop every ledger. Tests only."""
    _usage_by_case.clear()
    _usage_order.clear()
