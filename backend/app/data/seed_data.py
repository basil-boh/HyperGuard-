"""Demo personas and scenarios.

A small, opinionated fixture set that exercises every branch of the swarm:
a coercion scam (block + recover), a legitimate transfer (fast approve), an
investment scam, and a post-hoc fraud report (recovery-only). Timestamps are
derived at call time so the off-hours signal always fires relative to "now".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.schemas import (
    CustomerProfile,
    ScamArchetype,
    TransactionRequest,
    TransactionStatus,
    TrustedContact,
)

_CUSTOMERS: dict[str, CustomerProfile] = {
    "cust_may": CustomerProfile(
        id="cust_may",
        name="May Tan",
        phone="+6580000001",
        age=72,
        vulnerability_flags=["elderly", "prior_scam_target", "lives_alone"],
        baseline_avg_amount=320.0,
        baseline_std_amount=180.0,
        typical_hour_start=9,
        typical_hour_end=20,
        typical_velocity_per_day=1.0,
        known_payees=["SP Group", "NTUC FairPrice", "Sarah Tan", "City Clinic"],
        trusted_contacts=[
            TrustedContact(
                id="tc_marcus", name="Marcus Tan", phone="+6580000010",
                relationship="son", priority=1,
            ),
            TrustedContact(
                id="tc_sarah", name="Sarah Tan", phone="+6580000011",
                relationship="daughter", priority=2,
            ),
        ],
    ),
    "cust_daniel": CustomerProfile(
        id="cust_daniel",
        name="Daniel Lim",
        phone="+6580000002",
        age=34,
        vulnerability_flags=[],
        baseline_avg_amount=1450.0,
        baseline_std_amount=900.0,
        typical_hour_start=7,
        typical_hour_end=23,
        typical_velocity_per_day=2.5,
        known_payees=["Income Tax", "GreenView Condo MCST", "Jolene Lim", "DBS Card"],
        trusted_contacts=[
            TrustedContact(
                id="tc_jolene", name="Jolene Lim", phone="+6580000012",
                relationship="spouse", priority=1,
            ),
        ],
    ),
}


def _at(hour: int, *, days_ago: int = 0) -> datetime:
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return base.replace(hour=hour, minute=14, second=0, microsecond=0)


def _txn(**kwargs) -> TransactionRequest:
    kwargs.setdefault("id", f"txn_{uuid4().hex[:10]}")
    return TransactionRequest(**kwargs)


# scenario_id -> (metadata, factory)
def _scenarios() -> dict[str, dict]:
    return {
        "police_impersonation": {
            "title": "Police Impersonation",
            "subtitle": "Elderly customer told to move savings to a “safe account”",
            "customer_id": "cust_may",
            "severity": "critical",
            "expected": "Blocked + Recovery",
            "factory": lambda: _txn(
                customer_id="cust_may",
                amount=8000.0,
                payee_name="Quik Holdings Pte Ltd",
                payee_account="884-220931-0",
                channel="mobile_app",
                memo="urgent, transfer to safe account, do not tell anyone",
                requested_at=_at(2),
                recent_transfer_count_24h=4,
                seeded_archetype=ScamArchetype.government_impersonation,
            ),
        },
        "investment_scam": {
            "title": "Investment / Crypto Scam",
            "subtitle": "“Release fee” demanded before withdrawing fake profits",
            "customer_id": "cust_daniel",
            "severity": "high",
            "expected": "Blocked + Recovery",
            "factory": lambda: _txn(
                customer_id="cust_daniel",
                amount=15800.0,
                payee_name="CryptoGain Capital",
                payee_account="771-559020-8",
                channel="web",
                memo="withdrawal release fee for trading profit",
                requested_at=_at(22),
                recent_transfer_count_24h=3,
                seeded_archetype=ScamArchetype.investment,
            ),
        },
        "legitimate_transfer": {
            "title": "Legitimate Transfer",
            "subtitle": "Routine in-pattern payment that should sail through",
            "customer_id": "cust_may",
            "severity": "minimal",
            "expected": "Approved",
            "factory": lambda: _txn(
                customer_id="cust_may",
                amount=280.0,
                payee_name="NTUC FairPrice",
                payee_account="100-000111-2",
                channel="mobile_app",
                memo="monthly groceries",
                requested_at=_at(11),
                recent_transfer_count_24h=1,
                seeded_archetype=None,
                victim_script=[
                    "Oh hello, yes, this is my usual grocery top-up.",
                    "I do this every month, nobody asked me to.",
                ],
            ),
        },
        "post_hoc_recovery": {
            "title": "Post-Incident Recovery",
            "subtitle": "Fraud already processed, assemble the evidence package",
            "customer_id": "cust_may",
            "severity": "critical",
            "expected": "Recovery only",
            "factory": lambda: _txn(
                customer_id="cust_may",
                amount=12500.0,
                payee_name="Sunrise Mule Services",
                payee_account="990-100455-1",
                channel="mobile_app",
                memo="safe account transfer as instructed by officer",
                requested_at=_at(3, days_ago=1),
                recent_transfer_count_24h=5,
                status=TransactionStatus.completed,
                seeded_archetype=ScamArchetype.government_impersonation,
            ),
        },
    }


def list_scenarios() -> list[dict]:
    out = []
    for sid, meta in _scenarios().items():
        out.append(
            {
                "id": sid,
                "title": meta["title"],
                "subtitle": meta["subtitle"],
                "customer_id": meta["customer_id"],
                "customer_name": _CUSTOMERS[meta["customer_id"]].name,
                "severity": meta["severity"],
                "expected": meta["expected"],
            }
        )
    return out


def get_customer(customer_id: str) -> CustomerProfile | None:
    return _CUSTOMERS.get(customer_id)


def build_scenario(scenario_id: str) -> tuple[CustomerProfile, TransactionRequest]:
    scenarios = _scenarios()
    if scenario_id not in scenarios:
        raise KeyError(scenario_id)
    meta = scenarios[scenario_id]
    customer = _CUSTOMERS[meta["customer_id"]]
    return customer, meta["factory"]()
