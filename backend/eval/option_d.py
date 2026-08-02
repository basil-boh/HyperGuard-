"""Option D — are the explanations right, or just present?

"Explainable decisions" is asserted everywhere in the pitch. This measures it two ways.

**Signal fidelity.** Each case records which signals a correct model *should* fire. We
compare that to what actually fired. This catches the failure mode that a bare accuracy
number hides: being right for the wrong reason. A model that blocks every scam while citing
the wrong evidence is unusable in an audit, and indefensible on a phone call.

**Rationale legibility.** A cheap proxy for the human study: does every fired signal carry a
non-empty, non-duplicated, human-readable reason, and does the top-contributing signal
actually name the dominant cause?
"""

from __future__ import annotations

from app.services.risk_engine import RiskEngine
from eval.metrics import fmt, pct, proportion_ci
from eval.schema import Dataset

_engine = RiskEngine()


def run(ds: Dataset) -> dict:
    per_signal: dict[str, dict[str, int]] = {}
    exact = 0
    jaccards: list[float] = []
    empty_details = 0
    total_signals = 0
    top_signal_correct = 0
    scored = 0

    for case in ds.cases:
        a = _engine.assess(case.customer, case.transaction)
        fired = {s.code for s in a.signals}
        expected = set(case.expected_signals)

        for code in fired | expected:
            row = per_signal.setdefault(code, {"tp": 0, "fp": 0, "fn": 0})
            if code in fired and code in expected:
                row["tp"] += 1
            elif code in fired:
                row["fp"] += 1
            else:
                row["fn"] += 1

        if fired == expected:
            exact += 1
        union = fired | expected
        jaccards.append(len(fired & expected) / len(union) if union else 1.0)

        for s in a.signals:
            total_signals += 1
            if not s.detail.strip() or not s.label.strip():
                empty_details += 1

        # Does the loudest signal name a real cause?
        if a.signals:
            scored += 1
            top = max(a.signals, key=lambda s: s.contribution)
            if top.code in expected:
                top_signal_correct += 1

    rows = []
    for code, r in sorted(per_signal.items()):
        p = r["tp"] / (r["tp"] + r["fp"]) if (r["tp"] + r["fp"]) else float("nan")
        rec = r["tp"] / (r["tp"] + r["fn"]) if (r["tp"] + r["fn"]) else float("nan")
        rows.append({"code": code, **r, "precision": p, "recall": rec})

    n = len(ds.cases)
    lo, hi = proportion_ci(exact, n)
    return {
        "n": n,
        "exact_match": exact / n,
        "exact_ci": (lo, hi),
        "mean_jaccard": sum(jaccards) / len(jaccards) if jaccards else float("nan"),
        "per_signal": rows,
        "empty_details": empty_details,
        "total_signals": total_signals,
        "top_signal_accuracy": top_signal_correct / scored if scored else float("nan"),
    }


def render(res: dict) -> str:
    L = ["## Option D — Explainability, measured\n"]
    L.append(
        "Does the engine fire the signals it *should* fire? Ground truth is recorded per case "
        "at generation time, independently of what the engine does.\n"
    )
    lo, hi = res["exact_ci"]
    L.append(f"- **Exact signal-set match:** {pct(res['exact_match'])} ({pct(lo)}–{pct(hi)}) of {res['n']} cases")
    L.append(f"- **Mean overlap (Jaccard):** {fmt(res['mean_jaccard'])}")
    L.append(
        f"- **Top signal names a true cause:** {pct(res['top_signal_accuracy'])} — this is the one "
        "an operator reads first, and the one the customer hears on the phone"
    )
    L.append(
        f"- **Signals with an empty reason string:** {res['empty_details']} of {res['total_signals']} "
        "(anything above zero is an audit hole)\n"
    )
    L.append("| Signal | Correctly fired | Wrongly fired | Missed | Precision | Recall |")
    L.append("|---|---|---|---|---|---|")
    for r in res["per_signal"]:
        L.append(
            f"| `{r['code']}` | {r['tp']} | {r['fp']} | {r['fn']} | "
            f"{pct(r['precision'])} | {pct(r['recall'])} |"
        )
    L.append(
        "\n> Read `fp` as *the engine cited a reason that wasn't true of the case* and `fn` as "
        "*a real driver it never mentioned*. Both are explainability failures even when the "
        "final verdict happens to be right."
    )
    return "\n".join(L)
