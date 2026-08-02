"""The evaluation case — one labelled transfer, with everything each option needs.

A case carries three independent layers:

* **features** — the numeric/categorical transfer facts the risk engine scores (Option A)
* **transcript** — what the customer said on the call, which the classifier reads (Option B)
* **truth** — the label, the archetype, and *which signals should have fired* (Option D)

Keeping them separate is deliberate: the risk engine never sees the transcript, and the
classifier never sees the amount, so neither can launder the label through the other.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas import CustomerProfile, ScamArchetype, TransactionRequest


class Slice(str, Enum):
    """Which population a case belongs to. The two legit slices carry the weight —
    a scam detector that never sees a plausible false positive is untested."""

    scam_clean = "scam_clean"
    scam_adversarial = "scam_adversarial"  # same scams, reworded to dodge keyword matching
    legit_suspicious = "legit_suspicious"  # looks like fraud, isn't — the expensive mistakes
    legit_obvious = "legit_obvious"


class EvalCase(BaseModel):
    id: str
    slice: Slice
    is_scam: bool
    archetype: ScamArchetype  # `none` for legitimate cases

    # What the Digital Twin scores.
    customer: CustomerProfile
    transaction: TransactionRequest

    # What the Educator reads: the customer's own words, no agent turns.
    utterances: list[str] = Field(default_factory=list)

    # Which risk signal codes a correct model should fire, for Option D's fidelity check.
    expected_signals: list[str] = Field(default_factory=list)

    # Free-text note on why this case is what it is — for reading failures by hand.
    rationale: str = ""

    @property
    def speech(self) -> str:
        return " ".join(self.utterances)


class Dataset(BaseModel):
    version: str
    generated_at: datetime
    generator: str  # "llm" | "template" — how the utterances were produced
    notes: str
    cases: list[EvalCase]

    def by_slice(self, *slices: Slice) -> list[EvalCase]:
        wanted = set(slices)
        return [c for c in self.cases if c.slice in wanted]

    @property
    def scams(self) -> list[EvalCase]:
        return [c for c in self.cases if c.is_scam]

    @property
    def legit(self) -> list[EvalCase]:
        return [c for c in self.cases if not c.is_scam]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.cases:
            out[c.slice.value] = out.get(c.slice.value, 0) + 1
        return out


def utc(days_ago: float = 0, hour: int | None = None) -> datetime:
    at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    if hour is not None:
        at = at.replace(hour=hour, minute=0, second=0, microsecond=0)
    return at
