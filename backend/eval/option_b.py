"""Option B — does the scam classifier survive rewording?

The Educator matches literal substrings (`"safe account"`). This asks what happens when the
same scam is described as *"an account where it'll be protected"* — and whether an LLM
holds up where the matcher doesn't.

Four classifiers, two datasets (clean and adversarial). The delta between the two is the
finding, not the absolute score.
"""

from __future__ import annotations

import asyncio

from app.schemas import ScamArchetype
from app.services.llm import LLMClient
from app.services.scam_taxonomy import ScamTaxonomy
from eval.metrics import ClassReport, classification_report, expected_calibration_error, fmt, pct, proportion_ci
from eval.schema import Dataset, EvalCase, Slice

_taxonomy = ScamTaxonomy()

_LABELS = [a.value for a in ScamArchetype if a not in (ScamArchetype.unknown,)]

_LLM_SYSTEM = (
    "You classify what kind of scam, if any, a bank customer is describing. You are given "
    "only what the customer said on a verification call.\n\n"
    "Choose exactly one:\n"
    "- government_impersonation: someone posing as police/government, money must be moved to be "
    "checked or kept safe\n"
    "- bank_impersonation: someone posing as the customer's bank, move funds to a 'new' account\n"
    "- investment_scam: high or guaranteed returns, a platform showing gains, a fee to withdraw\n"
    "- romance_scam: an online partner never met in person who needs money\n"
    "- job_scam: paid tasks/commission work requiring the customer to fund it first\n"
    "- tech_support_scam: fake virus/compromise, remote access, an overpaid 'refund' to return\n"
    "- none: no scam — an ordinary payment the customer arranged themselves\n\n"
    'Respond ONLY as JSON: {"archetype": "<one of the above>", "confidence": 0.0-1.0}'
)


def keyword_classify(case: EvalCase) -> tuple[str, float]:
    c = _taxonomy.classify(case.speech)
    return c.archetype.value, c.confidence


async def llm_classify(case: EvalCase, llm: LLMClient) -> tuple[str, float]:
    # tier="deep" deliberately: the default "fast" tier resolves to a model id that 404s,
    # and a silent fallback would score the LLM as if it had answered "none" every time.
    out = await llm.complete_json(
        _LLM_SYSTEM, f"The customer said:\n{case.speech}", tier="deep"
    )
    arch = (out or {}).get("archetype")
    if arch not in _LABELS:
        arch = ScamArchetype.none.value
    try:
        conf = max(0.0, min(1.0, float((out or {}).get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    return arch, conf


def floor_combine(kw: tuple[str, float], llm_out: tuple[str, float]) -> tuple[str, float]:
    """LLM proposes; the keyword matcher can only make it stricter, never laxer.

    Same bias-to-safety shape the Arbiter already uses: if the deterministic matcher is
    confident a scam is present and the LLM says 'none', the matcher wins. It can never
    talk the LLM *out* of a scam call.
    """
    kw_arch, kw_conf = kw
    llm_arch, llm_conf = llm_out
    if llm_arch == ScamArchetype.none.value and kw_arch != ScamArchetype.none.value and kw_conf >= 0.6:
        return kw_arch, kw_conf
    return llm_arch, llm_conf


async def _classify_all(cases: list[EvalCase], llm: LLMClient) -> dict[str, list[tuple[str, float]]]:
    kw = [keyword_classify(c) for c in cases]
    if not llm.enabled:
        return {"C1": kw}
    sem = asyncio.Semaphore(8)

    async def one(c: EvalCase):
        async with sem:
            return await llm_classify(c, llm)

    llm_out = list(await asyncio.gather(*(one(c) for c in cases)))
    combined = [floor_combine(k, l) for k, l in zip(kw, llm_out)]
    return {"C1": kw, "C2": llm_out, "C3": combined}


def _majority(cases: list[EvalCase]) -> list[tuple[str, float]]:
    return [(ScamArchetype.none.value, 0.0)] * len(cases)


def _score(cases: list[EvalCase], preds: list[tuple[str, float]]) -> dict:
    truth = [c.archetype.value for c in cases]
    pred = [p for p, _ in preds]
    rep: ClassReport = classification_report(truth, pred)

    # Abstention: on legitimate cases, does it correctly say "none"?
    legit_idx = [i for i, c in enumerate(cases) if not c.is_scam]
    correct_abstain = sum(1 for i in legit_idx if pred[i] == ScamArchetype.none.value)
    lo, hi = proportion_ci(correct_abstain, len(legit_idx))

    # Binary scam/not, independent of getting the archetype right.
    scam_true = [1 if c.is_scam else 0 for c in cases]
    scam_pred = [1 if p != ScamArchetype.none.value else 0 for p in pred]
    tp = sum(1 for t, p in zip(scam_true, scam_pred) if t and p)
    fp = sum(1 for t, p in zip(scam_true, scam_pred) if not t and p)
    fn = sum(1 for t, p in zip(scam_true, scam_pred) if t and not p)

    conf = [c for _, c in preds]
    ece, _ = expected_calibration_error(
        conf, [1 if pred[i] == truth[i] else 0 for i in range(len(truth))]
    )

    return {
        "macro_f1": rep.macro_f1,
        "accuracy": rep.accuracy,
        "per_class": rep.per_class,
        "confusion": rep.confusion,
        "abstention": correct_abstain / len(legit_idx) if legit_idx else float("nan"),
        "abstention_ci": (lo, hi),
        "scam_recall": tp / (tp + fn) if (tp + fn) else float("nan"),
        "scam_precision": tp / (tp + fp) if (tp + fp) else float("nan"),
        "confidence_ece": ece,
    }


async def run(ds: Dataset, llm: LLMClient) -> dict:
    clean = ds.by_slice(Slice.scam_clean, Slice.legit_suspicious, Slice.legit_obvious)
    adversarial = ds.by_slice(Slice.scam_adversarial, Slice.legit_suspicious, Slice.legit_obvious)

    out: dict = {"llm_available": llm.enabled, "sets": {}}
    for name, cases in (("clean", clean), ("adversarial", adversarial)):
        preds = await _classify_all(cases, llm)
        entry = {"n": len(cases), "C0": _score(cases, _majority(cases))}
        for key, p in preds.items():
            entry[key] = _score(cases, p)
        out["sets"][name] = entry

    # Scam-only view: the paraphrase delta, uncontaminated by the shared legit cases.
    scam_clean = ds.by_slice(Slice.scam_clean)
    scam_adv = ds.by_slice(Slice.scam_adversarial)
    out["scam_only"] = {}
    for name, cases in (("clean", scam_clean), ("adversarial", scam_adv)):
        preds = await _classify_all(cases, llm)
        out["scam_only"][name] = {
            "n": len(cases),
            **{k: _score(cases, v)["scam_recall"] for k, v in preds.items()},
        }
    return out


_NAMES = {
    "C0": "always say 'none'",
    "C1": "keyword matcher (shipped)",
    "C2": "LLM zero-shot",
    "C3": "LLM + keyword floor",
}


def render(res: dict) -> str:
    L = ["## Option B — Scam classifier, clean vs reworded\n"]
    if not res["llm_available"]:
        L.append("> No `OPENAI_API_KEY` — only the shipped keyword matcher was evaluated.\n")

    for set_name in ("clean", "adversarial"):
        e = res["sets"][set_name]
        title = "Clean scams" if set_name == "clean" else "Reworded (adversarial) scams"
        L.append(f"### {title} — n={e['n']}\n")
        L.append("| Classifier | Macro-F1 | Scam recall | Scam precision | Correct 'none' on legit | Confidence error |")
        L.append("|---|---|---|---|---|---|")
        for key in ("C0", "C1", "C2", "C3"):
            if key not in e:
                continue
            r = e[key]
            bold = "**" if key == "C1" else ""
            lo, hi = r["abstention_ci"]
            L.append(
                f"| {bold}{_NAMES[key]}{bold} | {fmt(r['macro_f1'])} | {pct(r['scam_recall'])} | "
                f"{pct(r['scam_precision'])} | {pct(r['abstention'])} ({pct(lo)}–{pct(hi)}) | "
                f"{fmt(r['confidence_ece'])} |"
            )
        L.append("")

    so = res["scam_only"]
    L.append("### The headline: recall on scams only, clean vs reworded\n")
    L.append("| Classifier | Clean | Reworded | Drop |")
    L.append("|---|---|---|---|")
    for key in ("C1", "C2", "C3"):
        if key not in so["clean"]:
            continue
        c, a = so["clean"][key], so["adversarial"][key]
        L.append(f"| {_NAMES[key]} | {pct(c)} | {pct(a)} | **{(a - c) * 100:+.1f} pts** |")

    L.append("\n### Where the keyword matcher confuses classes (clean set)\n")
    conf = res["sets"]["clean"]["C1"]["confusion"]
    classes = sorted(conf)
    L.append("| truth ↓ / pred → | " + " | ".join(f"`{c[:12]}`" for c in classes) + " |")
    L.append("|---" * (len(classes) + 1) + "|")
    for t in classes:
        L.append(f"| `{t[:16]}` | " + " | ".join(str(conf[t][p]) for p in classes) + " |")
    return "\n".join(L)
