"""Option C — does the conversation change any decisions?

Four pipelines over the same cases. E2 is what the live path does today (score, then
decide, no conversation); E3 adds the call. **If E3 and E2 produce identical verdicts, the
five-agent swarm is an expensive risk score.**

Reported as expected cost under an explicit cost model, not accuracy, because the two
mistakes are not equally bad and pretending otherwise hides the whole trade-off.

⚠️ Known ceiling: the Arbiter cannot currently release a transfer the score already
condemned — there is no un-block path in the system (see FUNCTIONALITY.md). So E3 can only
ever *add* blocks. The "decisions changed" count below is therefore a lower bound on what
the conversation could be worth, and the direction it cannot move in is the one that would
reduce false positives. Fix that before reading this table as a verdict on the idea.
"""

from __future__ import annotations

from app.schemas import ScamArchetype, VerificationStatus
from app.services.llm import LLMClient
from app.services.risk_engine import RiskEngine
from eval import option_b
from eval.metrics import fmt, pct
from eval.schema import Dataset, EvalCase

INTERVENTION_THRESHOLD = 0.58
HARD_BLOCK_THRESHOLD = 0.88

# Cost model. Stated here so it can be argued with — it drives every conclusion below.
#   A missed scam costs the transfer amount (the bank refunds, or the customer eats it).
#   A false block costs handling plus a churn risk on the relationship.
FALSE_BLOCK_COST = 40.0        # SGD, analyst handling + customer friction
FALSE_BLOCK_CHURN_P = 0.02     # probability the customer leaves over it
CHURN_COST = 1_200.0           # lifetime value lost

_engine = RiskEngine()


def _cost(blocked: bool, case: EvalCase) -> float:
    if case.is_scam:
        return 0.0 if blocked else case.transaction.amount
    return (FALSE_BLOCK_COST + FALSE_BLOCK_CHURN_P * CHURN_COST) if blocked else 0.0


def e0_approve_all(_case: EvalCase, _score: float, _cls) -> bool:
    return False


def e1_amount_rule(case: EvalCase, _score: float, _cls) -> bool:
    return case.transaction.amount >= 5_000


def e2_score_only(_case: EvalCase, score: float, _cls) -> bool:
    """What the live path does today: everything at or above the threshold blocks, because
    without the educator the Arbiter never sees a `verified` verification."""
    return score >= INTERVENTION_THRESHOLD


def e3_with_conversation(_case: EvalCase, score: float, cls: tuple[str, float]) -> bool:
    """Full swarm: the Arbiter's real logic, with the classifier's verdict fed in."""
    arch, conf = cls
    is_scam = arch not in (ScamArchetype.none.value, ScamArchetype.unknown.value) and conf >= 0.6
    # The educator marks a case verified when it finds no scam pattern after a couple of turns.
    verification = VerificationStatus.verified if not is_scam else VerificationStatus.coerced

    if score < INTERVENTION_THRESHOLD:
        return False
    if verification == VerificationStatus.verified and score < HARD_BLOCK_THRESHOLD:
        return False
    if is_scam or verification == VerificationStatus.coerced:
        return True
    return True


PIPELINES = {
    "E0": ("approve everything", e0_approve_all),
    "E1": ("block over SGD 5,000, no call", e1_amount_rule),
    "E2": ("risk score only, no conversation", e2_score_only),
    "E3": ("full swarm with the call", e3_with_conversation),
}


async def run(ds: Dataset, llm: LLMClient) -> dict:
    cases = ds.cases
    scores = [_engine.assess(c.customer, c.transaction).score for c in cases]

    # The classifier the swarm would actually have used, on each case's real utterances.
    if llm.enabled:
        preds = await option_b._classify_all(cases, llm)
        cls_used, cls_name = preds.get("C3", preds["C1"]), (
            "LLM + keyword floor" if "C3" in preds else "keyword matcher"
        )
    else:
        cls_used, cls_name = [option_b.keyword_classify(c) for c in cases], "keyword matcher"

    rows = []
    verdicts: dict[str, list[bool]] = {}
    for key, (label, fn) in PIPELINES.items():
        blocked = [fn(c, s, cl) for c, s, cl in zip(cases, scores, cls_used)]
        verdicts[key] = blocked
        total = sum(_cost(b, c) for b, c in zip(blocked, cases))
        caught = sum(1 for b, c in zip(blocked, cases) if c.is_scam and b)
        missed = sum(1 for b, c in zip(blocked, cases) if c.is_scam and not b)
        false_blocks = sum(1 for b, c in zip(blocked, cases) if not c.is_scam and b)
        rows.append({
            "key": key, "label": label,
            "cost": total, "cost_per_case": total / len(cases),
            "caught": caught, "missed": missed, "false_blocks": false_blocks,
            "scam_recall": caught / (caught + missed) if (caught + missed) else float("nan"),
        })

    # The question this option exists to answer.
    changed = [
        {
            "id": c.id, "slice": c.slice.value, "is_scam": c.is_scam,
            "score": round(s, 3), "e2": e2, "e3": e3,
        }
        for c, s, e2, e3 in zip(cases, scores, verdicts["E2"], verdicts["E3"])
        if e2 != e3
    ]
    helped = sum(1 for d in changed if (d["e3"] and d["is_scam"]) or (not d["e3"] and not d["is_scam"]))
    hurt = len(changed) - helped

    return {
        "rows": rows,
        "classifier": cls_name,
        "n": len(cases),
        "changed": changed,
        "changed_helped": helped,
        "changed_hurt": hurt,
        "cost_model": {
            "false_block": FALSE_BLOCK_COST + FALSE_BLOCK_CHURN_P * CHURN_COST,
            "missed_scam": "the transfer amount",
        },
        "sensitivity": _sensitivity(cases, scores, verdicts),
    }


def _sensitivity(cases, scores, verdicts) -> list[dict]:
    """Sweep the cost of a false block. The ranking of pipelines should not depend on one
    guessed constant — if it does, say so rather than picking the flattering value."""
    out = []
    for fb in (10, 40, 100, 400, 1_000):
        row = {"false_block_cost": fb}
        for key, blocked in verdicts.items():
            total = 0.0
            for b, c in zip(blocked, cases):
                if c.is_scam:
                    total += 0.0 if b else c.transaction.amount
                else:
                    total += fb if b else 0.0
            row[key] = total / len(cases)
        out.append(row)
    return out


def render(res: dict) -> str:
    L = ["## Option C — Does the conversation change the outcome?\n"]
    L.append(
        f"Same {res['n']} cases through four pipelines. Classifier in the loop: "
        f"**{res['classifier']}**. Cost model: a missed scam costs the transfer amount; a "
        f"false block costs SGD {res['cost_model']['false_block']:.0f} "
        f"(handling + churn risk).\n"
    )
    L.append("| | Pipeline | Scams caught | Missed | False blocks | Cost per case |")
    L.append("|---|---|---|---|---|---|")
    for r in res["rows"]:
        bold = "**" if r["key"] in ("E2", "E3") else ""
        L.append(
            f"| {r['key']} | {bold}{r['label']}{bold} | {r['caught']} ({pct(r['scam_recall'])}) | "
            f"{r['missed']} | {r['false_blocks']} | {bold}SGD {r['cost_per_case']:,.0f}{bold} |"
        )

    n_changed = len(res["changed"])
    L.append(f"\n### E2 → E3: the conversation changed **{n_changed}** of {res['n']} decisions\n")
    if n_changed == 0:
        L.append(
            "> **The conversation changed nothing.** On this dataset the five-agent swarm "
            "reaches the same verdict as the risk score alone. Either the score already "
            "contains everything the call reveals, or the call's output isn't reaching the "
            "decision. Both are worth knowing before pitching the voice layer as the "
            "differentiator.\n"
        )
    else:
        L.append(
            f"Of those, **{res['changed_helped']} were improvements** (a scam blocked, or a "
            f"legitimate transfer released) and **{res['changed_hurt']} were regressions**.\n"
        )
        L.append("| Case | Slice | Actually a scam | Score | Score-only | With call |")
        L.append("|---|---|---|---|---|---|")
        for d in res["changed"][:20]:
            L.append(
                f"| `{d['id']}` | {d['slice']} | {'yes' if d['is_scam'] else 'no'} | {d['score']} | "
                f"{'BLOCK' if d['e2'] else 'allow'} | {'BLOCK' if d['e3'] else 'allow'} |"
            )
        if n_changed > 20:
            L.append(f"\n_…and {n_changed - 20} more._")

    L.append("\n### Sensitivity: does the ranking survive a different cost of a false block?\n")
    L.append("| False block costs | " + " | ".join(PIPELINES) + " |")
    L.append("|---" * (len(PIPELINES) + 1) + "|")
    for row in res["sensitivity"]:
        cells = " | ".join(f"{row[k]:,.0f}" for k in PIPELINES)
        L.append(f"| SGD {row['false_block_cost']:,} | {cells} |")

    L.append(
        "\n> **Ceiling on this result.** The Arbiter has no path to release a transfer the "
        "score already condemned, so E3 can only add blocks, never remove them. The one "
        "direction that would cut false positives is structurally unavailable. Read the "
        "table with that in mind, and fix the reversal gap before treating it as a verdict."
    )
    return "\n".join(L)
