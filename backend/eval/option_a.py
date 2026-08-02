"""Option A — is the risk score smarter than a dumb rule?

Runs six scorers over the same cases and reports ranking quality, the operating point at
the *shipped* threshold (0.58, not a tuned one), and calibration. Then ablates each signal
to turn the engine's asserted weights into measured ones.
"""

from __future__ import annotations

from app.services.llm import LLMClient
from app.services.risk_engine import RiskEngine
from eval import baselines as bl
from eval.metrics import (
    bootstrap_ci, expected_calibration_error, fmt, operating_point, pct, pr_auc, roc_auc, sweep
)
from eval.schema import Dataset, EvalCase

THRESHOLD = 0.58  # settings.intervention_threshold — the shipped value, deliberately


def _scores(fn, cases: list[EvalCase], ctx: dict) -> list[float]:
    return [fn(c, ctx) for c in cases]


async def run(ds: Dataset, llm: LLMClient) -> dict:
    cases = ds.cases
    labels = [1 if c.is_scam else 0 for c in cases]
    ctx = bl.population_context(cases)

    rows = []
    for key, (label, fn) in bl.DETERMINISTIC.items():
        s = _scores(fn, cases, ctx)
        rows.append(_evaluate(key, label, s, labels))

    llm_scores = await bl.b5_llm_scores(cases, llm)
    if llm_scores is not None:
        rows.append(_evaluate("B5", "raw LLM, no features", llm_scores, labels))
    else:
        rows.append({"key": "B5", "label": "raw LLM, no features", "skipped": "no OPENAI_API_KEY"})

    hg = _scores(bl.b4_hyperguard, cases, ctx)
    ece, curve = expected_calibration_error(hg, labels)

    return {
        "rows": rows,
        "threshold": THRESHOLD,
        "calibration": {"ece": ece, "curve": curve},
        "sweep": [
            {"t": op.threshold, "tpr": op.tpr, "fpr": op.fpr, "precision": op.precision}
            for op in sweep(hg, labels, steps=11)
        ],
        "ablation": _ablate(cases, labels),
        "slice_fpr": _slice_fpr(cases, hg),
    }


def _evaluate(key: str, label: str, scores: list[float], labels: list[int]) -> dict:
    op = operating_point(scores, labels, THRESHOLD)
    auc = roc_auc(scores, labels)
    lo, hi = bootstrap_ci(scores, labels, roc_auc)
    return {
        "key": key, "label": label,
        "roc_auc": auc, "roc_ci": (lo, hi),
        "pr_auc": pr_auc(scores, labels),
        "tpr": op.tpr, "fpr": op.fpr, "precision": op.precision, "f1": op.f1,
        "tp": op.tp, "fp": op.fp, "tn": op.tn, "fn": op.fn,
    }


def _ablate(cases: list[EvalCase], labels: list[int]) -> list[dict]:
    """Drop one signal at a time and measure the AUC it was worth.

    Implemented by zeroing the signal's contribution rather than editing the engine: we
    re-score with the signal's weight removed from the evidence sum, which is exactly what
    deleting it would do.
    """
    engine = RiskEngine()
    full = [engine.assess(c.customer, c.transaction) for c in cases]
    base_auc = roc_auc([a.score for a in full], labels)

    codes = sorted({s.code for a in full for s in a.signals})
    out = []
    for code in codes:
        # Recompute the logistic with this signal's evidence removed.
        import math
        adjusted = []
        for a in full:
            removed = sum(
                _weight_of(s, a) for s in a.signals if s.code == code
            )
            evidence = _total_evidence(a) - removed
            adjusted.append(round(min(1 / (1 + math.exp(-(engine.BIAS + evidence))), 0.99), 4))
        auc = roc_auc(adjusted, labels)
        fired = sum(1 for a in full if any(s.code == code for s in a.signals))
        out.append({
            "code": code, "fired_in": fired, "auc_without": auc, "delta": base_auc - auc
        })
    out.sort(key=lambda r: -r["delta"])
    return [{"base_auc": base_auc}] + out


def _total_evidence(assessment) -> float:
    """Invert the engine's contribution split to recover the evidence sum it used."""
    import math
    s = min(assessment.score, 0.9899)
    # score = logistic(bias + evidence) * amplifier; recover pre-amplifier logit.
    amp = 1.15 if any(x.code == "elevated_vulnerability" for x in assessment.signals) else 1.0
    p = min(max(s / amp, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p)) - RiskEngine.BIAS


def _weight_of(signal, assessment) -> float:
    total_contrib = sum(x.contribution for x in assessment.signals) or 1.0
    return _total_evidence(assessment) * (signal.contribution / total_contrib)


def _slice_fpr(cases: list[EvalCase], scores: list[float]) -> list[dict]:
    """False-positive rate broken out by slice. The headline FPR hides the one that matters:
    legitimate transfers that *look* suspicious."""
    out = []
    for slice_ in {c.slice for c in cases if not c.is_scam}:
        idx = [i for i, c in enumerate(cases) if c.slice is slice_]
        flagged = sum(1 for i in idx if scores[i] >= THRESHOLD)
        out.append({
            "slice": slice_.value, "n": len(idx), "flagged": flagged,
            "fpr": flagged / len(idx) if idx else float("nan"),
        })
    return sorted(out, key=lambda r: -r["fpr"])


def render(res: dict) -> str:
    L = []
    L.append("## Option A — Risk engine vs baselines\n")
    L.append(
        f"Ranking quality and the operating point at the **shipped threshold "
        f"({res['threshold']})**, not a tuned one.\n"
    )
    L.append("| | Scorer | ROC-AUC | 95% CI | PR-AUC | Catch rate | False-positive rate | Precision |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in res["rows"]:
        if r.get("skipped"):
            L.append(f"| {r['key']} | {r['label']} | — | — | — | — | — | _{r['skipped']}_ |")
            continue
        ci = f"{fmt(r['roc_ci'][0], 2)}–{fmt(r['roc_ci'][1], 2)}"
        bold = "**" if r["key"] == "B4" else ""
        L.append(
            f"| {r['key']} | {bold}{r['label']}{bold} | {bold}{fmt(r['roc_auc'])}{bold} | {ci} | "
            f"{fmt(r['pr_auc'])} | {pct(r['tpr'])} | {pct(r['fpr'])} | {pct(r['precision'])} |"
        )

    L.append("\n### False positives by slice\n")
    L.append("| Slice | n | Flagged | FPR |")
    L.append("|---|---|---|---|")
    for s in res["slice_fpr"]:
        L.append(f"| `{s['slice']}` | {s['n']} | {s['flagged']} | {pct(s['fpr'])} |")

    L.append("\n### Threshold sweep (HyperGuard)\n")
    L.append("| Threshold | Catch rate | FPR | Precision |")
    L.append("|---|---|---|---|")
    for p in res["sweep"]:
        mark = "  ← shipped" if abs(p["t"] - res["threshold"]) < 0.06 else ""
        L.append(f"| {p['t']:.1f}{mark} | {pct(p['tpr'])} | {pct(p['fpr'])} | {pct(p['precision'])} |")

    ab = res["ablation"]
    base = ab[0]["base_auc"]
    L.append(f"\n### Signal ablation (base ROC-AUC {fmt(base)})\n")
    L.append("What each signal is actually worth, versus the weight it was assigned by hand.\n")
    L.append("| Signal | Fired in | AUC without it | Value |")
    L.append("|---|---|---|---|")
    for r in ab[1:]:
        L.append(
            f"| `{r['code']}` | {r['fired_in']} | {fmt(r['auc_without'])} | {r['delta']:+.3f} |"
        )

    ece = res["calibration"]["ece"]
    L.append(f"\n### Calibration\n\nExpected calibration error: **{fmt(ece)}**.")
    L.append("A score of 0.7 should mean a 70% chance of being a scam.\n")
    L.append("| Claimed | Observed | n |")
    L.append("|---|---|---|")
    for mean_s, obs, n in res["calibration"]["curve"]:
        L.append(f"| {fmt(mean_s, 2)} | {fmt(obs, 2)} | {n} |")
    return "\n".join(L)
