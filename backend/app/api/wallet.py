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
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import current_account, current_user_id, repository
from app.api.network import deliver_incident_report, effective_transfer_limit
from app.config import get_settings
from app.graph import get_orchestrator
from app.services.baselines import derive_profile
from app.services.model_policy import peek_usage
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
async def account(
    acc: Account = Depends(current_account),
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    # The limit rides along with the account summary so the wallet can show it up
    # front, rather than only discovering it when a transfer is refused.
    limit = await effective_transfer_limit(repo, user_id)
    payload = acc.summary()
    if limit is not None:
        briefs = await repo.get_user_brief([limit.guardian_user_id])
        payload["transfer_limit"] = {
            "amount": limit.amount,
            "set_by": briefs.get(limit.guardian_user_id, {}).get("name", ""),
            "relationship": limit.relationship,
        }
    return payload


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
    contact = await repo.add_contact(user_id, body.name, body.phone, body.relationship)
    # If this guardian already banks with HyperGuard, join the two accounts as well.
    # No invitation is needed: consent belongs to the protected person, and they are
    # the one making this request.
    linked = await link_existing_guardian(
        repo, protected_user_id=user_id, phone=body.phone, relationship=body.relationship
    )
    return {**contact, "linked_account": linked}


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

    # A guardian's ceiling is checked before the swarm runs: it's a standing
    # instruction from someone this customer trusted while they were clear-headed,
    # not a risk judgement to be argued with mid-call.
    limit = await effective_transfer_limit(repo, user_id)
    if limit is not None and body.amount > limit.amount:
        briefs = await repo.get_user_brief([limit.guardian_user_id])
        guardian = briefs.get(limit.guardian_user_id, {}).get("name", "your guardian")
        raise HTTPException(
            status_code=403,
            detail=(
                f"{acc.currency} {body.amount:,.2f} is over the "
                f"{acc.currency} {limit.amount:,.2f} limit {guardian} "
                f"({limit.relationship}) set for this account. "
                f"Ask {guardian.split()[0]} if you need it raised."
            ),
        )

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
            # A blocked transfer is exactly what a guardian signed up to hear about,
            # so the report goes out without waiting to be asked. Best-effort: a
            # delivery failure must not lose the verdict.
            if case.decision == "block":
                try:
                    await deliver_incident_report(repo, case)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("incident delivery for %s failed: %s", case_id, exc)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("transfer %s failed: %s", case_id, exc)

    asyncio.create_task(_drive())
    return {"case_id": case_id, "transaction_id": txn.id, "status": "intervening"}


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
        # What the tiered models cost this case — see services/model_policy. Falls
        # back to the live ledger so it's available before the follow-up finishes.
        "model_usage": bucket.get("model_usage") or _live_usage(case_id),
    }


def _live_usage(case_id: str) -> dict | None:
    usage = peek_usage(case_id)
    return usage.summary(get_settings()) if usage else None
