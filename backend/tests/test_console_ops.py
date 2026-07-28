"""Operator-channel behaviour: resume replay, override flags, arbiter deference."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.data.seed_data import build_scenario
from app.domain.events import EventType, SwarmEvent
from app.graph import SwarmOrchestrator
from app.integrations.event_bus import EventBus
from app.schemas import Decision, TransactionStatus
from app.services.overrides import get_override_registry


@pytest.fixture(scope="module", autouse=True)
def _hermetic():
    s = get_settings()
    s.demo_step_delay = 0.0
    s.force_demo_mode = True
    s.public_base_url = None
    s.supabase_url = None
    s.supabase_service_key = None


def _event(case_id: str = "HG-TEST") -> SwarmEvent:
    return SwarmEvent(type=EventType.risk_scored, case_id=case_id)


def test_replay_since_returns_only_the_gap() -> None:
    bus = EventBus()
    events = [_event() for _ in range(5)]
    bus._replay.extend(events)

    assert bus.replay_since(events[2].id) == events[3:]
    assert bus.replay_since(None) == events
    assert bus.replay_since("no-such-id") == events  # unknown id → full replay


async def test_operator_freeze_forces_block() -> None:
    orchestrator = SwarmOrchestrator()
    customer, txn = build_scenario("legitimate_transfer")
    case_id = "HG-FREEZETEST"
    flags = get_override_registry().for_case(case_id)
    flags.frozen, flags.frozen_by = True, "cobalt-7f"

    outcome = await orchestrator.run(customer, txn, case_id=case_id)

    assert outcome.decision == Decision.block
    assert "operator override" in outcome.narrative.lower()


async def test_operator_handoff_holds_the_case() -> None:
    orchestrator = SwarmOrchestrator()
    customer, txn = build_scenario("legitimate_transfer")
    case_id = "HG-HANDOFFTEST"
    get_override_registry().for_case(case_id).handoff = True

    outcome = await orchestrator.run(customer, txn, case_id=case_id)

    assert outcome.decision == Decision.hold
    assert txn.status == TransactionStatus.intervening
