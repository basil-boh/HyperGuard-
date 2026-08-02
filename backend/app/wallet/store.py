"""The simulated bank.

A multi-account, in-memory bank. Each `Account` is one customer's banking app
(the mobile client drives the "app user"); the `Bank` aggregates every account plus
a global log of intervention `CaseRecord`s. The website control centre reads across
all of this; the mobile app reads/writes only its own account.

Some seeded recipients carry a hidden scam `archetype`, transferring to them drives
the matching social-engineering script through the swarm, so a keyless demo shows a
real interception. A handful of historical blocked cases are seeded directly so the
control centre is populated the moment it loads.

The customer book itself — who exists, their PIN, their transaction history — lives
in `seed_profiles` as plain data; this module materialises it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
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
from app.services.phone import parse_country
from app.wallet.network import (
    ACTIVE,
    AuthorityFiling,
    GuardianLink,
    IncidentReport,
)
from app.wallet.seed_profiles import (
    PERSONAS_BY_ID,
    SEED_LINKS,
    SEED_PERSONAS,
    SeedCase,
    SeedPersona,
    build_ledger,
    case_id_for,
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
    phone: str | None = None
    country: str | None = None
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
    counterparty_phone: str | None = None

    def json(self) -> dict:
        return {
            "id": self.id,
            "ts": _iso(self.ts),
            "direction": self.direction,
            "counterparty": self.counterparty,
            "counterparty_phone": self.counterparty_phone,
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


def build_case_record(
    account: "Account", txn: TransactionRequest, outcome: InterventionOutcome, case_id: str
) -> CaseRecord:
    """Fold a finished intervention into the durable case shape the control centre
    reads. Shared by the in-memory Bank and the Supabase repository."""
    return CaseRecord(
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
        pin_hash: str | None = None,
    ) -> None:
        self.owner = owner
        self.account_number = account_number
        self.currency = currency
        self.balance = balance
        self.recipients: list[Recipient] = recipients or []
        self.ledger: list[LedgerEntry] = []
        # Sign-in credential (PBKDF2, see services/auth). Deliberately *not* on
        # CustomerProfile: that model is serialised to the console, this must never be.
        self.pin_hash: str | None = pin_hash

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
        # NOTE: archetype is intentionally never serialised out — the hidden scam
        # tag must not leak to the client.
        return [
            {
                "id": r.id,
                "name": r.name,
                "account": r.account,
                "bank": r.bank,
                "phone": r.phone,
                "country": r.country,
                "saved": r.saved,
            }
            for r in self.recipients
        ]

    def list_contacts(self) -> list[dict]:
        return [c.model_dump() for c in self.owner.trusted_contacts]

    # writes --------------------------------------------------------------------
    def add_recipient(
        self,
        name: str,
        account: str,
        bank: str,
        phone: str | None = None,
        country: str | None = None,
    ) -> dict:
        rcp = Recipient(
            id=f"rcp_{uuid4().hex[:8]}",
            name=name,
            account=account,
            bank=bank,
            phone=phone,
            country=country or parse_country(phone),
        )
        self.recipients.append(rcp)
        return {
            "id": rcp.id,
            "name": rcp.name,
            "account": rcp.account,
            "bank": rcp.bank,
            "phone": rcp.phone,
            "country": rcp.country,
            "saved": True,
        }

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
        self,
        *,
        payee_name: str,
        payee_account: str,
        amount: float,
        memo: str | None,
        archetype: ScamArchetype | None,
        payee_phone: str | None = None,
    ) -> TransactionRequest:
        recent = sum(1 for e in self.ledger if e.direction == "out" and e.ts >= _now() - timedelta(hours=24))
        return TransactionRequest(
            id=f"txn_{uuid4().hex[:10]}",
            customer_id=self.owner.id,
            amount=amount,
            currency=self.currency,
            payee_name=payee_name,
            payee_account=payee_account,
            payee_phone=payee_phone,
            payee_country=parse_country(payee_phone),
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
            counterparty_phone=txn.payee_phone,
        )
        self.ledger.insert(0, entry)
        return entry


# ── Bank ─────────────────────────────────────────────────────────────────────
class Bank:
    APP_USER = "acc_alex"

    def __init__(self, seed: bool = True) -> None:
        self.accounts: dict[str, Account] = {}
        self.cases: dict[str, CaseRecord] = {}
        # The guardian network: who watches over whom, what they were told, and any
        # simulated authority filing raised from a case.
        self.links: dict[str, GuardianLink] = {}
        self.incidents: dict[str, IncidentReport] = {}
        self.filings: dict[str, AuthorityFiling] = {}  # keyed by case_id
        if seed:
            self.reset()

    @classmethod
    def empty(cls) -> "Bank":
        """An unseeded bank — used when state is hydrated from persistence."""
        return cls(seed=False)

    def account(self, user_id: str) -> Account | None:
        return self.accounts.get(user_id)

    def account_by_phone(self, phone: str) -> Account | None:
        """Look an account up by its sign-in identifier (normalised E.164)."""
        from app.services.auth import normalize_phone

        wanted = normalize_phone(phone)
        if not wanted:
            return None
        return next(
            (a for a in self.accounts.values() if normalize_phone(a.owner.phone) == wanted),
            None,
        )

    def app_account(self) -> Account:
        return self.accounts[self.APP_USER]

    def list_accounts(self) -> list[Account]:
        return list(self.accounts.values())

    # case recording ------------------------------------------------------------
    def record_case(self, account: Account, txn: TransactionRequest, outcome: InterventionOutcome, case_id: str) -> None:
        self.cases[case_id] = build_case_record(account, txn, outcome, case_id)

    def cases_for(self, user_id: str) -> list[CaseRecord]:
        return sorted(
            [c for c in self.cases.values() if c.user_id == user_id],
            key=lambda c: c.created_at,
            reverse=True,
        )

    def all_cases(self) -> list[CaseRecord]:
        return sorted(self.cases.values(), key=lambda c: c.created_at, reverse=True)

    # guardian network ------------------------------------------------------------
    def link(self, link_id: str) -> GuardianLink | None:
        return self.links.get(link_id)

    def find_link(self, guardian_user_id: str, protected_user_id: str) -> GuardianLink | None:
        """Any existing link between the pair, whatever its status.

        Callers use this to avoid duplicate invitations and to revive a link that was
        previously declined or revoked, rather than stacking rows for the same pair.
        """
        return next(
            (
                link
                for link in self.links.values()
                if link.guardian_user_id == guardian_user_id
                and link.protected_user_id == protected_user_id
            ),
            None,
        )

    def links_as_guardian(self, user_id: str, *, status: str | None = None) -> list[GuardianLink]:
        """People `user_id` looks after."""
        return self._links(lambda link: link.guardian_user_id == user_id, status)

    def links_as_protected(self, user_id: str, *, status: str | None = None) -> list[GuardianLink]:
        """People who look after `user_id`."""
        return self._links(lambda link: link.protected_user_id == user_id, status)

    def guardians_of(self, user_id: str) -> list[GuardianLink]:
        return self.links_as_protected(user_id, status=ACTIVE)

    def _links(self, predicate, status: str | None) -> list[GuardianLink]:
        return sorted(
            [
                link
                for link in self.links.values()
                if predicate(link) and (status is None or link.status == status)
            ],
            key=lambda link: link.created_at,
            reverse=True,
        )

    def incidents_for_guardian(self, user_id: str) -> list[IncidentReport]:
        return sorted(
            [r for r in self.incidents.values() if r.guardian_user_id == user_id],
            key=lambda r: r.sent_at,
            reverse=True,
        )

    def incidents_for_case(self, case_id: str) -> list[IncidentReport]:
        return [r for r in self.incidents.values() if r.case_id == case_id]

    def filing(self, case_id: str) -> AuthorityFiling | None:
        return self.filings.get(case_id)

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
        self.links = {}
        self.incidents = {}
        self.filings = {}
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


# ── Seeding from the customer book ───────────────────────────────────────────
def _ago(days: float = 0, hours: float = 0) -> datetime:
    return _now() - timedelta(days=days, hours=hours)


@lru_cache(maxsize=None)
def _seed_pin_hash(pin: str) -> str:
    """PBKDF2 is intentionally slow; the seed book is small and fixed, so hash each
    distinct PIN once per process rather than on every `Bank()` construction."""
    from app.services.auth import hash_pin

    return hash_pin(pin)


def _seed_bank(bank: Bank) -> None:
    """Materialise every persona in `seed_profiles` into accounts, ledgers and cases."""
    for persona in SEED_PERSONAS:
        owner = CustomerProfile(
            id=persona.id,
            name=persona.name,
            phone=persona.phone,
            age=persona.age,
            vulnerability_flags=list(persona.vulnerability_flags),
            baseline_avg_amount=persona.baseline_avg_amount,
            baseline_std_amount=persona.baseline_std_amount,
            typical_hour_start=persona.typical_hour_start,
            typical_hour_end=persona.typical_hour_end,
            typical_velocity_per_day=persona.typical_velocity_per_day,
            known_payees=list(persona.known_payees),
            known_payee_phones=list(persona.known_payee_phones),
            trusted_contacts=[
                TrustedContact(
                    id=c.id, name=c.name, phone=c.phone,
                    relationship=c.relationship, priority=c.priority,
                )
                for c in persona.contacts
            ],
        )
        account = Account(
            owner,
            account_number=persona.account_number,
            balance=persona.balance,
            recipients=[
                Recipient(
                    id=r.id, name=r.name, account=r.account, bank=r.bank,
                    phone=r.phone, country=r.country, archetype=r.archetype,
                )
                for r in persona.recipients
            ],
            pin_hash=_seed_pin_hash(persona.pin),
        )
        account.ledger = [
            LedgerEntry(
                id=spec.id,
                ts=_ago(days=spec.days_ago),
                direction=spec.direction,
                counterparty=spec.counterparty,
                amount=spec.amount,
                status=spec.status,
                decision=spec.decision,
                risk_score=spec.risk_score,
                memo=spec.memo,
            )
            for spec in build_ledger(persona)
        ]
        bank.accounts[persona.id] = account

        for case in persona.cases:
            _seed_case(bank, account, persona, case)

    _seed_network(bank)


def _seed_network(bank: Bank) -> None:
    """Wire the pre-existing guardian relationships, their delivered incident
    reports, and any simulated filing already raised."""
    from app.services.filing import file_case

    for spec in SEED_LINKS:
        created = _ago(days=spec.days_ago)
        link_id = f"lnk_seed_{spec.slug}"
        bank.links[link_id] = GuardianLink(
            id=link_id,
            guardian_user_id=spec.guardian_id,
            protected_user_id=spec.protected_id,
            relationship=spec.relationship,
            status=spec.status,
            invited_by=spec.invited_by,
            created_at=created,
            responded_at=created if spec.status == ACTIVE else None,
        )

        protected = bank.account(spec.protected_id)
        persona = PERSONAS_BY_ID.get(spec.protected_id)
        if protected is None or persona is None:
            continue

        for case_spec in persona.cases:
            if case_spec.slug not in spec.deliver_cases:
                continue
            case = bank.cases.get(case_id_for(persona, case_spec))
            if case is None:
                continue

            sent_at = _ago(days=case_spec.days_ago, hours=case_spec.hours_ago - 0.25)
            report_id = f"inc_seed_{spec.slug}_{case_spec.slug}"
            bank.incidents[report_id] = IncidentReport(
                id=report_id,
                case_id=case.case_id,
                protected_user_id=protected.owner.id,
                protected_name=protected.owner.name,
                guardian_user_id=spec.guardian_id,
                sent_at=sent_at,
                sent_by_user_id=None,  # delivered automatically by the swarm
                read_at=sent_at + timedelta(hours=1) if case_spec.slug in spec.read_cases else None,
                amount=float(case.transaction.get("amount") or 0),
                currency=case.transaction.get("currency", "SGD"),
                payee_name=case.transaction.get("payee_name") or "",
                scam_title=(case.classification or {}).get("title"),
                decision=case.decision,
                risk_score=case.risk_score,
            )

            if case_spec.slug in spec.filed_cases and case.case_id not in bank.filings:
                filing = file_case(
                    case,
                    filed_by_user_id=spec.guardian_id,
                    reference=f"SIM-NASC-SEED-{case_spec.slug.upper()}",
                )
                filing.filed_at = sent_at + timedelta(hours=2)
                bank.filings[case.case_id] = filing


def _seed_case(bank: Bank, account: Account, persona: SeedPersona, spec: SeedCase) -> None:
    """Construct a blocked historical case plus the ledger entry that mirrors it."""
    from app.services.risk_engine import _band  # local import to avoid cycle
    from app.services.scam_taxonomy import ScamTaxonomy

    case_id = case_id_for(persona, spec)
    when = _ago(days=spec.days_ago, hours=spec.hours_ago)
    taxonomy = ScamTaxonomy().get(spec.archetype)
    title = taxonomy.title if taxonomy else "Suspicious transfer"

    turns = [
        {
            "index": i,
            "speaker": speaker,
            "text": text,
            "ts": _iso(when + timedelta(seconds=8 * i)),
            "tags": (["guidance"] if speaker == "agent" and i > 0 else []),
        }
        for i, (speaker, text) in enumerate(spec.transcript)
    ]
    contact = next(
        (c for c in account.owner.trusted_contacts if c.name == spec.guardian), None
    )
    alert = {
        "contact": (
            contact.model_dump()
            if contact
            else {
                "id": "x", "name": spec.guardian, "phone": "+65",
                "relationship": spec.relationship, "priority": 1,
            }
        ),
        "channel": "sms",
        "status": "acknowledged",
        "acknowledged": True,
        "message": (
            f"HyperGuard alert: {account.owner.name} attempted SGD {spec.amount:,.0f} to "
            f"{spec.payee}. Risk {spec.score:.0%}, pattern {title}. Please confirm."
        ),
    }
    txn_id = f"txn_seed_{persona.id.removeprefix('acc_')}_{spec.slug}"

    bank.cases[case_id] = CaseRecord(
        case_id=case_id,
        user_id=account.owner.id,
        user_name=account.owner.name,
        created_at=_iso(when),
        transaction={
            "id": txn_id, "amount": spec.amount, "currency": "SGD",
            "payee_name": spec.payee, "payee_account": spec.account,
            "channel": "wallet_app", "memo": spec.memo,
            "requested_at": _iso(when), "status": "blocked",
        },
        decision="block",
        status="blocked",
        risk_score=spec.score,
        band=_band(spec.score).value,
        risk_signals=[
            {
                "code": "new_payee",
                "label": "First-ever transfer to this payee",
                "contribution": round(spec.score * 0.4, 3),
                "severity": "alarm",
                "detail": f"'{spec.payee}' has never received funds.",
            },
            {
                "code": "pressure_language",
                "label": "Coercion language in transfer note",
                "contribution": round(spec.score * 0.3, 3),
                "severity": "alarm",
                "detail": f"Note: “{spec.memo}”.",
            },
        ],
        rationale=f"Risk {spec.score:.0%}, pattern consistent with {title.lower()}.",
        scam_type=spec.archetype.value,
        classification={
            "archetype": spec.archetype.value,
            "title": title,
            "confidence": round(min(spec.score + 0.02, 0.98), 2),
            "indicators": list(taxonomy.indicators[:4]) if taxonomy else [],
            "guidance": taxonomy.guidance if taxonomy else "",
        },
        guardian_alerts=[alert],
        transcript=turns,
        evidence=None,
        narrative=(
            f"Blocked. The SGD {spec.amount:,.0f} transfer to {spec.payee} was halted after "
            f"the call surfaced {title}; {spec.guardian} was alerted. The money never left "
            "the account."
        ),
    )
    account.ledger.insert(
        0,
        LedgerEntry(
            id=txn_id, ts=when, direction="out", counterparty=spec.payee,
            amount=spec.amount, status="blocked", decision="block",
            risk_score=spec.score, scam_type=spec.archetype.value,
            memo=spec.memo, case_id=case_id,
        ),
    )
