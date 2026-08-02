"""Baseline scorers.

A number reported in isolation says nothing. Each of these is a cheaper way to do what the
Digital Twin does, and the Digital Twin has to beat them to justify existing:

* **B0 approve-all** — the real-world status quo for authorised payments. Zero false
  positives, catches nothing. If you can't beat this on expected cost, the product is net
  negative.
* **B1 amount rule** — what a bank does with one line of SQL.
* **B2 population z-score** — an anomaly rule that is *not* personalised. **The Digital
  Twin's entire thesis is beating this one.**
* **B3 first-time-payee alone** — your single strongest signal, unaided. If the full
  eight-signal model can't beat one boolean, the other seven are decoration.
* **B4 HyperGuard** — the real engine.
* **B5 raw LLM** — no feature engineering, just the transaction described in prose. Answers
  "why not just prompt it?"
"""

from __future__ import annotations

import asyncio
import statistics

from app.schemas import CustomerProfile, TransactionRequest
from app.services.llm import LLMClient
from app.services.risk_engine import RiskEngine
from eval.schema import EvalCase

_engine = RiskEngine()


def b0_approve_all(_case: EvalCase, _ctx: dict) -> float:
    return 0.0


def b1_amount_threshold(case: EvalCase, _ctx: dict, cutoff: float = 5_000.0) -> float:
    """Flag anything over a flat ceiling. Scaled to [0,1] so it can be ranked, but it is a
    step function — its AUC is capped by construction, which is the point."""
    return 1.0 if case.transaction.amount >= cutoff else 0.0


def b2_population_z(case: EvalCase, ctx: dict) -> float:
    """z-score against the *whole book's* amount distribution, not the customer's own.

    This is the honest strawman: it is a real anomaly detector, it just doesn't know who
    the customer is. The gap between this and B4 is the value of personalisation.
    """
    mean = ctx["pop_mean"]
    std = ctx["pop_std"] or 1.0
    z = (case.transaction.amount - mean) / std
    return max(0.0, min(1.0, z / 4.0))


def b3_new_payee_only(case: EvalCase, _ctx: dict) -> float:
    txn = case.transaction
    if txn.payee_phone:
        return 1.0 if txn.payee_phone not in case.customer.known_payee_phones else 0.0
    return 1.0 if txn.payee_name not in case.customer.known_payees else 0.0


def b4_hyperguard(case: EvalCase, _ctx: dict) -> float:
    return _engine.assess(case.customer, case.transaction).score


def population_context(cases: list[EvalCase]) -> dict:
    amounts = [c.transaction.amount for c in cases]
    return {
        "pop_mean": statistics.fmean(amounts),
        "pop_std": statistics.pstdev(amounts) if len(amounts) > 1 else 1.0,
    }


DETERMINISTIC: dict[str, tuple[str, callable]] = {
    "B0": ("approve everything (status quo)", b0_approve_all),
    "B1": ("amount > SGD 5,000", b1_amount_threshold),
    "B2": ("population z-score (not personalised)", b2_population_z),
    "B3": ("first-time payee only", b3_new_payee_only),
    "B4": ("HyperGuard Digital Twin", b4_hyperguard),
}


# ── B5: the LLM, given no engineered features ──────────────────────────────────────
_B5_SYSTEM = (
    "You are a bank's fraud analyst. Given one outgoing transfer and the customer's normal "
    "banking behaviour, estimate the probability that this transfer is an authorised-push-"
    "payment scam — i.e. the customer is being manipulated into sending it. You are NOT told "
    "anything the customer said; judge on the transfer facts alone. Most transfers are "
    'legitimate. Respond ONLY as JSON: {"p": 0.0-1.0}'
)


def _describe(cust: CustomerProfile, txn: TransactionRequest) -> str:
    dest = txn.payee_phone or txn.payee_account
    known = (
        txn.payee_phone in cust.known_payee_phones
        if txn.payee_phone
        else txn.payee_name in cust.known_payees
    )
    return (
        f"Transfer: {txn.currency} {txn.amount:,.0f} to '{txn.payee_name}' ({dest}, "
        f"country {txn.payee_country}) via {txn.channel} at "
        f"{txn.requested_at.strftime('%H:%M')}. Memo: {txn.memo or '(none)'}. "
        f"Paid this recipient before: {'yes' if known else 'no'}. "
        f"{txn.recent_transfer_count_24h} transfers in the last 24h.\n"
        f"Customer: age {cust.age}, typically sends SGD "
        f"{cust.baseline_avg_amount:,.0f} (sd {cust.baseline_std_amount:,.0f}), "
        f"usually active {cust.typical_hour_start:02d}:00-{cust.typical_hour_end:02d}:00, "
        f"about {cust.typical_velocity_per_day:.1f} transfers/day."
    )


async def b5_llm_scores(cases: list[EvalCase], llm: LLMClient, concurrency: int = 8) -> list[float] | None:
    """Returns None when no LLM is configured, so the report can say so rather than guess."""
    if not llm.enabled:
        return None
    sem = asyncio.Semaphore(concurrency)

    async def one(case: EvalCase) -> float:
        async with sem:
            out = await llm.complete_json(_B5_SYSTEM, _describe(case.customer, case.transaction))
        try:
            return max(0.0, min(1.0, float((out or {}).get("p"))))
        except (TypeError, ValueError):
            return 0.0  # a refusal or malformed reply scores as "no concern"

    return list(await asyncio.gather(*(one(c) for c in cases)))
