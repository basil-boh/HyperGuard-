"""Bank account, deterministic balance + ledger behaviour."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    Decision,
    InterventionOutcome,
    RiskAssessment,
    RiskBand,
    VerificationStatus,
)
from app.wallet.store import Bank


def _account():
    # Fresh bank per test for isolation; the app user is "Alex Tan".
    return Bank().app_account()


def _outcome(decision: Decision, score: float) -> InterventionOutcome:
    return InterventionOutcome(
        transaction_id="t1",
        decision=decision,
        verification=VerificationStatus.unknown,
        risk=RiskAssessment(
            transaction_id="t1", score=score, band=RiskBand.high, signals=[], rationale="x"
        ),
        classification=None,
        transcript=[],
        guardian_alerts=[],
        evidence=None,
        decided_at=datetime.now(timezone.utc),
        narrative="n",
    )


def test_scam_recipient_carries_hidden_archetype() -> None:
    acc = _account()
    quick = acc.find_recipient("rcp_quick")
    assert quick is not None and quick.archetype is not None
    # ...but it is never leaked through the API serialisation.
    assert all("archetype" not in r for r in acc.list_recipients())


def test_blocked_transfer_does_not_move_money() -> None:
    acc = _account()
    start = acc.balance
    txn = acc.build_transaction(
        payee_name="Quick Holdings Pte Ltd", payee_account="x", amount=8000, memo=None, archetype=None
    )
    acc.apply_outcome(txn, _outcome(Decision.block, 0.97), "HG-1")
    assert acc.balance == start
    assert acc.ledger[0].status == "blocked"


def test_approved_transfer_deducts_balance() -> None:
    acc = _account()
    start = acc.balance
    txn = acc.build_transaction(
        payee_name="NTUC FairPrice", payee_account="x", amount=80, memo="groceries", archetype=None
    )
    acc.apply_outcome(txn, _outcome(Decision.approve, 0.05), "HG-2")
    assert acc.balance == start - 80
    assert acc.ledger[0].status == "approved"


def test_adding_contact_grows_next_of_kin() -> None:
    acc = _account()
    before = len(acc.list_contacts())
    acc.add_contact("Jamie Tan", "+6580000099", "daughter")
    assert len(acc.list_contacts()) == before + 1


def test_bank_seeds_multiple_customers_and_cases() -> None:
    bank = Bank()
    assert len(bank.list_accounts()) >= 5
    assert len(bank.cases) >= 4
    ov = bank.overview()
    assert ov["blocked"] >= 4 and ov["amount_protected"] > 0
