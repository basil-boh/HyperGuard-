"""Wallet data access.

One interface, two implementations chosen at runtime by `settings.persistence_enabled`:

- `InMemoryRepository` — a thin delegate over the seeded singleton `Bank`. This is
  today's behaviour, byte-for-byte: `get_account` returns the *live* `Account`, so
  in-place mutations (balance, ledger) are the persisted state.
- `SupabaseRepository` — hydrates `Bank`/`Account` objects from Supabase rows, reuses
  their aggregate methods, and persists deltas. Every sync supabase call is off-loaded
  with `asyncio.to_thread` (the pattern established in `integrations/persistence.py`).

Because both return real `Account`/`Bank` objects, the wallet routes, admin aggregates,
the orchestrator call, and the registry are unchanged in spirit.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from uuid import uuid4

from app.config import Settings, get_settings
from app.schemas import (
    CustomerProfile,
    InterventionOutcome,
    ScamArchetype,
    TransactionRequest,
    TrustedContact,
)
from app.wallet.store import (
    Account,
    Bank,
    CaseRecord,
    LedgerEntry,
    Recipient,
    build_case_record,
    get_bank,
)

logger = logging.getLogger("hyperguard.repository")

_NEW_USER_AVG = 200.0
_NEW_USER_STD = 400.0


def _new_account_number() -> str:
    return f"DBS •••• {uuid4().hex[:4].upper()}"


# ── Interface ──────────────────────────────────────────────────────────────────
class WalletRepository(ABC):
    # identity / profiles
    @abstractmethod
    async def list_profiles(self) -> list[dict]: ...

    @abstractmethod
    async def get_profile(self, user_id: str) -> dict | None: ...

    @abstractmethod
    async def create_profile(
        self,
        *,
        name: str,
        phone: str,
        age: int | None = None,
        vulnerability_flags: list[str] | None = None,
        home_country: str = "SG",
        initial_balance: float = 1000.0,
    ) -> dict: ...

    @abstractmethod
    async def get_account(self, user_id: str) -> Account | None: ...

    # mutations
    @abstractmethod
    async def add_recipient(
        self, user_id: str, name: str, account: str, bank: str,
        phone: str | None, country: str | None,
    ) -> dict: ...

    @abstractmethod
    async def add_contact(
        self, user_id: str, name: str, phone: str, relationship: str
    ) -> dict: ...

    @abstractmethod
    async def remove_contact(self, user_id: str, contact_id: str) -> bool: ...

    @abstractmethod
    async def commit_transfer(
        self, user_id: str, account: Account, entry: LedgerEntry, case: CaseRecord
    ) -> None: ...

    # admin aggregates
    @abstractmethod
    async def load_bank(self) -> Bank: ...

    @abstractmethod
    async def get_case(self, case_id: str) -> CaseRecord | None: ...


# ── In-memory (back-compat / no creds) ──────────────────────────────────────────
class InMemoryRepository(WalletRepository):
    def __init__(self, bank: Bank | None = None) -> None:
        self._bank = bank or get_bank()

    async def list_profiles(self) -> list[dict]:
        return self._bank.directory()

    async def get_profile(self, user_id: str) -> dict | None:
        return self._bank.profile(user_id)

    async def create_profile(
        self, *, name, phone, age=None, vulnerability_flags=None,
        home_country="SG", initial_balance=1000.0,
    ) -> dict:
        uid = f"acc_{uuid4().hex[:8]}"
        owner = CustomerProfile(
            id=uid, name=name, phone=phone, age=age,
            vulnerability_flags=vulnerability_flags or [],
            baseline_avg_amount=_NEW_USER_AVG, baseline_std_amount=_NEW_USER_STD,
            home_country=home_country,
        )
        acc = Account(owner, account_number=_new_account_number(),
                      balance=float(initial_balance), recipients=[])
        self._bank.accounts[uid] = acc
        return _profile_summary(acc, self._bank.APP_USER)

    async def get_account(self, user_id: str) -> Account | None:
        return self._bank.account(user_id)

    async def add_recipient(self, user_id, name, account, bank, phone, country) -> dict:
        acc = self._require(user_id)
        return acc.add_recipient(name, account, bank, phone, country)

    async def add_contact(self, user_id, name, phone, relationship) -> dict:
        return self._require(user_id).add_contact(name, phone, relationship)

    async def remove_contact(self, user_id, contact_id) -> bool:
        return self._require(user_id).remove_contact(contact_id)

    async def commit_transfer(self, user_id, account, entry, case) -> None:
        # Balance + ledger already mutated on the live Account; just record the case.
        self._bank.cases[case.case_id] = case

    async def load_bank(self) -> Bank:
        return self._bank

    async def get_case(self, case_id) -> CaseRecord | None:
        return self._bank.cases.get(case_id)

    def _require(self, user_id: str) -> Account:
        acc = self._bank.account(user_id)
        if acc is None:
            raise KeyError(user_id)
        return acc


# ── Supabase ────────────────────────────────────────────────────────────────────
class SupabaseRepository(WalletRepository):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def _connect(self):
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                self._settings.supabase_url, self._settings.supabase_service_key
            )
        return self._client

    # -- reads ------------------------------------------------------------------
    async def get_account(self, user_id: str) -> Account | None:
        def _q():
            c = self._connect()
            u = c.table("users").select("*").eq("id", user_id).limit(1).execute().data
            if not u:
                return None
            rcps = c.table("recipients").select("*").eq("user_id", user_id).execute().data
            contacts = c.table("contacts").select("*").eq("user_id", user_id).execute().data
            txns = c.table("transactions").select("*").eq("user_id", user_id).execute().data
            return _hydrate_account(u[0], rcps, contacts, txns)

        return await asyncio.to_thread(_q)

    async def list_profiles(self) -> list[dict]:
        return (await self.load_bank()).directory()

    async def get_profile(self, user_id: str) -> dict | None:
        return (await self.load_bank()).profile(user_id)

    async def load_bank(self) -> Bank:
        def _q():
            c = self._connect()
            users = c.table("users").select("*").execute().data
            rcps = c.table("recipients").select("*").execute().data
            contacts = c.table("contacts").select("*").execute().data
            txns = c.table("transactions").select("*").execute().data
            cases = c.table("cases").select("*").execute().data
            return _hydrate_bank(users, rcps, contacts, txns, cases)

        return await asyncio.to_thread(_q)

    async def get_case(self, case_id: str) -> CaseRecord | None:
        def _q():
            c = self._connect()
            rows = c.table("cases").select("*").eq("case_id", case_id).limit(1).execute().data
            return _row_to_case(rows[0]) if rows else None

        return await asyncio.to_thread(_q)

    # -- writes -----------------------------------------------------------------
    async def create_profile(
        self, *, name, phone, age=None, vulnerability_flags=None,
        home_country="SG", initial_balance=1000.0,
    ) -> dict:
        uid = f"acc_{uuid4().hex[:8]}"
        account_number = _new_account_number()
        row = {
            "id": uid, "name": name, "phone": phone, "age": age,
            "vulnerability_flags": vulnerability_flags or [],
            "home_country": home_country, "account_number": account_number,
            "currency": "SGD", "balance": float(initial_balance),
            "is_app_user": False, "known_payees": [], "known_payee_phones": [],
        }

        def _w():
            self._connect().table("users").insert(row).execute()

        await asyncio.to_thread(_w)
        return {
            "id": uid, "name": name, "phone": phone,
            "account_number": account_number, "balance": float(initial_balance),
            "currency": "SGD", "is_app_user": False,
        }

    async def add_recipient(self, user_id, name, account, bank, phone, country) -> dict:
        from app.services.phone import parse_country

        rid = f"rcp_{uuid4().hex[:8]}"
        country = country or parse_country(phone)
        row = {
            "id": rid, "user_id": user_id, "name": name, "account": account,
            "bank": bank, "phone": phone, "country": country, "saved": True,
        }

        def _w():
            self._connect().table("recipients").insert(row).execute()

        await asyncio.to_thread(_w)
        return {
            "id": rid, "name": name, "account": account, "bank": bank,
            "phone": phone, "country": country, "saved": True,
        }

    async def add_contact(self, user_id, name, phone, relationship) -> dict:
        cid = f"koc_{uuid4().hex[:8]}"

        def _w():
            c = self._connect()
            existing = c.table("contacts").select("id").eq("user_id", user_id).execute().data
            priority = len(existing) + 1
            row = {
                "id": cid, "user_id": user_id, "name": name, "phone": phone,
                "relationship": relationship, "priority": priority,
            }
            c.table("contacts").insert(row).execute()
            return row

        row = await asyncio.to_thread(_w)
        return {
            "id": cid, "name": name, "phone": phone,
            "relationship": relationship, "priority": row["priority"],
        }

    async def remove_contact(self, user_id, contact_id) -> bool:
        def _w():
            res = (
                self._connect().table("contacts").delete()
                .eq("user_id", user_id).eq("id", contact_id).execute()
            )
            return bool(res.data)

        return await asyncio.to_thread(_w)

    async def commit_transfer(self, user_id, account, entry, case) -> None:
        txn_row = {
            "id": entry.id, "user_id": user_id, "ts": _iso(entry.ts),
            "direction": entry.direction, "counterparty": entry.counterparty,
            "amount": entry.amount, "currency": account.currency,
            "status": entry.status, "decision": entry.decision,
            "risk_score": entry.risk_score, "scam_type": entry.scam_type,
            "memo": entry.memo, "case_id": entry.case_id,
            "payee_account": case.transaction.get("payee_account"),
            "payee_phone": entry.counterparty_phone,
            "payee_country": case.transaction.get("payee_country"),
        }
        case_row = _case_to_row(case)

        def _w():
            c = self._connect()
            # Balance already reflects apply_outcome's decrement on the transient account.
            c.table("users").update({"balance": round(account.balance, 2)}).eq("id", user_id).execute()
            c.table("transactions").upsert(txn_row).execute()
            c.table("cases").upsert(case_row).execute()

        await asyncio.to_thread(_w)


# ── Hydration helpers ───────────────────────────────────────────────────────────
def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_ts(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _profile_summary(acc: Account, app_user_id: str) -> dict:
    return {
        "id": acc.owner.id, "name": acc.owner.name, "phone": acc.owner.phone,
        "account_number": acc.account_number, "balance": round(acc.balance, 2),
        "currency": acc.currency, "is_app_user": acc.owner.id == app_user_id,
    }


def _hydrate_account(u: dict, rcps: list[dict], contacts: list[dict], txns: list[dict]) -> Account:
    owner = CustomerProfile(
        id=u["id"], name=u["name"], phone=u["phone"], age=u.get("age"),
        vulnerability_flags=u.get("vulnerability_flags") or [],
        baseline_avg_amount=_NEW_USER_AVG, baseline_std_amount=_NEW_USER_STD,
        known_payees=u.get("known_payees") or [],
        known_payee_phones=u.get("known_payee_phones") or [],
        home_country=u.get("home_country") or "SG",
        trusted_contacts=[
            TrustedContact(
                id=c["id"], name=c["name"], phone=c["phone"],
                relationship=c["relationship"], priority=c.get("priority", 1),
            )
            for c in sorted(contacts, key=lambda c: c.get("priority", 1))
        ],
    )
    acc = Account(
        owner,
        account_number=u["account_number"],
        balance=float(u.get("balance") or 0),
        currency=u.get("currency") or "SGD",
        recipients=[
            Recipient(
                id=r["id"], name=r["name"], account=r.get("account") or "",
                bank=r.get("bank") or "—", phone=r.get("phone"), country=r.get("country"),
                saved=r.get("saved", True),
                archetype=ScamArchetype(r["archetype"]) if r.get("archetype") else None,
            )
            for r in rcps
        ],
    )
    acc.ledger = [
        LedgerEntry(
            id=t["id"], ts=_parse_ts(t["ts"]), direction=t["direction"],
            counterparty=t["counterparty"], amount=float(t["amount"]),
            status=t["status"], decision=t.get("decision"),
            risk_score=t.get("risk_score"), scam_type=t.get("scam_type"),
            memo=t.get("memo"), case_id=t.get("case_id"),
            counterparty_phone=t.get("payee_phone"),
        )
        for t in txns
    ]
    return acc


def _hydrate_bank(users, rcps, contacts, txns, cases) -> Bank:
    bank = Bank.empty()
    by_user_r: dict[str, list] = {}
    by_user_c: dict[str, list] = {}
    by_user_t: dict[str, list] = {}
    for r in rcps:
        by_user_r.setdefault(r["user_id"], []).append(r)
    for c in contacts:
        by_user_c.setdefault(c["user_id"], []).append(c)
    for t in txns:
        by_user_t.setdefault(t["user_id"], []).append(t)
    for u in users:
        acc = _hydrate_account(
            u, by_user_r.get(u["id"], []), by_user_c.get(u["id"], []),
            by_user_t.get(u["id"], []),
        )
        bank.accounts[u["id"]] = acc
    for row in cases:
        case = _row_to_case(row)
        bank.cases[case.case_id] = case
    return bank


def _case_to_row(case: CaseRecord) -> dict:
    return {
        "case_id": case.case_id, "user_id": case.user_id, "user_name": case.user_name,
        "created_at": case.created_at, "transaction": case.transaction,
        "decision": case.decision, "status": case.status, "risk_score": case.risk_score,
        "band": case.band, "risk_signals": case.risk_signals, "rationale": case.rationale,
        "scam_type": case.scam_type, "classification": case.classification,
        "guardian_alerts": case.guardian_alerts, "transcript": case.transcript,
        "evidence": case.evidence, "narrative": case.narrative,
    }


def _row_to_case(row: dict) -> CaseRecord:
    return CaseRecord(
        case_id=row["case_id"], user_id=row.get("user_id"),
        user_name=row.get("user_name"), created_at=row["created_at"],
        transaction=row.get("transaction") or {}, decision=row["decision"],
        status=row["status"], risk_score=float(row.get("risk_score") or 0),
        band=row.get("band") or "minimal", risk_signals=row.get("risk_signals") or [],
        rationale=row.get("rationale") or "", scam_type=row.get("scam_type"),
        classification=row.get("classification"),
        guardian_alerts=row.get("guardian_alerts") or [],
        transcript=row.get("transcript") or [], evidence=row.get("evidence"),
        narrative=row.get("narrative") or "",
    )


# ── Singleton ───────────────────────────────────────────────────────────────────
@lru_cache
def get_repository() -> WalletRepository:
    settings = get_settings()
    if settings.persistence_enabled:
        logger.info("Wallet persistence: Supabase")
        return SupabaseRepository(settings)
    logger.info("Wallet persistence: in-memory (no Supabase creds)")
    return InMemoryRepository()


# re-export for callers that build the outcome case record
__all__ = ["WalletRepository", "get_repository", "build_case_record"]
