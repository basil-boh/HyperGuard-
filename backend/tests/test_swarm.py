"""End-to-end swarm behaviour across the seeded scenarios."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.data.seed_data import build_scenario
from app.graph import SwarmOrchestrator
from app.schemas import Decision, ScamArchetype


@pytest.fixture(scope="module", autouse=True)
def _fast_mode():
    get_settings().demo_step_delay = 0.0


@pytest.fixture
def orchestrator() -> SwarmOrchestrator:
    return SwarmOrchestrator()


async def test_police_impersonation_is_blocked_and_recovered(orchestrator) -> None:
    customer, txn = build_scenario("police_impersonation")
    outcome = await orchestrator.run(customer, txn)

    assert outcome.decision == Decision.block
    assert outcome.classification is not None
    assert outcome.classification.archetype == ScamArchetype.government_impersonation
    assert outcome.guardian_alerts, "a trusted contact should have been alerted"
    assert outcome.evidence is not None
    assert outcome.evidence.recommended_actions


async def test_legitimate_transfer_is_approved(orchestrator) -> None:
    customer, txn = build_scenario("legitimate_transfer")
    outcome = await orchestrator.run(customer, txn)

    assert outcome.decision == Decision.approve
    assert outcome.evidence is None


async def test_post_hoc_case_skips_to_recovery(orchestrator) -> None:
    customer, txn = build_scenario("post_hoc_recovery")
    outcome = await orchestrator.run(customer, txn)

    assert outcome.evidence is not None
    assert outcome.transcript == []  # no live call on a post-hoc report


async def test_investment_scam_is_blocked(orchestrator) -> None:
    customer, txn = build_scenario("investment_scam")
    outcome = await orchestrator.run(customer, txn)

    assert outcome.decision == Decision.block
    assert outcome.classification.archetype == ScamArchetype.investment
