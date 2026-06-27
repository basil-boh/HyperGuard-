"""Per-case event recorder.

The mobile wallet can't hold a websocket reliably across Expo Go / LAN, so instead
of pushing, it polls. This registry subscribes to the swarm bus once and buckets
every event by case id, plus stores the final outcome. `GET /wallet/intervention/{id}`
just reads from here, giving the app a live, replayable view of the agents working.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from app.domain.events import EventType, SwarmEvent
from app.integrations.event_bus import get_event_bus
from app.schemas import InterventionOutcome

logger = logging.getLogger("hyperguard.registry")

_MAX_CASES = 200


class InterventionRegistry:
    def __init__(self) -> None:
        self._cases: dict[str, dict] = {}
        self._order: list[str] = []
        self._task: asyncio.Task | None = None

    def _bucket(self, case_id: str) -> dict:
        bucket = self._cases.get(case_id)
        if bucket is None:
            bucket = {
                "events": [], "outcome": None, "done": False,
                # case context captured from the event stream, for the voice follow-up
                "customer": None, "transaction": None, "risk": None, "classification": None,
                # voice follow-up results
                "context": [], "assessment": None, "escalation": None, "report": None,
            }
            self._cases[case_id] = bucket
            self._order.append(case_id)
            # evict oldest to bound memory
            while len(self._order) > _MAX_CASES:
                self._cases.pop(self._order.pop(0), None)
        return bucket

    def record(self, event: SwarmEvent) -> None:
        bucket = self._bucket(event.case_id)
        bucket["events"].append(event.envelope())
        p = event.payload or {}
        if event.type == EventType.case_opened:
            bucket["customer"] = p.get("customer")
            bucket["transaction"] = p.get("transaction")
        elif event.type == EventType.risk_scored:
            bucket["risk"] = p.get("risk")
        elif event.type == EventType.scam_classified:
            bucket["classification"] = p.get("classification")
        elif event.type == EventType.case_closed:
            bucket["done"] = True

    def set_outcome(self, case_id: str, outcome: InterventionOutcome) -> None:
        bucket = self._bucket(case_id)
        bucket["outcome"] = outcome.model_dump(mode="json")
        bucket["done"] = True

    # ── Voice follow-up state ────────────────────────────────────────────────────
    def add_answer(self, case_id: str, question: str, answer: str) -> None:
        self._bucket(case_id)["context"].append({"question": question, "answer": answer})

    def set_followup(self, case_id: str, *, assessment: dict | None = None,
                     escalation: dict | None = None, report: str | None = None) -> None:
        bucket = self._bucket(case_id)
        if assessment is not None:
            bucket["assessment"] = assessment
        if escalation is not None:
            bucket["escalation"] = escalation
        if report is not None:
            bucket["report"] = report

    def get(self, case_id: str) -> dict | None:
        return self._cases.get(case_id)

    # ── Bus consumer lifecycle ───────────────────────────────────────────────────
    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _consume(self) -> None:
        bus = get_event_bus()
        with bus.subscribe() as sub:
            try:
                async for event in sub.stream():
                    self.record(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("registry consumer ended: %s", exc)


_registry: InterventionRegistry | None = None


def get_registry() -> InterventionRegistry:
    global _registry
    if _registry is None:
        _registry = InterventionRegistry()
    return _registry
