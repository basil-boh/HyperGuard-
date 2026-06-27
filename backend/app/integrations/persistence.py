"""Optional durable store (Supabase / Postgres).

Best-effort by design: when credentials are absent, or a write fails, the swarm
keeps running and simply isn't persisted. The supabase client is synchronous, so
writes are off-loaded to a worker thread to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.schemas import CustomerProfile, Decision, InterventionOutcome

logger = logging.getLogger("hyperguard.store")


class SupabaseStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    @property
    def enabled(self) -> bool:
        return self._settings.persistence_enabled

    def _connect(self):
        if not self.enabled:
            return None
        if self._client is None:
            try:
                from supabase import create_client

                self._client = create_client(
                    self._settings.supabase_url, self._settings.supabase_service_key
                )
            except Exception as exc:  # pragma: no cover - dep optional
                logger.warning("Supabase client unavailable: %s", exc)
                return None
        return self._client

    async def save_outcome(
        self, case_id: str, customer: CustomerProfile, outcome: InterventionOutcome
    ) -> None:
        client = self._connect()
        if client is None:
            return
        txn = (
            outcome.evidence.transaction.model_dump(mode="json")
            if (outcome.evidence and outcome.evidence.transaction)
            else {"id": outcome.transaction_id}
        )
        row = {
            "case_id": case_id,
            "user_id": customer.id,
            "user_name": customer.name,
            "created_at": outcome.decided_at.isoformat(),
            "transaction": txn,
            "decision": outcome.decision.value,
            "status": "approved" if outcome.decision == Decision.approve else "blocked",
            "risk_score": outcome.risk.score,
            "band": outcome.risk.band.value,
            "risk_signals": [s.model_dump() for s in outcome.risk.signals],
            "rationale": outcome.risk.rationale,
            "scam_type": outcome.classification.archetype.value
            if outcome.classification
            else None,
            "classification": outcome.classification.model_dump(mode="json")
            if outcome.classification
            else None,
            "guardian_alerts": [a.model_dump(mode="json") for a in outcome.guardian_alerts],
            "transcript": [t.model_dump(mode="json") for t in outcome.transcript],
            "evidence": outcome.evidence.model_dump(mode="json") if outcome.evidence else None,
            "narrative": outcome.narrative,
        }
        try:
            await asyncio.to_thread(lambda: client.table("cases").upsert(row).execute())
        except Exception as exc:  # pragma: no cover - network
            logger.warning("Persisting case %s failed: %s", case_id, exc)
