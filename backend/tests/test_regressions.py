"""Option E — the three known defects, pinned as executable specifications.

Each test below describes the behaviour the system *should* have and is marked
`xfail(strict=True)` because it does not have it yet. That marker does real work:

* CI stays green while the bug is open — an xfail is expected, not a failure.
* The moment someone fixes the bug the test **passes**, and `strict=True` turns an
  unexpected pass into a hard failure. You cannot fix one of these by accident and leave
  the test behind; the suite forces you to delete the marker and lock the fix in.

A bug described in a document rots. A bug described in a failing test cannot.
See FUNCTIONALITY.md for how each was found.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.data.seed_data import list_scenarios
from app.schemas import Decision
from app.wallet.store import Bank


# ── 1. Scenario cases can never be persisted ───────────────────────────────────────
@pytest.mark.xfail(
    strict=True,
    reason=(
        "FUNCTIONALITY.md #1 — SupabaseStore.save_outcome writes customer.id into "
        "cases.user_id, which has a foreign key onto users(id). Scenario personas "
        "('cust_may') live in a different namespace from wallet accounts ('acc_may'), so "
        "every scenario case fails to persist with a 23503 and is lost on restart. The "
        "warning is swallowed, so nothing surfaces it."
    ),
)
def test_scenario_personas_are_valid_wallet_users() -> None:
    """Anything written to `cases.user_id` must be a real wallet user id.

    Fix by either upserting a users row for scenario personas before saving, or by
    dropping the FK on cases.user_id and treating it as a soft reference.
    """
    wallet_user_ids = set(Bank().accounts)
    scenario_customer_ids = {s["customer_id"] for s in list_scenarios()}
    orphans = scenario_customer_ids - wallet_user_ids
    assert not orphans, (
        f"these scenario personas have no wallet user row, so their cases cannot "
        f"satisfy cases_user_id_fkey: {sorted(orphans)}"
    )


# ── 2. A blocked transfer can never be released ────────────────────────────────────
@pytest.mark.xfail(
    strict=True,
    reason=(
        "FUNCTIONALITY.md #2 — the post-call adjudicator can conclude "
        "recommended_action='clear', but nothing consumes that verdict. There is no "
        "un-block path in backend, frontend or mobile, so a customer who fully explains a "
        "legitimate transfer stays blocked permanently. This is also the ceiling on "
        "Option C: the conversation can only ever add blocks."
    ),
)
def test_a_cleared_assessment_releases_the_transfer() -> None:
    """A 'clear' verdict from the follow-up must be able to reverse a block.

    Fix by having finalize_followup act on recommended_action: release the held transfer,
    emit a decision_revised event, and update the case record.
    """
    from app.wallet import followup

    assert hasattr(followup, "release_transfer") or hasattr(followup, "revise_decision"), (
        "finalize_followup has no way to reverse a block — a 'clear' assessment is computed, "
        "emitted, persisted, and then ignored"
    )


# ── 3. Anyone can inject answers into a live case ──────────────────────────────────
@pytest.mark.xfail(
    strict=True,
    reason=(
        "FUNCTIONALITY.md #4 — /twilio/voice/* perform no signature validation and take "
        "case_id from a query parameter. Anyone who guesses a case id can POST arbitrary "
        "'customer answers', which then feed the LLM adjudicator, the guardian SMS and the "
        "incident report."
    ),
)
def test_forged_twilio_webhook_is_rejected() -> None:
    """An unsigned POST to the voice webhook must not be accepted.

    Fix with twilio.request_validator.RequestValidator against X-Twilio-Signature, as a
    dependency on the router.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/twilio/voice/answer?case_id=HG-FORGED&step=0",
        data={"SpeechResult": "injected by an attacker"},
    )
    assert resp.status_code in (401, 403), (
        f"forged webhook accepted with {resp.status_code} — an unauthenticated caller can "
        f"write into any case's conversation"
    )


# ── Guards on the fixes, so they can't regress silently ────────────────────────────
def test_blocked_transfer_does_not_move_money() -> None:
    """Whatever else changes about reversal, a block must never debit the account.

    Not xfail — this passes today, and it is the invariant any future release path has to
    keep. Written here so a reversal feature can't quietly break it.
    """
    from app.data.seed_data import build_scenario

    acc = Bank().app_account()
    before = acc.balance
    customer, txn = build_scenario("police_impersonation")
    txn.customer_id = acc.owner.id

    entry = acc.apply_outcome(txn, _blocked_outcome(txn), case_id="HG-TEST")

    assert entry.status == "blocked"
    assert acc.balance == before, (
        f"a blocked transfer moved money: {before} → {acc.balance}"
    )

    approved = acc.apply_outcome(txn, _approved_outcome(txn), case_id="HG-TEST-2")
    assert approved.status == "approved"
    assert acc.balance == before - txn.amount, "an approved transfer failed to debit"


def _blocked_outcome(txn):
    return _outcome(txn, Decision.block)


def _approved_outcome(txn):
    return _outcome(txn, Decision.approve)


def _outcome(txn, decision: Decision):
    from app.schemas import (
        InterventionOutcome, RiskAssessment, RiskBand, VerificationStatus,
    )

    return InterventionOutcome(
        transaction_id=txn.id,
        decision=decision,
        verification=VerificationStatus.unknown,
        risk=RiskAssessment(
            transaction_id=txn.id, score=0.9, band=RiskBand.critical, signals=[],
            rationale="test",
        ),
        classification=None,
        transcript=[],
        guardian_alerts=[],
        evidence=None,
        decided_at=datetime.now(timezone.utc),
        narrative="test",
    )


def test_every_seeded_scenario_still_reaches_a_decision() -> None:
    """A smoke guard on the scenario fixtures the demo depends on."""
    from app.data.seed_data import build_scenario

    scenarios = list_scenarios()
    assert scenarios, "no scenarios registered"
    for s in scenarios:
        customer, txn = build_scenario(s["id"])
        assert customer is not None and txn is not None
        assert txn.amount > 0
        # Timezone-aware and anchored to roughly now — the fixtures pin an hour-of-day, so
        # a scenario can legitimately sit a few hours either side of the current clock.
        assert txn.requested_at.tzinfo is not None, f"{s['id']} has a naive timestamp"
        age_days = abs((datetime.now(timezone.utc) - txn.requested_at).total_seconds()) / 86_400
        assert age_days < 30, f"{s['id']} timestamp is {age_days:.0f} days out"
