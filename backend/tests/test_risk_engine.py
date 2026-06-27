"""Risk engine, the deterministic core deserves deterministic tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import CustomerProfile, RiskBand, TransactionRequest
from app.services.risk_engine import RiskEngine


def _customer(**overrides) -> CustomerProfile:
    base = dict(
        id="c1",
        name="Test User",
        phone="+650000000",
        baseline_avg_amount=300.0,
        baseline_std_amount=150.0,
        typical_hour_start=9,
        typical_hour_end=20,
        known_payees=["Grocer", "Landlord"],
    )
    base.update(overrides)
    return CustomerProfile(**base)


def _txn(**overrides) -> TransactionRequest:
    base = dict(
        id="t1",
        customer_id="c1",
        amount=300.0,
        payee_name="Grocer",
        payee_account="000",
        requested_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return TransactionRequest(**base)


def test_in_pattern_transfer_scores_low() -> None:
    risk = RiskEngine().assess(_customer(), _txn())
    assert risk.score < 0.35
    assert risk.band == RiskBand.minimal
    assert risk.signals == []


def test_coercion_scenario_scores_critical() -> None:
    risk = RiskEngine().assess(
        _customer(vulnerability_flags=["elderly"]),
        _txn(
            amount=8000.0,
            payee_name="Unknown Mule",
            requested_at=datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc),
            memo="urgent safe account, do not tell anyone",
            recent_transfer_count_24h=5,
        ),
    )
    assert risk.score >= 0.85
    assert risk.band == RiskBand.critical
    codes = {s.code for s in risk.signals}
    assert {"new_payee", "amount_anomaly", "off_hours", "pressure_language"} <= codes


def test_contributions_are_bounded_by_score() -> None:
    risk = RiskEngine().assess(
        _customer(), _txn(amount=5000.0, payee_name="New Person")
    )
    total = sum(s.contribution for s in risk.signals)
    assert total <= risk.score + 1e-6
