"""Wallet API, the simulated bank the mobile app drives.

A transfer here is the real entrypoint to the swarm: it builds a transaction from
the account holder's profile, runs the orchestrator in the background (so the app
can watch the agents work via polling), and applies the verdict to the balance.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph import get_orchestrator
from app.wallet.registry import get_registry
from app.wallet.store import get_bank, get_wallet

logger = logging.getLogger("hyperguard.wallet")
router = APIRouter(prefix="/api/wallet")


# ── Payloads ───────────────────────────────────────────────────────────────────
class AddRecipient(BaseModel):
    name: str = Field(min_length=1)
    account: str = Field(min_length=1)
    bank: str = "—"


class AddContact(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=3)
    relationship: str = "family"


class TransferRequest(BaseModel):
    recipient_id: str | None = None
    # ad-hoc payee (when not transferring to a saved recipient)
    payee_name: str | None = None
    payee_account: str | None = None
    amount: float = Field(gt=0)
    memo: str | None = None


# ── Account ──────────────────────────────────────────────────────────────────────
@router.get("")
async def account() -> dict:
    return get_wallet().summary()


@router.post("/reset")
async def reset() -> dict:
    get_bank().reset()
    return get_wallet().summary()


@router.get("/transactions")
async def transactions() -> list[dict]:
    return get_wallet().list_transactions()


# ── Recipients ───────────────────────────────────────────────────────────────────
@router.get("/recipients")
async def recipients() -> list[dict]:
    return get_wallet().list_recipients()


@router.post("/recipients")
async def add_recipient(body: AddRecipient) -> dict:
    return get_wallet().add_recipient(body.name, body.account, body.bank)


# ── Next of kin ──────────────────────────────────────────────────────────────────
@router.get("/contacts")
async def contacts() -> list[dict]:
    return get_wallet().list_contacts()


@router.post("/contacts")
async def add_contact(body: AddContact) -> dict:
    return get_wallet().add_contact(body.name, body.phone, body.relationship)


@router.delete("/contacts/{contact_id}")
async def remove_contact(contact_id: str) -> dict:
    if not get_wallet().remove_contact(contact_id):
        raise HTTPException(status_code=404, detail="contact not found")
    return {"removed": contact_id}


# ── Transfer → swarm ─────────────────────────────────────────────────────────────
@router.post("/transfer")
async def transfer(body: TransferRequest) -> dict:
    wallet = get_wallet()

    if body.amount > wallet.balance:
        raise HTTPException(status_code=400, detail="insufficient balance")

    archetype = None
    if body.recipient_id:
        rcp = wallet.find_recipient(body.recipient_id)
        if rcp is None:
            raise HTTPException(status_code=404, detail="recipient not found")
        payee_name, payee_account, archetype = rcp.name, rcp.account, rcp.archetype
    elif body.payee_name and body.payee_account:
        payee_name, payee_account = body.payee_name, body.payee_account
    else:
        raise HTTPException(status_code=422, detail="recipient_id or payee details required")

    txn = wallet.build_transaction(
        payee_name=payee_name,
        payee_account=payee_account,
        amount=body.amount,
        memo=body.memo,
        archetype=archetype,
    )

    case_id = f"HG-{uuid4().hex[:10].upper()}"
    orchestrator = get_orchestrator()
    registry = get_registry()
    # pre-create the bucket so the app can poll immediately, even before the first event
    registry._bucket(case_id)

    async def _drive() -> None:
        try:
            outcome = await orchestrator.run(wallet.owner, txn, case_id=case_id)
            wallet.apply_outcome(txn, outcome, case_id)
            get_bank().record_case(wallet, txn, outcome, case_id)
            registry.set_outcome(case_id, outcome)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("transfer %s failed: %s", case_id, exc)

    asyncio.create_task(_drive())
    return {"case_id": case_id, "transaction_id": txn.id, "status": "intervening"}


@router.get("/intervention/{case_id}")
async def intervention(case_id: str) -> dict:
    bucket = get_registry().get(case_id)
    if bucket is None:
        raise HTTPException(status_code=404, detail="unknown case")
    return {
        "case_id": case_id,
        "events": bucket["events"],
        "outcome": bucket["outcome"],
        "done": bucket["done"],
        "balance": round(get_wallet().balance, 2),
    }
