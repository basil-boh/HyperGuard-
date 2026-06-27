"""Optional durable store (Supabase / Postgres).

Best-effort by design: when credentials are absent, or a write fails, the swarm
keeps running and simply isn't persisted. The supabase client is synchronous, so
writes are off-loaded to a worker thread to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.schemas import CustomerProfile, InterventionOutcome

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
        row = {
            "case_id": case_id,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "decision": outcome.decision.value,
            "risk_score": outcome.risk.score,
            "scam_type": outcome.classification.archetype.value
            if outcome.classification
            else None,
            "outcome": outcome.model_dump(mode="json"),
        }
        try:
            await asyncio.to_thread(lambda: client.table("cases").upsert(row).execute())
        except Exception as exc:  # pragma: no cover - network
            logger.warning("Persisting case %s failed: %s", case_id, exc)
