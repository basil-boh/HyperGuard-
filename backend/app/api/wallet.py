"""Wallet API, the simulated bank the mobile app drives.

Every route is user-scoped via the `X-User-Id` header (see `api/deps.py`); with no
header it falls back to the demo user. A transfer is the real entrypoint to the swarm:
it builds a transaction from the account holder's *learned* profile, runs the
orchestrator in the background (so the app can watch the agents work via polling), and
persists the verdict (balance + ledger + case) through the repository.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import current_account, current_user_id, repository
from app.config import get_settings
from app.domain.events import EventType, SwarmEvent
from app.graph import get_orchestrator
from app.integrations.event_bus import get_event_bus
from app.integrations.push import phone_key
from app.services.baselines import derive_profile
from app.wallet.registry import get_registry
from app.wallet.repository import WalletRepository
from app.wallet.store import Account, build_case_record

logger = logging.getLogger("hyperguard.wallet")
router = APIRouter(prefix="/api/wallet")


# ── Payloads ───────────────────────────────────────────────────────────────────
class AddRecipient(BaseModel):
    name: str = Field(min_length=1)
    account: str = "—"
    bank: str = "—"
    phone: str | None = None
    country: str | None = None


class AddContact(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=3)
    relationship: str = "family"


class TransferRequest(BaseModel):
    recipient_id: str | None = None
    # ad-hoc payee (when not transferring to a saved recipient)
    payee_name: str | None = None
    payee_account: str | None = None
    payee_phone: str | None = None
    amount: float = Field(gt=0)
    memo: str | None = None


# ── Account ──────────────────────────────────────────────────────────────────────
@router.get("")
async def account(acc: Account = Depends(current_account)) -> dict:
    return acc.summary()


@router.post("/reset")
async def reset() -> dict:
    settings = get_settings()
    if settings.persistence_enabled:
        raise HTTPException(status_code=400, detail="reset is disabled when persistence is on")
    from app.wallet.store import get_bank, get_wallet

    get_bank().reset()
    return get_wallet().summary()


@router.get("/transactions")
async def transactions(acc: Account = Depends(current_account)) -> list[dict]:
    return acc.list_transactions()


# ── Recipients ───────────────────────────────────────────────────────────────────
@router.get("/recipients")
async def recipients(acc: Account = Depends(current_account)) -> list[dict]:
    return acc.list_recipients()


@router.post("/recipients")
async def add_recipient(
    body: AddRecipient,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    return await repo.add_recipient(
        user_id, body.name, body.account, body.bank, body.phone, body.country
    )


# ── Next of kin ──────────────────────────────────────────────────────────────────
@router.get("/contacts")
async def contacts(acc: Account = Depends(current_account)) -> list[dict]:
    return acc.list_contacts()


@router.post("/contacts")
async def add_contact(
    body: AddContact,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    return await repo.add_contact(user_id, body.name, body.phone, body.relationship)


@router.delete("/contacts/{contact_id}")
async def remove_contact(
    contact_id: str,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    if not await repo.remove_contact(user_id, contact_id):
        raise HTTPException(status_code=404, detail="contact not found")
    return {"removed": contact_id}


# ── Transfer → swarm ─────────────────────────────────────────────────────────────
@router.post("/transfer")
async def transfer(
    body: TransferRequest,
    user_id: str = Depends(current_user_id),
    acc: Account = Depends(current_account),
    repo: WalletRepository = Depends(repository),
) -> dict:
    if body.amount > acc.balance:
        raise HTTPException(status_code=400, detail="insufficient balance")

    archetype = None
    payee_phone = body.payee_phone
    if body.recipient_id:
        rcp = acc.find_recipient(body.recipient_id)
        if rcp is None:
            raise HTTPException(status_code=404, detail="recipient not found")
        payee_name, payee_account, archetype = rcp.name, rcp.account, rcp.archetype
        payee_phone = rcp.phone or payee_phone
    elif body.payee_name and (body.payee_account or body.payee_phone):
        payee_name, payee_account = body.payee_name, (body.payee_account or "—")
    else:
        raise HTTPException(status_code=422, detail="recipient_id or payee details required")

    txn = acc.build_transaction(
        payee_name=payee_name,
        payee_account=payee_account,
        payee_phone=payee_phone,
        amount=body.amount,
        memo=body.memo,
        archetype=archetype,
    )

    # Score against the customer's *learned* behaviour, not a static seed.
    profile = derive_profile(acc)

    case_id = f"HG-{uuid4().hex[:10].upper()}"
    orchestrator = get_orchestrator()
    registry = get_registry()
    # pre-create the bucket so the app can poll immediately, even before the first event
    registry._bucket(case_id)

    async def _drive() -> None:
        try:
            outcome = await orchestrator.run(profile, txn, case_id=case_id)
            entry = acc.apply_outcome(txn, outcome, case_id)
            case = build_case_record(acc, txn, outcome, case_id)
            await repo.commit_transfer(user_id, acc, entry, case)
            registry.set_outcome(case_id, outcome)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("transfer %s failed: %s", case_id, exc)

    asyncio.create_task(_drive())
    return {"case_id": case_id, "transaction_id": txn.id, "status": "intervening"}


# ── Guardian view ────────────────────────────────────────────────────────────────
class GuardianActionRequest(BaseModel):
    action: Literal["release", "hold"]


def _is_guardian_of(me: Account, ward: Account) -> bool:
    my_key = phone_key(me.owner.phone)
    return my_key is not None and any(
        phone_key(c.phone) == my_key for c in ward.owner.trusted_contacts
    )


@router.get("/guardian/cases")
async def guardian_cases(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> list[dict]:
    """Cases for every account that lists the current user as next of kin —
    in-flight interventions first (watchable live), then the case history."""
    bank = await repo.load_bank()
    me = bank.account(user_id)
    if me is None:
        raise HTTPException(status_code=404, detail="user not found")
    wards = {
        acc.owner.id: acc
        for acc in bank.list_accounts()
        if acc.owner.id != user_id and _is_guardian_of(me, acc)
    }

    rows: list[dict] = []
    seen: set[str] = set()
    for case_id, bucket in reversed(get_registry().open_cases()):
        cust = bucket.get("customer") or {}
        acc = wards.get(cust.get("id"))
        if acc is None:
            continue
        txn = bucket.get("transaction") or {}
        risk = bucket.get("risk") or {}
        rows.append({
            "case_id": case_id,
            "ward_id": acc.owner.id,
            "ward_name": acc.owner.name,
            "active": True,
            "created_at": txn.get("requested_at"),
            "amount": txn.get("amount"),
            "currency": txn.get("currency", "SGD"),
            "payee_name": txn.get("payee_name"),
            "decision": None,
            "status": "intervening",
            "risk_score": (risk.get("score") if isinstance(risk, dict) else None),
            "scam_title": (bucket.get("classification") or {}).get("title"),
        })
        seen.add(case_id)
    for acc in wards.values():
        for case in bank.cases_for(acc.owner.id):
            if case.case_id in seen:
                continue
            rows.append({
                "case_id": case.case_id,
                "ward_id": acc.owner.id,
                "ward_name": acc.owner.name,
                "active": False,
                "created_at": case.created_at,
                "amount": case.transaction.get("amount"),
                "currency": case.transaction.get("currency", "SGD"),
                "payee_name": case.transaction.get("payee_name"),
                "decision": case.decision,
                "status": case.status,
                "risk_score": case.risk_score,
                "scam_title": (case.classification or {}).get("title"),
            })
    return rows


@router.post("/guardian/cases/{case_id}/action")
async def guardian_action(
    case_id: str,
    body: GuardianActionRequest,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    """A guardian's verdict on a blocked transfer: release it (the ward really did
    mean it) or keep the block. Only available once the swarm has decided."""
    case = await repo.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=409, detail="intervention still in progress")
    ward = await repo.get_account(case.user_id)
    me = await repo.get_account(user_id)
    if ward is None or me is None:
        raise HTTPException(status_code=404, detail="user not found")
    if not _is_guardian_of(me, ward):
        raise HTTPException(status_code=403, detail="you are not a guardian for this account")

    entry = next((e for e in ward.ledger if e.case_id == case_id), None)

    if body.action == "release":
        if case.status != "blocked":
            raise HTTPException(status_code=400, detail="transfer is not blocked")
        if entry is not None:
            if ward.balance < entry.amount:
                raise HTTPException(status_code=400, detail="insufficient balance to release")
            ward.balance -= entry.amount
            entry.status = "approved"
            entry.decision = "approve"
        case.status = "approved"
        case.decision = "approve"
        case.narrative = (case.narrative or "").strip() + f" Released by guardian {me.owner.name} after review."
        result = "released"
    else:
        for alert in case.guardian_alerts:
            alert["acknowledged"] = True
            alert["status"] = "acknowledged"
        case.narrative = (case.narrative or "").strip() + f" Guardian {me.owner.name} confirmed the block."
        result = "held"

    if entry is not None:
        await repo.commit_transfer(case.user_id, ward, entry, case)
    await get_event_bus().publish(
        SwarmEvent(
            type=EventType.guardian_action,
            case_id=case_id,
            agent="guardian",
            payload={"action": result, "by": me.owner.name},
        )
    )
    return {"case_id": case_id, "action": result, "status": case.status, "decision": case.decision}


@router.get("/intervention/{case_id}")
async def intervention(
    case_id: str, acc: Account = Depends(current_account)
) -> dict:
    bucket = get_registry().get(case_id)
    if bucket is None:
        raise HTTPException(status_code=404, detail="unknown case")
    # A live interactive call runs its interview + LLM follow-up *after* the graph closes
    # the case, so the client must keep polling until the assessment lands.
    had_interactive = any(
        e.get("type") == "call.started" and (e.get("payload") or {}).get("interactive")
        for e in bucket["events"]
    )
    followup_pending = had_interactive and bucket.get("assessment") is None
    return {
        "case_id": case_id,
        "events": bucket["events"],
        "outcome": bucket["outcome"],
        "done": bucket["done"],
        "followup_pending": followup_pending,
        "balance": round(acc.balance, 2),
        # Voice follow-up (populated after an interactive call).
        "context": bucket.get("context") or [],
        "assessment": bucket.get("assessment"),
        "escalation": bucket.get("escalation"),
        "report": bucket.get("report"),
    }
