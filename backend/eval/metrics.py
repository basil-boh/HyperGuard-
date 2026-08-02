"""Metrics, implemented directly so the harness adds no dependency.

Everything that reports a headline number also reports a bootstrap confidence interval.
A point estimate on a few hundred cases is not a result — the interval is what tells you
whether a gap between two systems is real or noise.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# ── Ranking quality ────────────────────────────────────────────────────────────────
def roc_auc(scores: list[float], labels: list[int]) -> float:
    """Probability a random positive outranks a random negative (Mann-Whitney U).
    Ties count as half, which matters here — rule baselines emit only 0.0 and 1.0."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")

    ranked = sorted(zip(scores, labels), key=lambda t: t[0])
    ranks: dict[int, float] = {}
    i = 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based average rank across the tie group
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1

    rank_sum_pos = sum(ranks[k] for k, (_, y) in enumerate(ranked) if y == 1)
    n_pos, n_neg = len(pos), len(neg)
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2
    return u / (n_pos * n_neg)


def pr_auc(scores: list[float], labels: list[int]) -> float:
    """Average precision. More honest than ROC when positives are the minority."""
    if not any(labels):
        return float("nan")
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    total_pos = sum(labels)
    tp = 0
    prev_recall = 0.0
    area = 0.0
    for rank, idx in enumerate(order, start=1):
        tp += labels[idx]
        precision = tp / rank
        recall = tp / total_pos
        area += precision * (recall - prev_recall)
        prev_recall = recall
    return area


# ── Operating point ────────────────────────────────────────────────────────────────
@dataclass
class OperatingPoint:
    threshold: float
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def tpr(self) -> float:  # recall / catch rate
        d = self.tp + self.fn
        return self.tp / d if d else float("nan")

    @property
    def fpr(self) -> float:  # legitimate transfers interrupted
        d = self.fp + self.tn
        return self.fp / d if d else float("nan")

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else float("nan")

    @property
    def f1(self) -> float:
        p, r = self.precision, self.tpr
        return 2 * p * r / (p + r) if (p + r) else float("nan")


def operating_point(scores: list[float], labels: list[int], threshold: float) -> OperatingPoint:
    op = OperatingPoint(threshold=threshold)
    for s, y in zip(scores, labels):
        flagged = s >= threshold
        if y == 1 and flagged:
            op.tp += 1
        elif y == 1:
            op.fn += 1
        elif flagged:
            op.fp += 1
        else:
            op.tn += 1
    return op


def sweep(scores: list[float], labels: list[int], steps: int = 21) -> list[OperatingPoint]:
    return [operating_point(scores, labels, i / (steps - 1)) for i in range(steps)]


# ── Calibration ────────────────────────────────────────────────────────────────────
def expected_calibration_error(
    scores: list[float], labels: list[int], bins: int = 10
) -> tuple[float, list[tuple[float, float, int]]]:
    """Does a claimed 0.7 mean 70%? Returns (ECE, [(mean_score, observed_rate, n)]).

    A confidence number nobody has calibrated should not be shown to an operator, and
    should not be a routing threshold either.
    """
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for s, y in zip(scores, labels):
        idx = min(int(s * bins), bins - 1)
        buckets[idx].append((s, y))

    ece = 0.0
    curve: list[tuple[float, float, int]] = []
    n = len(scores)
    for b in buckets:
        if not b:
            continue
        mean_score = sum(s for s, _ in b) / len(b)
        observed = sum(y for _, y in b) / len(b)
        curve.append((mean_score, observed, len(b)))
        ece += (len(b) / n) * abs(mean_score - observed)
    return ece, curve


# ── Multi-class ────────────────────────────────────────────────────────────────────
@dataclass
class ClassReport:
    per_class: dict[str, dict[str, float]] = field(default_factory=dict)
    macro_f1: float = 0.0
    accuracy: float = 0.0
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)


def classification_report(truth: list[str], pred: list[str]) -> ClassReport:
    classes = sorted(set(truth) | set(pred))
    confusion = {t: {p: 0 for p in classes} for t in classes}
    for t, p in zip(truth, pred):
        confusion[t][p] += 1

    rep = ClassReport(confusion=confusion)
    f1s = []
    for c in classes:
        tp = confusion[c][c]
        fp = sum(confusion[t][c] for t in classes if t != c)
        fn = sum(confusion[c][p] for p in classes if p != c)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = sum(confusion[c].values())
        rep.per_class[c] = {
            "precision": precision, "recall": recall, "f1": f1, "support": support
        }
        if support:  # macro over classes actually present in truth
            f1s.append(f1)
    rep.macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    rep.accuracy = sum(1 for t, p in zip(truth, pred) if t == p) / len(truth) if truth else 0.0
    return rep


# ── Uncertainty ────────────────────────────────────────────────────────────────────
def bootstrap_ci(
    values: list[float], labels: list[int], stat, iterations: int = 400, seed: int = 7
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI. Deterministic seed so the report is reproducible."""
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    out = []
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        s = [values[i] for i in idx]
        y = [labels[i] for i in idx]
        try:
            v = stat(s, y)
        except Exception:
            continue
        if not math.isnan(v):
            out.append(v)
    if not out:
        return (float("nan"), float("nan"))
    out.sort()
    lo = out[int(0.025 * len(out))]
    hi = out[min(int(0.975 * len(out)), len(out) - 1)]
    return (lo, hi)


def proportion_ci(successes: int, n: int) -> tuple[float, float]:
    """Wilson interval — behaves near 0 and 1 where the normal approximation doesn't."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = 1.96
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def fmt(x: float, places: int = 3) -> str:
    return "n/a" if x is None or math.isnan(x) else f"{x:.{places}f}"


def pct(x: float) -> str:
    return "n/a" if x is None or math.isnan(x) else f"{x * 100:.1f}%"
