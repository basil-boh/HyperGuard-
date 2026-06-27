"""Control-centre API.

The bank's operations view over the agentic protection layer: every customer (each
running the wallet app), their profile, guardian network, transaction ledger, the
escalations raised on their behalf, and the full adjudication of every blocked or
intervened transfer. Read-only, the layer makes the decisions; this surfaces them.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.wallet.store import get_bank

router = APIRouter(prefix="/api/admin")


@router.get("/overview")
async def overview() -> dict:
    return get_bank().overview()


@router.get("/users")
async def users() -> list[dict]:
    return get_bank().directory()


@router.get("/users/{user_id}")
async def user_detail(user_id: str) -> dict:
    profile = get_bank().profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="user not found")
    return profile


@router.get("/cases")
async def cases(status: str | None = None) -> list[dict]:
    records = get_bank().all_cases()
    if status:
        records = [c for c in records if c.status == status]
    return [c.summary() for c in records]


@router.get("/cases/{case_id}")
async def case_detail(case_id: str) -> dict:
    record = get_bank().cases.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="case not found")
    return record.detail()
