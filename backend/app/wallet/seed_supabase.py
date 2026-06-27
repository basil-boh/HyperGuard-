"""Idempotent Supabase seeding.

On first boot with persistence enabled, populate the tables from the same in-memory
seed used in the demo (the 5 customers, their recipients/contacts/ledger, and the
historical blocked cases). Guarded by the presence of the app user, so re-runs and
multiple workers are safe and never clobber live data.
"""

from __future__ import annotations

import asyncio
import logging

from app.wallet.repository import WalletRepository, SupabaseRepository, _case_to_row
from app.wallet.store import Bank

logger = logging.getLogger("hyperguard.seed")


def _iso(dt) -> str:
    return dt.isoformat()


async def ensure_seeded(repo: WalletRepository) -> None:
    if not isinstance(repo, SupabaseRepository):
        return

    def _seed() -> str:
        client = repo._connect()
        existing = client.table("users").select("id").eq("id", Bank.APP_USER).execute().data
        if existing:
            return "already-seeded"

        bank = Bank()  # seeded singleton-equivalent (fresh)
        users, recipients, contacts, transactions, cases = [], [], [], [], []
        for acc in bank.list_accounts():
            o = acc.owner
            users.append({
                "id": o.id, "name": o.name, "phone": o.phone, "age": o.age,
                "vulnerability_flags": o.vulnerability_flags,
                "home_country": o.home_country,
                "known_payees": o.known_payees,
                "known_payee_phones": o.known_payee_phones,
                "account_number": acc.account_number, "currency": acc.currency,
                "balance": round(acc.balance, 2),
                "is_app_user": o.id == Bank.APP_USER,
            })
            for r in acc.recipients:
                recipients.append({
                    "id": r.id, "user_id": o.id, "name": r.name, "account": r.account,
                    "bank": r.bank, "phone": r.phone, "country": r.country,
                    "saved": r.saved,
                    "archetype": r.archetype.value if r.archetype else None,
                })
            for c in o.trusted_contacts:
                contacts.append({
                    "id": c.id, "user_id": o.id, "name": c.name, "phone": c.phone,
                    "relationship": c.relationship, "priority": c.priority,
                })
            for e in acc.ledger:
                transactions.append({
                    "id": e.id, "user_id": o.id, "ts": _iso(e.ts),
                    "direction": e.direction, "counterparty": e.counterparty,
                    "amount": e.amount, "currency": acc.currency, "status": e.status,
                    "decision": e.decision, "risk_score": e.risk_score,
                    "scam_type": e.scam_type, "memo": e.memo, "case_id": e.case_id,
                    "payee_account": None, "payee_phone": e.counterparty_phone,
                    "payee_country": None,
                })
        for case in bank.cases.values():
            cases.append(_case_to_row(case))

        # Order matters for FKs: users first.
        client.table("users").upsert(users).execute()
        if recipients:
            client.table("recipients").upsert(recipients).execute()
        if contacts:
            client.table("contacts").upsert(contacts).execute()
        if transactions:
            client.table("transactions").upsert(transactions).execute()
        if cases:
            client.table("cases").upsert(cases).execute()
        return f"seeded {len(users)} users, {len(cases)} cases"

    try:
        result = await asyncio.to_thread(_seed)
        logger.info("Supabase seed: %s", result)
    except Exception as exc:  # pragma: no cover - network/setup
        logger.warning("Supabase seeding failed (continuing): %s", exc)
