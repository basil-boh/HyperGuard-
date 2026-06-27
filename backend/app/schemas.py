"""Domain models shared across every agent and the API surface.

These are the contract between the swarm, the persistence layer, and the
frontend. Keep them serialisable and free of behaviour.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enumerations ───────────────────────────────────────────────────────────────
class ScamArchetype(str, Enum):
    bank_impersonation = "bank_impersonation"
    government_impersonation = "government_impersonation"
    investment = "investment_scam"
    romance = "romance_scam"
    job = "job_scam"
    tech_support = "tech_support_scam"
    unknown = "unknown"
    none = "none"


class TransactionStatus(str, Enum):
    pending = "pending"
    intervening = "intervening"
    approved = "approved"
    blocked = "blocked"
    completed = "completed"


class RiskBand(str, Enum):
    minimal = "minimal"
    elevated = "elevated"
    high = "high"
    critical = "critical"


class VerificationStatus(str, Enum):
    unknown = "unknown"
    verified = "verified"
    failed = "failed"
    coerced = "coerced"


class Decision(str, Enum):
    approve = "approve"
    block = "block"
    hold = "hold"


class Speaker(str, Enum):
    agent = "agent"
    customer = "customer"
    system = "system"


# ── Entities ───────────────────────────────────────────────────────────────────
class TrustedContact(BaseModel):
    id: str
    name: str
    phone: str
    relationship: str
    priority: int = 1


class CustomerProfile(BaseModel):
    id: str
    name: str
    phone: str
    age: int | None = None
    vulnerability_flags: list[str] = Field(default_factory=list)
    baseline_avg_amount: float
    baseline_std_amount: float
    typical_hour_start: int = 8
    typical_hour_end: int = 22
    typical_velocity_per_day: float = 1.5
    known_payees: list[str] = Field(default_factory=list)
    # Phone numbers (E.164) this customer has paid before or saved — the PayNow
    # analogue of `known_payees`, used by the unknown-number signal.
    known_payee_phones: list[str] = Field(default_factory=list)
    # ISO country the customer banks in; anything else is "overseas".
    home_country: str = "SG"
    trusted_contacts: list[TrustedContact] = Field(default_factory=list)


class TransactionRequest(BaseModel):
    id: str
    customer_id: str
    amount: float
    currency: str = "SGD"
    payee_name: str
    payee_account: str
    # PayNow-style transfers target a mobile number; account stays for bank transfers.
    payee_phone: str | None = None
    payee_country: str | None = None  # derived from payee_phone at build time
    channel: str = "mobile_app"
    memo: str | None = None
    requested_at: datetime
    recent_transfer_count_24h: int = 0
    status: TransactionStatus = TransactionStatus.pending
    # Optional, demo-only: a script the simulated victim follows when no live caller.
    victim_script: list[str] | None = None
    seeded_archetype: ScamArchetype | None = None


# ── Risk ───────────────────────────────────────────────────────────────────────
class RiskSignal(BaseModel):
    code: str
    label: str
    contribution: float  # 0..1 share of the final score this signal drove
    severity: str  # "info" | "warn" | "alarm"
    detail: str


class RiskAssessment(BaseModel):
    transaction_id: str
    score: float
    band: RiskBand
    signals: list[RiskSignal]
    rationale: str
    model_version: str = "twin-heuristic-1"


# ── Conversation ───────────────────────────────────────────────────────────────
class TranscriptTurn(BaseModel):
    index: int
    speaker: Speaker
    text: str
    ts: datetime
    tags: list[str] = Field(default_factory=list)


class ScamClassification(BaseModel):
    archetype: ScamArchetype
    title: str
    confidence: float
    indicators: list[str]
    guidance: str  # what the negotiator should say back to the customer
    # ── Educator debrief: shown to the customer after the call ──────────────────
    mentions: list[str] = Field(default_factory=list)  # the customer's own phrases that matched
    how_it_works: str = ""  # plain-language explanation of this scam's mechanics
    prevention: list[str] = Field(default_factory=list)  # how to avoid it next time


# ── Guardian ───────────────────────────────────────────────────────────────────
class GuardianAlert(BaseModel):
    contact: TrustedContact
    channel: str  # "sms" | "voice" | "whatsapp"
    status: str  # "queued" | "delivered" | "acknowledged" | "failed"
    message: str
    acknowledged: bool = False


# ── Recovery ───────────────────────────────────────────────────────────────────
class TimelineEntry(BaseModel):
    at: datetime
    actor: str
    event: str


class EvidencePackage(BaseModel):
    case_id: str
    transaction: TransactionRequest
    risk: RiskAssessment
    classification: ScamClassification | None
    transcript: list[TranscriptTurn]
    guardian_alerts: list[GuardianAlert]
    timeline: list[TimelineEntry]
    generated_at: datetime
    executive_summary: str
    recommended_actions: list[str]


# ── Outcome ────────────────────────────────────────────────────────────────────
class InterventionOutcome(BaseModel):
    transaction_id: str
    decision: Decision
    verification: VerificationStatus
    risk: RiskAssessment
    classification: ScamClassification | None
    transcript: list[TranscriptTurn]
    guardian_alerts: list[GuardianAlert]
    evidence: EvidencePackage | None
    decided_at: datetime
    narrative: str
