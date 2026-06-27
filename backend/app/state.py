"""The shared state threaded through the LangGraph swarm.

`transcript` uses an additive reducer so the negotiator↔educator loop can append
turns incrementally without clobbering earlier ones; every other field is
last-write-wins.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from app.schemas import (
    CustomerProfile,
    Decision,
    EvidencePackage,
    GuardianAlert,
    RiskAssessment,
    ScamClassification,
    TranscriptTurn,
    TransactionRequest,
    VerificationStatus,
)


class SwarmState(TypedDict, total=False):
    case_id: str
    customer: CustomerProfile
    transaction: TransactionRequest

    risk: RiskAssessment | None
    transcript: Annotated[list[TranscriptTurn], add]
    classification: ScamClassification | None
    verification: VerificationStatus
    guardian_alerts: list[GuardianAlert]
    decision: Decision | None
    evidence: EvidencePackage | None

    turn_count: int
    narrative: str
