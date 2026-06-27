"""Service container.

A single object that owns every collaborator an agent might need, constructed once
and injected into the orchestrator. This keeps agents free of global lookups and
makes the whole swarm trivially testable with fakes.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.integrations.event_bus import EventBus, get_event_bus
from app.integrations.notifications import NotificationGateway
from app.integrations.persistence import SupabaseStore
from app.integrations.voice import VoiceGateway
from app.services.dialogue import NegotiatorVoice, VictimSimulator
from app.services.llm import LLMClient
from app.services.risk_engine import RiskEngine
from app.services.scam_taxonomy import ScamTaxonomy


class Runtime:
    def __init__(self, settings: Settings | None = None, bus: EventBus | None = None) -> None:
        self.settings = settings or get_settings()
        self.bus = bus or get_event_bus()
        self.llm = LLMClient(self.settings)
        self.risk = RiskEngine()
        self.taxonomy = ScamTaxonomy()
        self.voice = VoiceGateway(self.settings)
        self.notify = NotificationGateway(self.settings)
        self.store = SupabaseStore(self.settings)
        self.negotiator = NegotiatorVoice(self.llm)
        self.simulator = VictimSimulator()
