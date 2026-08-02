"""Idempotent Supabase seeding.

On boot with persistence enabled, reconcile the database against the customer book
in `seed_profiles`. Two paths, both safe to re-run and both non-destructive:

- **Empty database** — insert every customer, recipient, contact, ledger row and
  historical case.
- **Already seeded** — insert only the customers that are new, backfill a `pin_hash`
  for any that predate the login flow, and upsert the reference/history rows. Every
  seeded row has a stable id, so an upsert updates in place; balances of existing
  customers are never overwritten, because a live session may have moved money.
"""

from __future__ import annotations

import asyncio
import logging

from app.wallet.network import filing_to_row, link_to_row, report_to_row
from app.wallet.repository import SupabaseRepository, WalletRepository, _case_to_row
from app.wallet.store import Bank

logger = logging.getLogger("hyperguard.seed")


def _iso(dt) -> str:
    return dt.isoformat()


def _rows_from_bank(bank: Bank) -> tuple[list, list, list, list, list]:
    users, recipients, contacts, transactions, cases = [], [], [], [], []
    for acc in bank.list_accounts():
        owner = acc.owner
        users.append({
            "id": owner.id, "name": owner.name, "phone": owner.phone, "age": owner.age,
            "vulnerability_flags": owner.vulnerability_flags,
            "home_country": owner.home_country,
            "known_payees": owner.known_payees,
            "known_payee_phones": owner.known_payee_phones,
            "account_number": acc.account_number, "currency": acc.currency,
            "balance": round(acc.balance, 2),
            "is_app_user": owner.id == Bank.APP_USER,
            "pin_hash": acc.pin_hash,
        })
        for r in acc.recipients:
            recipients.append({
                "id": r.id, "user_id": owner.id, "name": r.name, "account": r.account,
                "bank": r.bank, "phone": r.phone, "country": r.country, "saved": r.saved,
                "archetype": r.archetype.value if r.archetype else None,
            })
        for c in owner.trusted_contacts:
            contacts.append({
                "id": c.id, "user_id": owner.id, "name": c.name, "phone": c.phone,
                "relationship": c.relationship, "priority": c.priority,
            })
        for e in acc.ledger:
            transactions.append({
                "id": e.id, "user_id": owner.id, "ts": _iso(e.ts),
                "direction": e.direction, "counterparty": e.counterparty,
                "amount": e.amount, "currency": acc.currency, "status": e.status,
                "decision": e.decision, "risk_score": e.risk_score,
                "scam_type": e.scam_type, "memo": e.memo, "case_id": e.case_id,
                "payee_account": None, "payee_phone": e.counterparty_phone,
                "payee_country": None,
            })
    cases = [_case_to_row(case) for case in bank.cases.values()]
    return users, recipients, contacts, transactions, cases


def _network_rows_from_bank(bank: Bank) -> tuple[list, list, list]:
    return (
        [link_to_row(link) for link in bank.links.values()],
        [report_to_row(report) for report in bank.incidents.values()],
        [filing_to_row(filing) for filing in bank.filings.values()],
    )


def _existing_users(client) -> tuple[dict[str, dict], bool]:
    """Current user rows keyed by id, plus whether the `pin_hash` column exists."""
    try:
        rows = client.table("users").select("id,pin_hash").execute().data
        return {r["id"]: r for r in rows}, True
    except Exception:
        logger.warning(
            "users.pin_hash is missing — sign-in will not work until you run: "
            "alter table users add column if not exists pin_hash text;"
        )
        rows = client.table("users").select("id").execute().data
        return {r["id"]: r for r in rows}, False


async def ensure_seeded(repo: WalletRepository) -> None:
    if not isinstance(repo, SupabaseRepository):
        return

    def _seed() -> str:
        client = repo._connect()
        existing, has_pin_column = _existing_users(client)
        bank = Bank()  # a fresh materialisation of the customer book
        users, recipients, contacts, transactions, cases = _rows_from_bank(bank)

        if not has_pin_column:
            for row in users:
                row.pop("pin_hash", None)

        # 1) New customers, in full. Must precede their child rows (FKs).
        added = [u for u in users if u["id"] not in existing]
        if added:
            client.table("users").upsert(added).execute()

        # 2) Existing customers: only ever touch the credential, never the balance.
        backfilled = 0
        if has_pin_column:
            for row in users:
                current = existing.get(row["id"])
                if current is not None and not current.get("pin_hash"):
                    client.table("users").update(
                        {"pin_hash": row["pin_hash"], "phone": row["phone"]}
                    ).eq("id", row["id"]).execute()
                    backfilled += 1

        # 3) Reference data and history — stable ids, so this updates in place and
        #    leaves anything a live session created untouched.
        for table, rows in (
            ("recipients", recipients),
            ("contacts", contacts),
            ("transactions", transactions),
            ("cases", cases),
        ):
            if rows:
                client.table(table).upsert(rows).execute()

        # 4) The guardian network. Separate and best-effort: these tables post-date
        #    the base schema, and a database without them should still seed the rest.
        links, reports, filings = _network_rows_from_bank(bank)
        network_note = ""
        try:
            for table, rows in (
                ("guardian_links", links),
                ("incident_reports", reports),
                ("authority_filings", filings),
            ):
                if rows:
                    client.table(table).upsert(rows).execute()
            network_note = (
                f", {len(links)} guardian link(s) and {len(reports)} incident report(s)"
            )
        except Exception as exc:
            logger.warning(
                "guardian network not seeded — re-run db/schema.sql to create "
                "guardian_links / incident_reports / authority_filings: %s",
                exc,
            )
            network_note = " (guardian network tables missing — re-run db/schema.sql)"

        return (
            f"{len(added)} new customer(s), {backfilled} PIN(s) backfilled, "
            f"{len(transactions)} transactions and {len(cases)} cases reconciled"
            f"{network_note}"
        )

    try:
        result = await asyncio.to_thread(_seed)
        logger.info("Supabase seed: %s", result)
    except Exception as exc:  # pragma: no cover - network/setup
        logger.warning("Supabase seeding failed (continuing): %s", exc)
