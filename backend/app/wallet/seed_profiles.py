"""The demo bank's customer book, as data.

Seven customers, each with a *different financial signature*, because the risk
engine scores against learned behaviour rather than fixed thresholds — so the only
way to exercise it honestly is with accounts that genuinely differ:

| account       | signature                                    | tests                          |
|---------------|----------------------------------------------|--------------------------------|
| `acc_alex`    | retiree, small regular outgoings             | the default mobile demo user   |
| `acc_may`     | retiree, two scams already on file           | repeat-target escalation       |
| `acc_daniel`  | salaried professional, high volume           | large transfers that are fine  |
| `acc_wong`    | 81, thin file, tiny amounts                  | any 4-figure transfer is alarming |
| `acc_priya`   | mid-career, steady bills + school fees       | tech-support follow-up         |
| `acc_siti`    | gig worker, many small payouts               | high velocity, low amounts     |
| `acc_robert`  | SME owner, five-figure supplier runs         | big ≠ suspicious               |

Everything here is plain data — no imports from `store`, so `store` can import this
module and materialise it without a cycle. Ledgers are generated deterministically
(seeded RNG, stable ids) so a re-seed is idempotent and tests never flake.

Each persona carries a 6-digit `pin`: the sign-in credential for the mobile app,
hashed on the way into the database and surfaced to the login screen's demo picker
via `GET /api/auth/demo-accounts`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.schemas import ScamArchetype


# ── Building blocks ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SeedRecipient:
    id: str
    name: str
    account: str
    bank: str
    phone: str | None = None
    country: str | None = None
    # A hidden archetype turns this payee into a live scam scenario: transferring to
    # it drives the matching social-engineering script through the swarm.
    archetype: ScamArchetype | None = None


@dataclass(frozen=True)
class SeedContact:
    id: str
    name: str
    phone: str
    relationship: str
    priority: int = 1


@dataclass(frozen=True)
class Recurring:
    """A repeating line item — salary in, utilities out, an allowance to family."""

    counterparty: str
    amount: float
    direction: str = "out"
    every_days: float = 30.0
    count: int = 4
    first_days_ago: float = 1.0
    memo: str | None = None
    jitter: float = 0.0  # ± fraction of `amount`, applied deterministically
    risk: float = 0.06


@dataclass(frozen=True)
class OneOff:
    counterparty: str
    amount: float
    days_ago: float
    direction: str = "out"
    memo: str | None = None
    risk: float = 0.07


@dataclass(frozen=True)
class SeedCase:
    """An intervention already on file — a blocked transfer plus its case record."""

    slug: str  # → deterministic case id, so re-seeding never duplicates
    amount: float
    payee: str
    account: str
    archetype: ScamArchetype
    score: float
    days_ago: float
    memo: str
    transcript: tuple[tuple[str, str], ...]
    guardian: str
    relationship: str
    hours_ago: float = 0.0


@dataclass(frozen=True)
class SeedPersona:
    id: str
    name: str
    phone: str
    pin: str
    blurb: str  # one line, shown on the sign-in screen's demo picker
    account_number: str
    balance: float
    age: int | None = None
    vulnerability_flags: tuple[str, ...] = ()
    baseline_avg_amount: float = 300.0
    baseline_std_amount: float = 200.0
    typical_hour_start: int = 8
    typical_hour_end: int = 22
    typical_velocity_per_day: float = 1.5
    known_payees: tuple[str, ...] = ()
    known_payee_phones: tuple[str, ...] = ()
    contacts: tuple[SeedContact, ...] = ()
    recipients: tuple[SeedRecipient, ...] = ()
    recurring: tuple[Recurring, ...] = ()
    one_offs: tuple[OneOff, ...] = ()
    cases: tuple[SeedCase, ...] = ()


@dataclass(frozen=True)
class SeedLink:
    """A guardian relationship already in place when the demo starts.

    `deliver_cases` names the protected person's `SeedCase.slug`s whose reports have
    already been delivered to this guardian — that's what fills the guardian's inbox
    on first load. `read_cases` and `filed_cases` are subsets, so the demo opens with
    a mix of unread/read and filed/unfiled reports rather than a uniform wall.
    """

    slug: str
    guardian_id: str
    protected_id: str
    relationship: str  # the guardian's relationship *to* the protected person
    status: str = "active"
    invited_by: str = "guardian"
    days_ago: float = 30.0
    deliver_cases: tuple[str, ...] = ()
    read_cases: tuple[str, ...] = ()
    filed_cases: tuple[str, ...] = ()


@dataclass(frozen=True)
class LedgerSpec:
    """One materialised ledger row — `store` turns these into `LedgerEntry`s."""

    id: str
    days_ago: float
    direction: str
    counterparty: str
    amount: float
    status: str
    decision: str | None
    risk_score: float | None
    memo: str | None


# ── Ledger generation ──────────────────────────────────────────────────────────
def build_ledger(persona: SeedPersona) -> list[LedgerSpec]:
    """Expand a persona's recurring + one-off items into a dated ledger.

    Ids are stable (`sd_<account suffix>_<nnn>`) so upserting a re-seed updates rows
    in place instead of duplicating them. Amount and time-of-day jitter come from an
    RNG seeded on the persona and counterparty, so the history looks lived-in but is
    identical on every run.
    """
    rows: list[LedgerSpec] = []
    prefix = persona.id.removeprefix("acc_")

    for item in persona.recurring:
        rng = random.Random(f"{persona.id}|{item.counterparty}")
        for occurrence in range(item.count):
            amount = item.amount
            if item.jitter:
                amount *= rng.uniform(1 - item.jitter, 1 + item.jitter)
            rows.append(
                LedgerSpec(
                    id="",  # assigned after sorting
                    days_ago=item.first_days_ago
                    + occurrence * item.every_days
                    + rng.uniform(0, 0.35),
                    direction=item.direction,
                    counterparty=item.counterparty,
                    amount=round(amount, 2),
                    status="completed" if item.direction == "in" else "approved",
                    decision=None if item.direction == "in" else "approve",
                    risk_score=None if item.direction == "in" else item.risk,
                    memo=item.memo,
                )
            )

    for one_off in persona.one_offs:
        rows.append(
            LedgerSpec(
                id="",
                days_ago=one_off.days_ago,
                direction=one_off.direction,
                counterparty=one_off.counterparty,
                amount=round(one_off.amount, 2),
                status="completed" if one_off.direction == "in" else "approved",
                decision=None if one_off.direction == "in" else "approve",
                risk_score=None if one_off.direction == "in" else one_off.risk,
                memo=one_off.memo,
            )
        )

    # Newest first, then number them — a stable id per (persona, position).
    rows.sort(key=lambda r: r.days_ago)
    return [
        LedgerSpec(**{**row.__dict__, "id": f"sd_{prefix}_{index:03d}"})
        for index, row in enumerate(rows)
    ]


def case_id_for(persona: SeedPersona, case: SeedCase) -> str:
    """Deterministic case id — re-seeding updates the same row."""
    return f"HG-SEED-{persona.id.removeprefix('acc_').upper()}-{case.slug.upper()}"


# ── The customer book ──────────────────────────────────────────────────────────
SEED_PERSONAS: tuple[SeedPersona, ...] = (
    # 1) Alex Tan — the default mobile app user. Retiree, small regular outgoings,
    #    two planted scam payees so a keyless demo can show a real interception.
    SeedPersona(
        id="acc_alex",
        name="Alex Tan",
        phone="+6580001234",
        pin="112233",
        blurb="Retiree, 67 · the default demo account",
        account_number="DBS •••• 4471",
        balance=24_500.0,
        age=67,
        vulnerability_flags=("retiree", "lives_alone"),
        baseline_avg_amount=360.0,
        baseline_std_amount=220.0,
        typical_hour_start=8,
        typical_hour_end=21,
        typical_velocity_per_day=1.5,
        known_payees=("NTUC FairPrice", "SP Group", "Sarah Tan", "City Clinic", "Singtel"),
        known_payee_phones=("+6591234567",),  # Sarah, paid before
        contacts=(SeedContact("koc_marcus", "Marcus Tan", "+6580000010", "son", 1),),
        recipients=(
            SeedRecipient("rcp_ntuc", "NTUC FairPrice", "100-000111-2", "OCBC"),
            SeedRecipient("rcp_sarah", "Sarah Tan", "210-887654-9", "DBS", "+6591234567", "SG"),
            SeedRecipient("rcp_sp", "SP Group", "330-110022-4", "UOB"),
            SeedRecipient(
                "rcp_quick", "Quick Holdings Pte Ltd", "884-220931-0", "Standard Chartered",
                "+60182233445", "MY", ScamArchetype.government_impersonation,
            ),
            SeedRecipient(
                "rcp_crypto", "CryptoGain Capital", "771-559020-8", "Wise",
                "+85291234567", "HK", ScamArchetype.investment,
            ),
        ),
        recurring=(
            Recurring("Monthly Pension", 3200.0, "in", 30, 4, 2.0),
            Recurring("NTUC FairPrice", 84.30, every_days=9, count=6, first_days_ago=1.2, jitter=0.30),
            Recurring("SP Group", 132.0, every_days=30, count=4, first_days_ago=1.0, jitter=0.12),
            Recurring("Singtel", 42.90, every_days=30, count=3, first_days_ago=6.0),
            Recurring("Sarah Tan", 200.0, every_days=30, count=3, first_days_ago=0.85, memo="allowance"),
            Recurring("City Clinic", 45.0, every_days=45, count=2, first_days_ago=8.0, jitter=0.25),
        ),
        one_offs=(
            OneOff("Kopitiam Kim San", 12.60, 3.1),
            OneOff("Grab", 18.40, 5.4),
            OneOff("Guardian Pharmacy", 68.00, 11.2, memo="blood pressure meds"),
            OneOff("Marcus Tan", 500.0, 22.0, direction="in", memo="ang pow"),
            OneOff("Bishan Community Club", 30.0, 40.5, memo="tai chi class"),
        ),
    ),
    # 2) May Tan — repeat target. Two interventions already on file, so the console
    #    and the guardian-escalation path have history the moment they load.
    SeedPersona(
        id="acc_may",
        name="May Tan",
        phone="+6580000001",
        pin="445566",
        blurb="Retiree, 72 · two scams already blocked",
        account_number="OCBC •••• 8820",
        balance=18_240.0,
        age=72,
        vulnerability_flags=("elderly", "prior_scam_target", "lives_alone"),
        baseline_avg_amount=320.0,
        baseline_std_amount=180.0,
        typical_hour_start=9,
        typical_hour_end=20,
        typical_velocity_per_day=1.2,
        known_payees=("NTUC FairPrice", "SP Group", "City Clinic", "Church of St Andrew"),
        contacts=(
            SeedContact("koc_may1", "Marcus Tan", "+6580000010", "son", 1),
            SeedContact("koc_may2", "Grace Tan", "+6580000011", "daughter", 2),
        ),
        recipients=(
            SeedRecipient("rcp_clinic", "City Clinic", "440-220011-7", "DBS"),
            SeedRecipient("rcp_may_church", "Church of St Andrew", "120-330077-5", "OCBC"),
            SeedRecipient(
                "rcp_may_bank", "SecureBank Verification Unit", "990-114455-2", "Wise",
                "+60123998877", "MY", ScamArchetype.bank_impersonation,
            ),
        ),
        recurring=(
            Recurring("Pension", 2600.0, "in", 30, 4, 5.0),
            Recurring("City Clinic", 145.0, every_days=21, count=5, first_days_ago=3.0, jitter=0.22),
            Recurring("NTUC FairPrice", 62.0, every_days=10, count=6, first_days_ago=2.2, jitter=0.30),
            Recurring("Church of St Andrew", 50.0, every_days=30, count=4, first_days_ago=7.0, memo="offering"),
            Recurring("SP Group", 96.0, every_days=30, count=3, first_days_ago=4.0, jitter=0.10),
        ),
        one_offs=(
            OneOff("Grace Tan", 300.0, 14.3, direction="in", memo="for medicine"),
            OneOff("Eu Yan Sang TCM", 88.00, 9.6),
            OneOff("ComfortDelGro Taxi", 21.50, 4.2),
        ),
        cases=(
            SeedCase(
                slug="safe-account",
                amount=8000.0,
                payee="Quik Transfer Pte Ltd",
                account="884-553201-9",
                archetype=ScamArchetype.government_impersonation,
                score=0.97,
                days_ago=1.0,
                hours_ago=4.0,
                memo="urgent, move to safe account, tell no one",
                transcript=(
                    ("agent", "Hello May, I've paused an SGD 8,000 transfer to check it's really you. What's it for?"),
                    ("customer", "An officer said my account is in a money-laundering case."),
                    ("customer", "He told me to move it to a government safe account or I'll be arrested."),
                ),
                guardian="Marcus Tan",
                relationship="son",
            ),
            SeedCase(
                slug="release-fee",
                amount=4200.0,
                payee="GoldTrust Recovery",
                account="551-220190-3",
                archetype=ScamArchetype.investment,
                score=0.74,
                days_ago=12.0,
                memo="release fee for my profits",
                transcript=(
                    ("agent", "Can you tell me what this 4,200 payment is for?"),
                    ("customer", "My trading platform needs a release fee before I can withdraw my profits."),
                ),
                guardian="Grace Tan",
                relationship="daughter",
            ),
        ),
    ),
    # 3) Daniel Lim — salaried professional, high volume, all clear. His four-figure
    #    transfers are routine, which is the point: amount alone must not convict.
    SeedPersona(
        id="acc_daniel",
        name="Daniel Lim",
        phone="+6580000002",
        pin="778899",
        blurb="Professional, 34 · high volume, all clear",
        account_number="DBS •••• 9012",
        balance=41_180.0,
        age=34,
        baseline_avg_amount=1450.0,
        baseline_std_amount=900.0,
        typical_hour_start=7,
        typical_hour_end=23,
        typical_velocity_per_day=2.5,
        known_payees=("Income Tax", "GreenView MCST", "Jolene Lim", "DBS Home Loan", "Grab"),
        contacts=(SeedContact("koc_dan", "Jolene Lim", "+6580000012", "spouse", 1),),
        recipients=(
            SeedRecipient("rcp_mcst", "GreenView MCST", "200-110044-1", "OCBC"),
            SeedRecipient("rcp_dan_wife", "Jolene Lim", "210-554433-8", "DBS", "+6580000012", "SG"),
            SeedRecipient(
                "rcp_dan_job", "TalentBridge Recruitment", "667-880011-4", "Revolut",
                "+66812345678", "TH", ScamArchetype.job,
            ),
        ),
        recurring=(
            Recurring("Salary — Meridian Tech", 6800.0, "in", 30, 4, 1.0),
            Recurring("DBS Home Loan", 2380.0, every_days=30, count=4, first_days_ago=3.0, risk=0.10),
            Recurring("GreenView MCST", 420.0, every_days=30, count=4, first_days_ago=2.0, risk=0.12),
            Recurring("Jolene Lim", 1500.0, every_days=30, count=4, first_days_ago=4.0, memo="household", risk=0.18),
            Recurring("Amex Card", 1180.0, every_days=30, count=3, first_days_ago=6.0, jitter=0.28, risk=0.14),
            Recurring("Grab", 24.0, every_days=4, count=6, first_days_ago=0.6, jitter=0.45),
            Recurring("Anytime Fitness", 88.0, every_days=30, count=3, first_days_ago=9.0),
        ),
        one_offs=(
            OneOff("IRAS Income Tax", 3420.0, 26.4, memo="YA2025 instalment", risk=0.15),
            OneOff("Scoot Airlines", 862.0, 33.1, memo="KUL flights"),
            OneOff("Courts Megastore", 1299.0, 48.7, memo="washing machine", risk=0.13),
        ),
    ),
    # 4) Wong Ah Kow — 81, thin file, tiny amounts. Against this baseline any
    #    four-figure transfer is a screaming anomaly.
    SeedPersona(
        id="acc_wong",
        name="Wong Ah Kow",
        phone="+6580000003",
        pin="102030",
        blurb="Elderly, 81 · tiny spends, romance scam on file",
        account_number="UOB •••• 2210",
        balance=6_310.0,
        age=81,
        vulnerability_flags=("elderly", "lives_alone", "limited_digital_literacy"),
        baseline_avg_amount=180.0,
        baseline_std_amount=90.0,
        typical_hour_start=9,
        typical_hour_end=19,
        typical_velocity_per_day=0.6,
        known_payees=("SP Group", "NTUC FairPrice"),
        contacts=(SeedContact("koc_wong", "Linda Wong", "+6580000013", "daughter", 1),),
        recipients=(
            SeedRecipient("rcp_wong_sp", "SP Group", "330-110022-4", "UOB"),
            SeedRecipient(
                "rcp_wong_romance", "Daniel Ashworth", "990-771220-5", "Western Union",
                "+447700900123", "GB", ScamArchetype.romance,
            ),
        ),
        recurring=(
            Recurring("Pension", 1100.0, "in", 30, 4, 6.0),
            Recurring("SP Group", 58.0, every_days=30, count=4, first_days_ago=5.0, jitter=0.12),
            Recurring("NTUC FairPrice", 34.0, every_days=12, count=5, first_days_ago=2.5, jitter=0.35),
            Recurring("Linda Wong", 200.0, "in", 30, 3, 8.0, memo="from daughter"),
        ),
        one_offs=(
            OneOff("Kopitiam", 4.20, 2.3),
            OneOff("Ang Mo Kio Polyclinic", 15.00, 17.5),
        ),
        cases=(
            SeedCase(
                slug="stranded-partner",
                amount=3000.0,
                payee="Daniel (overseas)",
                account="990-771220-5",
                archetype=ScamArchetype.romance,
                score=0.88,
                days_ago=0.0,
                hours_ago=8.0,
                memo="for his flight, emergency",
                transcript=(
                    ("agent", "Can you tell me who this 3,000 transfer is going to?"),
                    ("customer", "My partner, we met online. He's stranded overseas and needs money for a flight."),
                    ("customer", "We haven't met in person yet but he'll pay me back."),
                ),
                guardian="Linda Wong",
                relationship="daughter",
            ),
        ),
    ),
    # 5) Priya Nair — mid-career, steady bills and school fees, one tech-support
    #    interception on file with a follow-up call worth replaying.
    SeedPersona(
        id="acc_priya",
        name="Priya Nair",
        phone="+6580000004",
        pin="135791",
        blurb="Mid-career, 58 · tech-support scam on file",
        account_number="OCBC •••• 5567",
        balance=12_640.0,
        age=58,
        vulnerability_flags=("recent_device_change",),
        baseline_avg_amount=540.0,
        baseline_std_amount=300.0,
        typical_hour_start=8,
        typical_hour_end=22,
        typical_velocity_per_day=1.8,
        known_payees=("StarHub", "NTUC FairPrice", "Anand Nair", "Great Eastern Life"),
        contacts=(SeedContact("koc_priya", "Anand Nair", "+6580000014", "spouse", 1),),
        recipients=(
            SeedRecipient("rcp_star", "StarHub", "300-220110-8", "DBS"),
            SeedRecipient("rcp_priya_ge", "Great Eastern Life", "410-990022-6", "OCBC"),
            SeedRecipient(
                "rcp_priya_tech", "SecureFix Support", "220-553010-2", "Payoneer",
                "+911140998877", "IN", ScamArchetype.tech_support,
            ),
        ),
        recurring=(
            Recurring("Salary — Horizon Logistics", 5200.0, "in", 30, 4, 7.0),
            Recurring("StarHub", 89.0, every_days=30, count=4, first_days_ago=2.0),
            Recurring("NTUC FairPrice", 118.0, every_days=8, count=6, first_days_ago=1.4, jitter=0.26),
            Recurring("Great Eastern Life", 310.0, every_days=30, count=4, first_days_ago=5.0),
            Recurring("Anand Nair", 400.0, every_days=30, count=3, first_days_ago=3.5, memo="shared bills"),
            Recurring("NUS Student Fees", 1450.0, every_days=90, count=2, first_days_ago=21.0, memo="semester fees", risk=0.11),
        ),
        one_offs=(
            OneOff("Watsons", 43.90, 6.7),
            OneOff("SP Group", 148.0, 12.1),
            OneOff("Sheng Siong", 76.20, 19.4),
        ),
        cases=(
            SeedCase(
                slug="refund-correction",
                amount=1800.0,
                payee="SecureFix Support",
                account="220-553010-2",
                archetype=ScamArchetype.tech_support,
                score=0.79,
                days_ago=2.0,
                hours_ago=6.0,
                memo="refund correction",
                transcript=(
                    ("agent", "What is this 1,800 payment for?"),
                    ("customer", "A technician fixed my computer remotely and said a refund was sent by mistake."),
                    ("customer", "He asked me to return the difference."),
                ),
                guardian="Anand Nair",
                relationship="spouse",
            ),
        ),
    ),
    # 6) Siti Rahman — gig worker. Many small movements a week: a high-velocity,
    #    low-amount baseline that is the mirror image of Robert's.
    SeedPersona(
        id="acc_siti",
        name="Siti Rahman",
        phone="+6580000005",
        pin="246810",
        blurb="Gig worker, 29 · frequent small payouts",
        account_number="UOB •••• 7734",
        balance=1_840.0,
        age=29,
        vulnerability_flags=("financial_stress",),
        baseline_avg_amount=95.0,
        baseline_std_amount=70.0,
        typical_hour_start=6,
        typical_hour_end=23,
        typical_velocity_per_day=3.2,
        known_payees=("Shell Petrol", "M1", "Mdm Chua"),
        contacts=(SeedContact("koc_siti", "Ibu Rahman", "+6580000015", "mother", 1),),
        recipients=(
            SeedRecipient("rcp_siti_rent", "Mdm Chua", "770-220110-3", "POSB", "+6590001122", "SG"),
            SeedRecipient(
                "rcp_siti_job", "GlobalTask Rewards", "556-330099-1", "Wise",
                "+8562098765432", "INTL", ScamArchetype.job,
            ),
        ),
        recurring=(
            Recurring("Grab Driver Payout", 310.0, "in", 7, 8, 1.0, jitter=0.32),
            Recurring("Shell Petrol", 62.0, every_days=7, count=7, first_days_ago=0.5, jitter=0.20),
            Recurring("Mdm Chua", 750.0, every_days=30, count=3, first_days_ago=4.0, memo="room rental", risk=0.09),
            Recurring("M1", 28.0, every_days=30, count=3, first_days_ago=8.0),
        ),
        one_offs=(
            OneOff("FairPrice Xpress", 23.40, 1.1),
            OneOff("Ibu Rahman", 200.0, 5.6, memo="untuk mak"),
        ),
    ),
    # 7) Robert Chen — SME owner. Five-figure supplier runs are normal here, so a
    #    transfer that would be critical for Wong is unremarkable for him.
    SeedPersona(
        id="acc_robert",
        name="Robert Chen",
        phone="+6580000006",
        pin="909090",
        blurb="Business owner, 46 · five-figure transfers are normal",
        account_number="SCB •••• 3390",
        balance=96_420.0,
        age=46,
        baseline_avg_amount=6800.0,
        baseline_std_amount=4200.0,
        typical_hour_start=7,
        typical_hour_end=21,
        typical_velocity_per_day=2.0,
        known_payees=("Hock Seng Steel", "IRAS", "JTC Corporation", "Singtel Business"),
        contacts=(SeedContact("koc_robert", "Mei Ling Chen", "+6580000016", "spouse", 1),),
        recipients=(
            SeedRecipient("rcp_rob_steel", "Hock Seng Steel Pte Ltd", "880-110044-9", "UOB"),
            SeedRecipient("rcp_rob_jtc", "JTC Corporation", "150-220033-7", "DBS"),
            SeedRecipient(
                "rcp_rob_inv", "Meridian Asset Partners", "334-889900-2", "Wise",
                "+85293334444", "HK", ScamArchetype.investment,
            ),
        ),
        recurring=(
            Recurring("Client — Sembcorp Marine", 18500.0, "in", 30, 3, 3.0, jitter=0.18),
            Recurring("Payroll — Chen Marine Supplies", 12400.0, every_days=30, count=3, first_days_ago=1.0, memo="staff payroll", risk=0.16),
            Recurring("Hock Seng Steel Pte Ltd", 6800.0, every_days=15, count=6, first_days_ago=2.0, jitter=0.30, memo="materials", risk=0.14),
            Recurring("JTC Corporation", 3100.0, every_days=30, count=3, first_days_ago=5.0, memo="workshop rent", risk=0.10),
            Recurring("IRAS Corporate Tax", 4200.0, every_days=90, count=2, first_days_ago=18.0, risk=0.12),
        ),
        one_offs=(
            OneOff("Client — PSA Singapore", 9200.0, 11.3, direction="in"),
            OneOff("Singtel Business", 340.0, 7.2),
            OneOff("Mei Ling Chen", 2000.0, 16.8, memo="monthly", risk=0.09),
        ),
    ),
    # 8) Marcus Tan — the guardian. Son to Alex and May, and already the trusted
    #    contact phone on both their accounts, so giving him an account snaps the
    #    network together rather than inventing a new relationship.
    SeedPersona(
        id="acc_marcus",
        name="Marcus Tan",
        phone="+6580000010",
        pin="321321",
        blurb="Son, 41 · guardian for Alex and May",
        account_number="DBS •••• 6628",
        balance=28_940.0,
        age=41,
        baseline_avg_amount=980.0,
        baseline_std_amount=620.0,
        typical_hour_start=7,
        typical_hour_end=23,
        typical_velocity_per_day=2.2,
        known_payees=("Alex Tan", "May Tan", "OCBC Home Loan", "NTUC FairPrice"),
        known_payee_phones=("+6580001234", "+6580000001"),
        contacts=(SeedContact("koc_marcus_wife", "Cheryl Tan", "+6580000017", "spouse", 1),),
        recipients=(
            SeedRecipient("rcp_mar_alex", "Alex Tan", "210-887100-4", "DBS", "+6580001234", "SG"),
            SeedRecipient("rcp_mar_may", "May Tan", "440-118820-6", "OCBC", "+6580000001", "SG"),
        ),
        recurring=(
            Recurring("Salary — Keppel Data Centres", 8400.0, "in", 30, 4, 2.0),
            Recurring("OCBC Home Loan", 2860.0, every_days=30, count=4, first_days_ago=4.0, risk=0.10),
            Recurring("May Tan", 600.0, every_days=30, count=4, first_days_ago=6.0, memo="for ma"),
            Recurring("NTUC FairPrice", 142.0, every_days=8, count=6, first_days_ago=1.0, jitter=0.28),
            Recurring("Cheryl Tan", 900.0, every_days=30, count=3, first_days_ago=3.0, memo="household"),
        ),
        one_offs=(
            OneOff("Alex Tan", 500.0, 22.0, memo="ang pow"),
            OneOff("Mount Alvernia Hospital", 380.0, 26.5, memo="pa's check-up", risk=0.11),
            OneOff("Klook", 1240.0, 44.0, memo="family trip"),
        ),
    ),
    # 9) Linda Wong — daughter and guardian to Wong Ah Kow. The 200/month she sends
    #    him is the mirror of the inbound line on his ledger.
    SeedPersona(
        id="acc_linda",
        name="Linda Wong",
        phone="+6580000013",
        pin="654654",
        blurb="Daughter, 52 · guardian for Wong Ah Kow",
        account_number="OCBC •••• 1145",
        balance=33_410.0,
        age=52,
        baseline_avg_amount=720.0,
        baseline_std_amount=480.0,
        typical_hour_start=8,
        typical_hour_end=22,
        typical_velocity_per_day=1.6,
        known_payees=("Wong Ah Kow", "SP Group", "NTUC Income", "Sheng Siong"),
        known_payee_phones=("+6580000003",),
        contacts=(SeedContact("koc_linda_bro", "Kelvin Wong", "+6580000018", "brother", 1),),
        recipients=(
            SeedRecipient("rcp_lin_pa", "Wong Ah Kow", "330-221055-2", "UOB", "+6580000003", "SG"),
        ),
        recurring=(
            Recurring("Salary — MOE Kindergarten", 5600.0, "in", 30, 4, 6.0),
            Recurring("Wong Ah Kow", 200.0, every_days=30, count=3, first_days_ago=8.0, memo="for pa"),
            Recurring("SP Group", 168.0, every_days=30, count=4, first_days_ago=3.0, jitter=0.12),
            Recurring("NTUC Income", 285.0, every_days=30, count=4, first_days_ago=11.0),
            Recurring("Sheng Siong", 96.0, every_days=9, count=6, first_days_ago=1.5, jitter=0.30),
        ),
        one_offs=(
            OneOff("Ang Mo Kio Polyclinic", 15.00, 17.5, memo="pa's appointment"),
            OneOff("Kelvin Wong", 400.0, 20.2, direction="in", memo="split for pa's care"),
            OneOff("Courts", 689.0, 37.0, memo="new fan for pa"),
        ),
    ),
)


PERSONAS_BY_ID: dict[str, SeedPersona] = {p.id: p for p in SEED_PERSONAS}


# ── The guardian network, pre-wired ────────────────────────────────────────────
# Marcus already watches both his parents and has their incident reports; Linda
# watches her father. The pending invitation to Wong exists so the accept/decline
# flow can be demonstrated on one device without setting an invite up first.
SEED_LINKS: tuple[SeedLink, ...] = (
    SeedLink(
        slug="marcus-alex",
        guardian_id="acc_marcus",
        protected_id="acc_alex",
        relationship="son",
        days_ago=120.0,
    ),
    SeedLink(
        slug="marcus-may",
        guardian_id="acc_marcus",
        protected_id="acc_may",
        relationship="son",
        days_ago=120.0,
        deliver_cases=("safe-account", "release-fee"),
        read_cases=("release-fee",),
        filed_cases=("release-fee",),
    ),
    SeedLink(
        slug="linda-wong",
        guardian_id="acc_linda",
        protected_id="acc_wong",
        relationship="daughter",
        days_ago=95.0,
        deliver_cases=("stranded-partner",),
    ),
    SeedLink(
        slug="marcus-wong",
        guardian_id="acc_marcus",
        protected_id="acc_wong",
        relationship="nephew",
        status="pending",
        days_ago=0.4,
    ),
)


def demo_credentials() -> list[dict]:
    """Phone/PIN pairs for the sign-in screen's demo picker (testing only)."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "phone": p.phone,
            "pin": p.pin,
            "blurb": p.blurb,
            "account_number": p.account_number,
            "balance": p.balance,
        }
        for p in SEED_PERSONAS
    ]
