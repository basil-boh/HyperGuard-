"""Operator override registry.

Consoles are not just spectators: an operator can freeze the transfer, force a
guardian escalation, or pull the case to a human reviewer. The flags land here
(keyed by case) and the swarm consults them at its decision points; every
override is also published on the bus so all connected consoles see who did what.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

OVERRIDE_ACTIONS = ("escalate_guardian", "freeze_transfer", "human_handoff")


@dataclass
class CaseOverrides:
    frozen: bool = False
    handoff: bool = False
    escalated: bool = False
    frozen_by: str | None = None
    handoff_by: str | None = None


class OverrideRegistry:
    """Per-case operator flags, bounded so abandoned cases age out."""

    def __init__(self, max_cases: int = 256) -> None:
        self._cases: OrderedDict[str, CaseOverrides] = OrderedDict()
        self._max = max_cases

    def for_case(self, case_id: str) -> CaseOverrides:
        if case_id not in self._cases:
            self._cases[case_id] = CaseOverrides()
            while len(self._cases) > self._max:
                self._cases.popitem(last=False)
        return self._cases[case_id]

    def peek(self, case_id: str) -> CaseOverrides | None:
        return self._cases.get(case_id)


_registry = OverrideRegistry()


def get_override_registry() -> OverrideRegistry:
    return _registry
