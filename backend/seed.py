"""Scenario runner & smoke test.

Runs every seeded scenario through the full swarm without a server or any API key,
printing the decision and the swarm's narrative. Doubles as a one-command sanity
check that the orchestration is wired correctly.

    python seed.py            # run all scenarios
    python seed.py police_impersonation   # run one
"""

from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.data.seed_data import build_scenario, list_scenarios
from app.graph import SwarmOrchestrator

_DIVIDER = "─" * 78


async def _run(scenario_id: str, orch: SwarmOrchestrator) -> None:
    customer, txn = build_scenario(scenario_id)
    outcome = await orch.run(customer, txn)
    scam = outcome.classification.title if outcome.classification else "—"
    print(_DIVIDER)
    print(f"  scenario   {scenario_id}")
    print(f"  customer   {customer.name}  ·  {txn.currency} {txn.amount:,.0f} → {txn.payee_name}")
    print(f"  risk       {outcome.risk.score:.0%}  ({outcome.risk.band.value})")
    print(f"  scam       {scam}")
    print(f"  decision   {outcome.decision.value.upper()}")
    print(f"  guardians  {len(outcome.guardian_alerts)} alerted")
    print(f"  evidence   {'built' if outcome.evidence else 'n/a'}")
    print(f"  narrative  {outcome.narrative}")


async def main() -> None:
    # Run hot, no synthetic pacing for the smoke test.
    settings = get_settings()
    settings.demo_step_delay = 0.0

    orch = SwarmOrchestrator()
    targets = sys.argv[1:] or [s["id"] for s in list_scenarios()]

    print(f"\nHyperGuard smoke test, capabilities: {settings.capability_report()}\n")
    for scenario_id in targets:
        await _run(scenario_id, orch)
    print(_DIVIDER)
    print()


if __name__ == "__main__":
    asyncio.run(main())
