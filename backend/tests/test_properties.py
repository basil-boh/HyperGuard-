"""Option E — properties the risk engine must hold for *any* input, not just fixtures.

Example-based tests only prove the engine works on the examples someone thought of.
These assert invariants over generated inputs, which is where the surprises live.

No new dependency: a small deterministic search stands in for Hypothesis.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas import CustomerProfile, TransactionRequest
from app.services.risk_engine import RiskEngine

ENGINE = RiskEngine()
SEEDS = range(200)


def _customer(rng: random.Random) -> CustomerProfile:
    base = rng.uniform(50, 5_000)
    return CustomerProfile(
        id="p", name="Property Tester", phone="+6580000000",
        age=rng.choice([None, 25, 45, 71, 83]),
        vulnerability_flags=rng.choice([[], ["elderly"], ["elderly", "recent_bereavement"]]),
        baseline_avg_amount=base,
        baseline_std_amount=rng.uniform(1, base),
        typical_hour_start=rng.randint(5, 10),
        typical_hour_end=rng.randint(18, 23),
        typical_velocity_per_day=rng.uniform(0.1, 5),
        known_payees=[f"Payee {i}" for i in range(rng.randint(0, 5))],
        known_payee_phones=[f"+6590000{i:03d}" for i in range(rng.randint(0, 5))],
    )


def _txn(rng: random.Random, cust: CustomerProfile, **over) -> TransactionRequest:
    fields = dict(
        id="t", customer_id=cust.id,
        amount=rng.uniform(1, 60_000),
        payee_name=rng.choice(cust.known_payees or ["Someone New"]),
        payee_account="12345678",
        payee_phone=rng.choice([None] + cust.known_payee_phones),
        payee_country=rng.choice(["SG", "MY", None]),
        memo=rng.choice([None, "rent", "urgent safe account"]),
        requested_at=datetime.now(timezone.utc).replace(hour=rng.randint(0, 23)),
        recent_transfer_count_24h=rng.randint(0, 20),
    )
    fields.update(over)
    return TransactionRequest(**fields)


@pytest.mark.parametrize("seed", SEEDS)
def test_score_is_a_probability(seed: int) -> None:
    rng = random.Random(seed)
    cust = _customer(rng)
    a = ENGINE.assess(cust, _txn(rng, cust))
    assert 0.0 <= a.score <= 1.0, f"score escaped [0,1]: {a.score}"


@pytest.mark.parametrize("seed", SEEDS)
def test_deterministic(seed: int) -> None:
    """Same input, same score — twice. An audit trail nobody can reproduce is not one."""
    rng = random.Random(seed)
    cust = _customer(rng)
    txn = _txn(rng, cust)
    assert ENGINE.assess(cust, txn).score == ENGINE.assess(cust, txn).score


@pytest.mark.parametrize("seed", range(60))
def test_more_money_never_looks_safer(seed: int) -> None:
    """Monotonicity in amount. Everything else fixed, a larger transfer must not score lower.

    If this ever fails, some signal is non-monotone and the score stops being explainable —
    you could not tell a customer "the amount is why" and be telling the truth.
    """
    rng = random.Random(seed)
    cust = _customer(rng)
    base = _txn(rng, cust, amount=cust.baseline_avg_amount)
    scores = []
    for mult in (1, 2, 4, 8, 16):
        txn = base.model_copy(update={"amount": cust.baseline_avg_amount * mult})
        scores.append(ENGINE.assess(cust, txn).score)
    for lo, hi in zip(scores, scores[1:]):
        assert hi >= lo - 1e-9, f"score fell as the amount rose: {scores}"


@pytest.mark.parametrize("seed", SEEDS)
def test_every_signal_carries_a_reason(seed: int) -> None:
    """The explainability claim, enforced. A signal with no readable reason is a number
    pretending to be an explanation."""
    rng = random.Random(seed)
    cust = _customer(rng)
    a = ENGINE.assess(cust, _txn(rng, cust))
    for s in a.signals:
        assert s.label.strip(), f"{s.code} has no label"
        assert s.detail.strip(), f"{s.code} has no detail"
        assert s.severity in {"info", "warn", "alarm"}, f"{s.code} bad severity {s.severity}"
    assert a.rationale.strip(), "assessment has no rationale"


@pytest.mark.parametrize("seed", SEEDS)
def test_band_matches_score(seed: int) -> None:
    rng = random.Random(seed)
    cust = _customer(rng)
    a = ENGINE.assess(cust, _txn(rng, cust))
    expected = (
        "critical" if a.score >= 0.85
        else "high" if a.score >= 0.6
        else "elevated" if a.score >= 0.35
        else "minimal"
    )
    assert a.band.value == expected, f"score {a.score} banded as {a.band.value}"


@pytest.mark.parametrize("seed", range(60))
def test_a_boring_transfer_stays_below_the_intervention_threshold(seed: int) -> None:
    """The restraint claim: a known payee, a normal amount, in normal hours, must not
    trigger a phone call. This is the property that keeps the product deployable."""
    rng = random.Random(seed)
    cust = _customer(rng)
    if not cust.known_payees:
        pytest.skip("customer has no established payees")
    txn = _txn(
        rng, cust,
        amount=cust.baseline_avg_amount,
        payee_name=cust.known_payees[0],
        payee_phone=None,
        payee_country="SG",
        memo="groceries",
        requested_at=datetime.now(timezone.utc).replace(hour=cust.typical_hour_start + 1),
        recent_transfer_count_24h=1,
    )
    score = ENGINE.assess(cust, txn).score
    assert score < 0.58, f"an ordinary transfer scored {score} and would have called the customer"


def test_contribution_shares_are_coherent() -> None:
    """Contributions are shown to operators as a bar chart. They must sum to the score."""
    rng = random.Random(99)
    cust = _customer(rng)
    for _ in range(50):
        a = ENGINE.assess(cust, _txn(rng, cust))
        if not a.signals:
            continue
        total = sum(s.contribution for s in a.signals)
        assert total == pytest.approx(a.score, abs=0.02), (
            f"contributions sum to {total} but score is {a.score}"
        )


def test_unknown_payee_is_never_free() -> None:
    """The engine's own docstring calls first-time payee the strongest predictor. Assert it
    actually moves the score, so the claim can't rot silently."""
    rng = random.Random(5)
    cust = _customer(rng)
    cust.known_payees = ["Established Payee"]
    common = dict(
        amount=cust.baseline_avg_amount, payee_phone=None, payee_country="SG",
        memo=None, requested_at=datetime.now(timezone.utc).replace(hour=cust.typical_hour_start + 1),
        recent_transfer_count_24h=0,
    )
    known = ENGINE.assess(cust, _txn(rng, cust, payee_name="Established Payee", **common)).score
    fresh = ENGINE.assess(cust, _txn(rng, cust, payee_name="Never Seen Before", **common)).score
    assert fresh > known, f"a first-time payee scored no higher than a known one ({fresh} vs {known})"
