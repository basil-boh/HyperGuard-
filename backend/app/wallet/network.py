"""The guardian network.

Two people, two roles. `trusted_contacts` (see `schemas.TrustedContact`) is a phone
number the swarm can *reach* during an intervention. A `GuardianLink` is stronger:
it joins two real HyperGuard accounts, so the guardian can sign in and see what
happened to the person they look after.

The consent rule is one-directional and absolute: **the protected person decides.**

- A guardian inviting a relative creates a `pending` link the relative must accept.
- A customer adding a guardian who already has an account creates an `active` link
  immediately — they initiated it, so consent is implicit from the side that matters.

Nothing here reads a case's contents; delivery of an incident report is a separate
record (`IncidentReport`) so "who was told what, and when" is auditable on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

# Link lifecycle. `revoked` is terminal and kept (rather than deleted) so an
# investigator can still see that access once existed.
PENDING = "pending"
ACTIVE = "active"
DECLINED = "declined"
REVOKED = "revoked"

# Who opened the link — drives the wording the other side sees.
BY_GUARDIAN = "guardian"
BY_PROTECTED = "protected"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _parse(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


@dataclass
class GuardianLink:
    """One guardian watching over one protected customer."""

    id: str
    guardian_user_id: str
    protected_user_id: str
    relationship: str  # the guardian's relationship *to* the protected person
    status: str = PENDING
    invited_by: str = BY_GUARDIAN
    created_at: datetime = field(default_factory=_now)
    responded_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == ACTIVE

    def json(self, *, guardian_name: str = "", protected_name: str = "") -> dict:
        return {
            "id": self.id,
            "guardian_user_id": self.guardian_user_id,
            "guardian_name": guardian_name,
            "protected_user_id": self.protected_user_id,
            "protected_name": protected_name,
            "relationship": self.relationship,
            "status": self.status,
            "invited_by": self.invited_by,
            "created_at": _iso(self.created_at),
            "responded_at": _iso(self.responded_at),
        }


@dataclass
class IncidentReport:
    """A case report delivered to one guardian.

    The body is always read live from the case, so a report can never drift from
    what actually happened. Only the delivery record and a headline snapshot (for
    rendering the inbox without loading every case) live here.
    """

    id: str
    case_id: str
    protected_user_id: str
    protected_name: str
    guardian_user_id: str
    sent_at: datetime = field(default_factory=_now)
    sent_by_user_id: str | None = None
    read_at: datetime | None = None
    note: str | None = None
    # Headline snapshot
    amount: float = 0.0
    currency: str = "SGD"
    payee_name: str = ""
    scam_title: str | None = None
    decision: str = "block"
    risk_score: float = 0.0

    @property
    def unread(self) -> bool:
        return self.read_at is None

    def json(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "protected_user_id": self.protected_user_id,
            "protected_name": self.protected_name,
            "guardian_user_id": self.guardian_user_id,
            "sent_at": _iso(self.sent_at),
            "sent_by_user_id": self.sent_by_user_id,
            "read_at": _iso(self.read_at),
            "unread": self.unread,
            "note": self.note,
            "amount": self.amount,
            "currency": self.currency,
            "payee_name": self.payee_name,
            "scam_title": self.scam_title,
            "decision": self.decision,
            "risk_score": self.risk_score,
        }


@dataclass
class AuthorityFiling:
    """A SIMULATED report to the anti-scam authorities.

    HyperGuard is a prototype and has no connection to the police, the National
    Anti-Scam Centre, or any other body. Nothing is transmitted anywhere. The
    `simulated` flag and the `SIM-` reference prefix exist so this can never be
    mistaken for a real filing — in the API, in the UI, or in a screenshot of either.
    """

    case_id: str
    reference: str
    authority: str
    filed_by_user_id: str
    filed_at: datetime = field(default_factory=_now)
    status: str = "received"
    timeline: list[dict] = field(default_factory=list)
    simulated: bool = True

    def json(self) -> dict:
        return {
            "case_id": self.case_id,
            "reference": self.reference,
            "authority": self.authority,
            "filed_by_user_id": self.filed_by_user_id,
            "filed_at": _iso(self.filed_at),
            "status": self.status,
            "timeline": self.timeline,
            "simulated": self.simulated,
            "disclaimer": SIMULATION_DISCLAIMER,
        }


SIMULATION_DISCLAIMER = (
    "Simulated filing. HyperGuard is a prototype and is not connected to the police, "
    "the National Anti-Scam Centre, or any other authority. No report has been sent "
    "to anyone. To report a real scam in Singapore, call the ScamShield helpline on "
    "1799 or file at police.gov.sg."
)


# ── Id helpers ─────────────────────────────────────────────────────────────────
def new_link_id() -> str:
    return f"lnk_{uuid4().hex[:10]}"


def new_report_id() -> str:
    return f"inc_{uuid4().hex[:10]}"


# ── Row (de)serialisation, shared by the Supabase repository ───────────────────
def link_to_row(link: GuardianLink) -> dict:
    return {
        "id": link.id,
        "guardian_user_id": link.guardian_user_id,
        "protected_user_id": link.protected_user_id,
        "relationship": link.relationship,
        "status": link.status,
        "invited_by": link.invited_by,
        "created_at": _iso(link.created_at),
        "responded_at": _iso(link.responded_at),
    }


def row_to_link(row: dict) -> GuardianLink:
    return GuardianLink(
        id=row["id"],
        guardian_user_id=row["guardian_user_id"],
        protected_user_id=row["protected_user_id"],
        relationship=row.get("relationship") or "family",
        status=row.get("status") or PENDING,
        invited_by=row.get("invited_by") or BY_GUARDIAN,
        created_at=_parse(row.get("created_at")) or _now(),
        responded_at=_parse(row.get("responded_at")),
    )


def report_to_row(report: IncidentReport) -> dict:
    return {
        "id": report.id,
        "case_id": report.case_id,
        "protected_user_id": report.protected_user_id,
        "protected_name": report.protected_name,
        "guardian_user_id": report.guardian_user_id,
        "sent_at": _iso(report.sent_at),
        "sent_by_user_id": report.sent_by_user_id,
        "read_at": _iso(report.read_at),
        "note": report.note,
        "amount": report.amount,
        "currency": report.currency,
        "payee_name": report.payee_name,
        "scam_title": report.scam_title,
        "decision": report.decision,
        "risk_score": report.risk_score,
    }


def row_to_report(row: dict) -> IncidentReport:
    return IncidentReport(
        id=row["id"],
        case_id=row["case_id"],
        protected_user_id=row["protected_user_id"],
        protected_name=row.get("protected_name") or "",
        guardian_user_id=row["guardian_user_id"],
        sent_at=_parse(row.get("sent_at")) or _now(),
        sent_by_user_id=row.get("sent_by_user_id"),
        read_at=_parse(row.get("read_at")),
        note=row.get("note"),
        amount=float(row.get("amount") or 0),
        currency=row.get("currency") or "SGD",
        payee_name=row.get("payee_name") or "",
        scam_title=row.get("scam_title"),
        decision=row.get("decision") or "block",
        risk_score=float(row.get("risk_score") or 0),
    )


def filing_to_row(filing: AuthorityFiling) -> dict:
    return {
        "case_id": filing.case_id,
        "reference": filing.reference,
        "authority": filing.authority,
        "filed_by_user_id": filing.filed_by_user_id,
        "filed_at": _iso(filing.filed_at),
        "status": filing.status,
        "timeline": filing.timeline,
        "simulated": filing.simulated,
    }


def row_to_filing(row: dict) -> AuthorityFiling:
    return AuthorityFiling(
        case_id=row["case_id"],
        reference=row["reference"],
        authority=row.get("authority") or "",
        filed_by_user_id=row.get("filed_by_user_id") or "",
        filed_at=_parse(row.get("filed_at")) or _now(),
        status=row.get("status") or "received",
        timeline=row.get("timeline") or [],
        simulated=bool(row.get("simulated", True)),
    )
