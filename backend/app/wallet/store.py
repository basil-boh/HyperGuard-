"""The simulated bank.

A multi-account, in-memory bank. Each `Account` is one customer's banking app
(the mobile client drives the "app user"); the `Bank` aggregates every account plus
a global log of intervention `CaseRecord`s. The website control centre reads across
all of this; the mobile app reads/writes only its own account.

Some seeded recipients carry a hidden scam `archetype`, transferring to them drives
the matching social-engineering script through the swarm, so a keyless demo shows a
real interception. A handful of historical blocked cases are seeded directly so the
control centre is populated the moment it loads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.schemas import (
    CustomerProfile,
    Decision,
    InterventionOutcome,
    ScamArchetype,
    TransactionRequest,
    TransactionStatus,
    TrustedContact,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── Value objects ────────────────────────────────────────────────────────────
@dataclass
class Recipient:
    id: str
    name: str
    account: str
    bank: str
    saved: bool = True
    archetype: ScamArchetype | None = None


@dataclass
class LedgerEntry:
    id: str
    ts: datetime
    direction: str  # "out" | "in"
    counterparty: str
    amount: float
    status: str  # approved | blocked | completed
    decision: str | None = None
    risk_score: float | None = None
    scam_type: str | None = None
    memo: str | None = None
    case_id: str | None = None

    def json(self) -> dict:
        return {
            "id": self.id,
            "ts": _iso(self.ts),
            "direction": self.direction,
            "counterparty": self.counterparty,
            "amount": self.amount,
            "status": self.status,
            "decision": self.decision,
            "risk_score": self.risk_score,
            "scam_type": self.scam_type,
            "memo": self.memo,
            "case_id": self.case_id,
        }


@dataclass
class CaseRecord:
    case_id: str
    user_id: str
    user_name: str
    created_at: str
    transaction: dict
    decision: str
    status: str
    risk_score: float
    band: str
    risk_signals: list[dict]
    rationale: str
    scam_type: str | None
    classification: dict | None
    guardian_alerts: list[dict]
    transcript: list[dict]
    evidence: dict | None
    narrative: str

    def summary(self) -> dict:
        return {
            "case_id": self.case_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "created_at": self.created_at,
            "amount": self.transaction.get("amount"),
            "currency": self.transaction.get("currency", "SGD"),
            "payee_name": self.transaction.get("payee_name"),
            "decision": self.decision,
            "status": self.status,
            "risk_score": self.risk_score,
            "band": self.band,
            "scam_type": self.scam_type,
            "scam_title": (self.classification or {}).get("title"),
            "escalated": len(self.guardian_alerts) > 0,
        }

    def detail(self) -> dict:
        return {**self.summary(), **{
            "transaction": self.transaction,
            "risk_signals": self.risk_signals,
            "rationale": self.rationale,
            "classification": self.classification,
            "guardian_alerts": self.guardian_alerts,
            "transcript": self.transcript,
            "evidence": self.evidence,
            "narrative": self.narrative,
        }}


# ── Account ──────────────────────────────────────────────────────────────────
class Account:
    def __init__(
        self,
        owner: CustomerProfile,
        *,
        account_number: str,
        balance: float,
        currency: str = "SGD",
        recipients: list[Recipient] | None = None,
    ) -> None:
        self.owner = owner
        self.account_number = account_number
        self.currency = currency
        self.balance = balance
        self.recipients: list[Recipient] = recipients or []
        self.ledger: list[LedgerEntry] = []

    # reads ---------------------------------------------------------------------
    def summary(self) -> dict:
        return {
            "holder": self.owner.name,
            "account_number": self.account_number,
            "currency": self.currency,
            "balance": round(self.balance, 2),
            "recipients": len(self.recipients),
            "next_of_kin": len(self.owner.trusted_contacts),
        }

    def metrics(self) -> dict:
        out = [e for e in self.ledger if e.direction == "out"]
        blocked = [e for e in out if e.status == "blocked"]
        return {
            "transactions": len(out),
            "succeeded": len([e for e in out if e.status == "approved"]),
            "blocked": len(blocked),
            "protected": round(sum(e.amount for e in blocked), 2),
        }

    def last_activity(self) -> str | None:
        if not self.ledger:
            return None
        return _iso(max(e.ts for e in self.ledger))

    def list_transactions(self) -> list[dict]:
        return [e.json() for e in sorted(self.ledger, key=lambda e: e.ts, reverse=True)]

    def list_recipients(self) -> list[dict]:
        return [
            {"id": r.id, "name": r.name, "account": r.account, "bank": r.bank, "saved": r.saved}
            for r in self.recipients
        ]

    def list_contacts(self) -> list[dict]:
        return [c.model_dump() for c in self.owner.trusted_contacts]

    # writes --------------------------------------------------------------------
    def add_recipient(self, name: str, account: str, bank: str) -> dict:
        rcp = Recipient(id=f"rcp_{uuid4().hex[:8]}", name=name, account=account, bank=bank)
        self.recipients.append(rcp)
        return {"id": rcp.id, "name": rcp.name, "account": rcp.account, "bank": rcp.bank, "saved": True}

    def add_contact(self, name: str, phone: str, relationship: str) -> dict:
        contact = TrustedContact(
            id=f"koc_{uuid4().hex[:8]}",
            name=name,
            phone=phone,
            relationship=relationship,
            priority=len(self.owner.trusted_contacts) + 1,
        )
        self.owner.trusted_contacts.append(contact)
        return contact.model_dump()

    def remove_contact(self, contact_id: str) -> bool:
        before = len(self.owner.trusted_contacts)
        self.owner.trusted_contacts = [c for c in self.owner.trusted_contacts if c.id != contact_id]
        return len(self.owner.trusted_contacts) < before

    def find_recipient(self, recipient_id: str) -> Recipient | None:
        return next((r for r in self.recipients if r.id == recipient_id), None)

    def build_transaction(
        self, *, payee_name: str, payee_account: str, amount: float, memo: str | None, archetype: ScamArchetype | None
    ) -> TransactionRequest:
        recent = sum(1 for e in self.ledger if e.direction == "out" and e.ts >= _now() - timedelta(hours=24))
        return TransactionRequest(
            id=f"txn_{uuid4().hex[:10]}",
            customer_id=self.owner.id,
            amount=amount,
            currency=self.currency,
            payee_name=payee_name,
            payee_account=payee_account,
            channel="wallet_app",
            memo=memo,
            requested_at=_now(),
            recent_transfer_count_24h=recent,
            seeded_archetype=archetype,
        )

    def apply_outcome(self, txn: TransactionRequest, outcome: InterventionOutcome, case_id: str) -> LedgerEntry:
        approved = outcome.decision == Decision.approve
        if approved:
            self.balance -= txn.amount
        entry = LedgerEntry(
            id=txn.id,
            ts=_now(),
            direction="out",
            counterparty=txn.payee_name,
            amount=txn.amount,
            status=TransactionStatus.approved.value if approved else TransactionStatus.blocked.value,
            decision=outcome.decision.value,
            risk_score=outcome.risk.score,
            scam_type=outcome.classification.archetype.value if outcome.classification else None,
            memo=txn.memo,
            case_id=case_id,
        )
        self.ledger.insert(0, entry)
        return entry


# ── Bank ─────────────────────────────────────────────────────────────────────
class Bank:
    APP_USER = "acc_alex"

    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.cases: dict[str, CaseRecord] = {}
        self.reset()

    def account(self, user_id: str) -> Account | None:
        return self.accounts.get(user_id)

    def app_account(self) -> Account:
        return self.accounts[self.APP_USER]

    def list_accounts(self) -> list[Account]:
        return list(self.accounts.values())

    # case recording ------------------------------------------------------------
    def record_case(self, account: Account, txn: TransactionRequest, outcome: InterventionOutcome, case_id: str) -> None:
        self.cases[case_id] = CaseRecord(
            case_id=case_id,
            user_id=account.owner.id,
            user_name=account.owner.name,
            created_at=_iso(_now()),
            transaction=txn.model_dump(mode="json"),
            decision=outcome.decision.value,
            status="approved" if outcome.decision == Decision.approve else "blocked",
            risk_score=outcome.risk.score,
            band=outcome.risk.band.value,
            risk_signals=[s.model_dump() for s in outcome.risk.signals],
            rationale=outcome.risk.rationale,
            scam_type=outcome.classification.archetype.value if outcome.classification else None,
            classification=outcome.classification.model_dump(mode="json") if outcome.classification else None,
            guardian_alerts=[a.model_dump(mode="json") for a in outcome.guardian_alerts],
            transcript=[t.model_dump(mode="json") for t in outcome.transcript],
            evidence=outcome.evidence.model_dump(mode="json") if outcome.evidence else None,
            narrative=outcome.narrative,
        )

    def cases_for(self, user_id: str) -> list[CaseRecord]:
        return sorted(
            [c for c in self.cases.values() if c.user_id == user_id],
            key=lambda c: c.created_at,
            reverse=True,
        )

    def all_cases(self) -> list[CaseRecord]:
        return sorted(self.cases.values(), key=lambda c: c.created_at, reverse=True)

    # control-centre aggregates -------------------------------------------------
    def overview(self) -> dict:
        accounts = self.list_accounts()
        out_entries = [e for acc in accounts for e in acc.ledger if e.direction == "out"]
        blocked = [e for e in out_entries if e.status == "blocked"]
        escalations = sum(len(c.guardian_alerts) for c in self.cases.values())
        return {
            "customers": len(accounts),
            "transactions": len(out_entries),
            "approved": len([e for e in out_entries if e.status == "approved"]),
            "blocked": len(blocked),
            "amount_protected": round(sum(e.amount for e in blocked), 2),
            "escalations": escalations,
            "recent_cases": [c.summary() for c in self.all_cases()[:8]],
        }

    def directory(self) -> list[dict]:
        rows = []
        for acc in self.accounts.values():
            m = acc.metrics()
            risk = "watch" if m["blocked"] else ("elevated" if acc.owner.vulnerability_flags else "clear")
            rows.append({
                "id": acc.owner.id,
                "name": acc.owner.name,
                "phone": acc.owner.phone,
                "age": acc.owner.age,
                "account_number": acc.account_number,
                "balance": round(acc.balance, 2),
                "currency": acc.currency,
                "vulnerability_flags": acc.owner.vulnerability_flags,
                "guardians": len(acc.owner.trusted_contacts),
                "transactions": m["transactions"],
                "blocked": m["blocked"],
                "protected": m["protected"],
                "last_activity": acc.last_activity(),
                "risk": risk,
                "is_app_user": acc.owner.id == self.APP_USER,
            })
        return rows

    def profile(self, user_id: str) -> dict | None:
        acc = self.accounts.get(user_id)
        if acc is None:
            return None
        cases = self.cases_for(user_id)
        escalations = [
            {**a, "case_id": c.case_id, "payee": c.transaction.get("payee_name"), "at": c.created_at}
            for c in cases
            for a in c.guardian_alerts
        ]
        return {
            "profile": acc.owner.model_dump(mode="json"),
            "account": acc.summary(),
            "metrics": acc.metrics(),
            "guardians": acc.list_contacts(),
            "transactions": acc.list_transactions(),
            "cases": [c.summary() for c in cases],
            "escalations": escalations,
        }

    # ── Seeding ───────────────────────────────────────────────────────────────
    def reset(self) -> None:
        self.accounts = {}
        self.cases = {}
        _seed_bank(self)


_bank: Bank | None = None


def get_bank() -> Bank:
    global _bank
    if _bank is None:
        _bank = Bank()
    return _bank


# Backwards-compatible accessor used by the mobile wallet API.
def get_wallet() -> Account:
    return get_bank().app_account()


# ── Seed data ────────────────────────────────────────────────────────────────
def _contact(cid: str, name: str, phone: str, rel: str, pr: int = 1) -> TrustedContact:
    return TrustedContact(id=cid, name=name, phone=phone, relationship=rel, priority=pr)


def _ago(days: float = 0, hours: float = 0) -> datetime:
    return _now() - timedelta(days=days, hours=hours)


def _seed_bank(bank: Bank) -> None:
    # 1) Alex Tan, the mobile app user.
    alex = Account(
        CustomerProfile(
            id="acc_alex", name="Alex Tan", phone="+6580001234", age=67,
            vulnerability_flags=["retiree", "lives_alone"],
            baseline_avg_amount=360.0, baseline_std_amount=220.0,
            typical_hour_start=8, typical_hour_end=21, typical_velocity_per_day=1.5,
            known_payees=["NTUC FairPrice", "SP Group", "Sarah Tan", "City Clinic"],
            trusted_contacts=[_contact("koc_marcus", "Marcus Tan", "+6580000010", "son", 1)],
        ),
        account_number="DBS •••• 4471", balance=24_500.0,
        recipients=[
            Recipient("rcp_ntuc", "NTUC FairPrice", "100-000111-2", "OCBC"),
            Recipient("rcp_sarah", "Sarah Tan", "210-887654-9", "DBS"),
            Recipient("rcp_sp", "SP Group", "330-110022-4", "UOB"),
            Recipient("rcp_quick", "Quick Holdings Pte Ltd", "884-220931-0", "Standard Chartered", archetype=ScamArchetype.government_impersonation),
            Recipient("rcp_crypto", "CryptoGain Capital", "771-559020-8", "Wise", archetype=ScamArchetype.investment),
        ],
    )
    alex.ledger = [
        LedgerEntry("sd_a1", _ago(days=2), "in", "Monthly Pension", 3200.0, "completed"),
        LedgerEntry("sd_a2", _ago(days=1, hours=3), "out", "NTUC FairPrice", 84.30, "approved", decision="approve", risk_score=0.06),
        LedgerEntry("sd_a3", _ago(days=1), "out", "SP Group", 132.0, "approved", decision="approve", risk_score=0.08),
        LedgerEntry("sd_a4", _ago(hours=20), "out", "Sarah Tan", 200.0, "approved", decision="approve", risk_score=0.05),
    ]
    bank.accounts[alex.owner.id] = alex

    # 2) May Tan, repeat target, two interventions on file.
    may = Account(
        CustomerProfile(
            id="acc_may", name="May Tan", phone="+6580000001", age=72,
            vulnerability_flags=["elderly", "prior_scam_target", "lives_alone"],
            baseline_avg_amount=320.0, baseline_std_amount=180.0,
            typical_hour_start=9, typical_hour_end=20,
            known_payees=["NTUC FairPrice", "SP Group", "City Clinic"],
            trusted_contacts=[_contact("koc_may1", "Marcus Tan", "+6580000010", "son", 1), _contact("koc_may2", "Grace Tan", "+6580000011", "daughter", 2)],
        ),
        account_number="OCBC •••• 8820", balance=18_240.0,
        recipients=[Recipient("rcp_clinic", "City Clinic", "440-220011-7", "DBS")],
    )
    may.ledger = [LedgerEntry("sd_m1", _ago(days=5), "in", "Pension", 2600.0, "completed"), LedgerEntry("sd_m2", _ago(days=3), "out", "City Clinic", 145.0, "approved", decision="approve", risk_score=0.09)]
    bank.accounts[may.owner.id] = may
    _seed_case(bank, may, amount=8000.0, payee="Quik Transfer Pte Ltd", acct="884-553201-9", archetype=ScamArchetype.government_impersonation, score=0.97, when=_ago(days=1, hours=4), memo="urgent, move to safe account, tell no one", transcript=[("agent", "Hello May, I've paused an SGD 8,000 transfer to check it's really you. What's it for?"), ("customer", "An officer said my account is in a money-laundering case."), ("customer", "He told me to move it to a government safe account or I'll be arrested.")], guardian="Marcus Tan", rel="son")
    _seed_case(bank, may, amount=4200.0, payee="GoldTrust Recovery", acct="551-220190-3", archetype=ScamArchetype.investment, score=0.74, when=_ago(days=12), memo="release fee for my profits", transcript=[("agent", "Can you tell me what this 4,200 payment is for?"), ("customer", "My trading platform needs a release fee before I can withdraw my profits.")], guardian="Grace Tan", rel="daughter")

    # 3) Daniel Lim, healthy customer, all clear.
    daniel = Account(
        CustomerProfile(
            id="acc_daniel", name="Daniel Lim", phone="+6580000002", age=34,
            baseline_avg_amount=1450.0, baseline_std_amount=900.0,
            typical_hour_start=7, typical_hour_end=23, typical_velocity_per_day=2.5,
            known_payees=["Income Tax", "GreenView MCST", "Jolene Lim"],
            trusted_contacts=[_contact("koc_dan", "Jolene Lim", "+6580000012", "spouse", 1)],
        ),
        account_number="DBS •••• 9012", balance=41_180.0,
        recipients=[Recipient("rcp_mcst", "GreenView MCST", "200-110044-1", "OCBC")],
    )
    daniel.ledger = [
        LedgerEntry("sd_d1", _ago(days=1), "in", "Salary", 6800.0, "completed"),
        LedgerEntry("sd_d2", _ago(days=2), "out", "GreenView MCST", 420.0, "approved", decision="approve", risk_score=0.12),
        LedgerEntry("sd_d3", _ago(days=4), "out", "Jolene Lim", 1500.0, "approved", decision="approve", risk_score=0.18),
    ]
    bank.accounts[daniel.owner.id] = daniel

    # 4) Mr Wong, high vulnerability, romance scam intercepted.
    wong = Account(
        CustomerProfile(
            id="acc_wong", name="Wong Ah Kow", phone="+6580000003", age=81,
            vulnerability_flags=["elderly", "lives_alone", "limited_digital_literacy"],
            baseline_avg_amount=180.0, baseline_std_amount=90.0,
            typical_hour_start=9, typical_hour_end=19,
            known_payees=["SP Group", "NTUC FairPrice"],
            trusted_contacts=[_contact("koc_wong", "Linda Wong", "+6580000013", "daughter", 1)],
        ),
        account_number="UOB •••• 2210", balance=6_310.0,
        recipients=[],
    )
    wong.ledger = [LedgerEntry("sd_w1", _ago(days=6), "in", "Pension", 1100.0, "completed")]
    bank.accounts[wong.owner.id] = wong
    _seed_case(bank, wong, amount=3000.0, payee="Daniel (overseas)", acct="990-771220-5", archetype=ScamArchetype.romance, score=0.88, when=_ago(hours=8), memo="for his flight, emergency", transcript=[("agent", "Can you tell me who this 3,000 transfer is going to?"), ("customer", "My partner, we met online. He's stranded overseas and needs money for a flight."), ("customer", "We haven't met in person yet but he'll pay me back.")], guardian="Linda Wong", rel="daughter")

    # 5) Priya Nair, tech-support scam intercepted.
    priya = Account(
        CustomerProfile(
            id="acc_priya", name="Priya Nair", phone="+6580000004", age=58,
            vulnerability_flags=["recent_device_change"],
            baseline_avg_amount=540.0, baseline_std_amount=300.0,
            typical_hour_start=8, typical_hour_end=22,
            known_payees=["StarHub", "NTUC FairPrice", "Anand Nair"],
            trusted_contacts=[_contact("koc_priya", "Anand Nair", "+6580000014", "spouse", 1)],
        ),
        account_number="OCBC •••• 5567", balance=12_640.0,
        recipients=[Recipient("rcp_star", "StarHub", "300-220110-8", "DBS")],
    )
    priya.ledger = [LedgerEntry("sd_p1", _ago(days=2), "out", "StarHub", 89.0, "approved", decision="approve", risk_score=0.07), LedgerEntry("sd_p2", _ago(days=7), "in", "Salary", 5200.0, "completed")]
    bank.accounts[priya.owner.id] = priya
    _seed_case(bank, priya, amount=1800.0, payee="SecureFix Support", acct="220-553010-2", archetype=ScamArchetype.tech_support, score=0.79, when=_ago(days=2, hours=6), memo="refund correction", transcript=[("agent", "What is this 1,800 payment for?"), ("customer", "A technician fixed my computer remotely and said a refund was sent by mistake."), ("customer", "He asked me to return the difference.")], guardian="Anand Nair", rel="spouse")


def _seed_case(
    bank: Bank, account: Account, *, amount: float, payee: str, acct: str,
    archetype: ScamArchetype, score: float, when: datetime, memo: str,
    transcript: list[tuple[str, str]], guardian: str, rel: str,
) -> None:
    """Construct a blocked historical case + its ledger entry."""
    from app.services.risk_engine import _band  # local import to avoid cycle
    from app.services.scam_taxonomy import ScamTaxonomy

    case_id = f"HG-{uuid4().hex[:10].upper()}"
    tax = ScamTaxonomy().get(archetype)
    indicators = list(tax.indicators[:4]) if tax else []
    title = tax.title if tax else "Suspicious transfer"
    guidance = tax.guidance if tax else ""

    turns = [
        {"index": i, "speaker": sp, "text": tx, "ts": _iso(when + timedelta(seconds=8 * i)), "tags": (["guidance"] if sp == "agent" and i > 0 else [])}
        for i, (sp, tx) in enumerate(transcript)
    ]
    contact = next((c for c in account.owner.trusted_contacts if c.name == guardian), None)
    alert = {
        "contact": (contact.model_dump() if contact else {"id": "x", "name": guardian, "phone": "+65", "relationship": rel, "priority": 1}),
        "channel": "sms", "status": "acknowledged", "acknowledged": True,
        "message": f"HyperGuard alert: {account.owner.name} attempted SGD {amount:,.0f} to {payee}. Risk {score:.0%}, pattern {title}. Please confirm.",
    }
    bank.cases[case_id] = CaseRecord(
        case_id=case_id, user_id=account.owner.id, user_name=account.owner.name, created_at=_iso(when),
        transaction={"id": f"txn_{uuid4().hex[:10]}", "amount": amount, "currency": "SGD", "payee_name": payee, "payee_account": acct, "channel": "wallet_app", "memo": memo, "requested_at": _iso(when), "status": "blocked"},
        decision="block", status="blocked", risk_score=score, band=_band(score).value,
        risk_signals=[{"code": "new_payee", "label": "First-ever transfer to this payee", "contribution": round(score * 0.4, 3), "severity": "alarm", "detail": f"'{payee}' has never received funds."}, {"code": "pressure_language", "label": "Coercion language in transfer note", "contribution": round(score * 0.3, 3), "severity": "alarm", "detail": f"Note: “{memo}”."}],
        rationale=f"Risk {score:.0%}, pattern consistent with {title.lower()}.",
        scam_type=archetype.value, classification={"archetype": archetype.value, "title": title, "confidence": round(min(score + 0.02, 0.98), 2), "indicators": indicators, "guidance": guidance},
        guardian_alerts=[alert], transcript=turns, evidence=None,
        narrative=f"Blocked. The SGD {amount:,.0f} transfer to {payee} was halted after the call surfaced {title}; {guardian} was alerted. The money never left the account.",
    )
    account.ledger.insert(0, LedgerEntry(id=bank.cases[case_id].transaction["id"], ts=when, direction="out", counterparty=payee, amount=amount, status="blocked", decision="block", risk_score=score, scam_type=archetype.value, memo=memo, case_id=case_id))
