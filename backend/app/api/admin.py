"""Control-centre API.

The bank's operations view over the agentic protection layer: every customer (each
running the wallet app), their profile, guardian network, transaction ledger, the
escalations raised on their behalf, and the full adjudication of every blocked or
intervened transfer. Read-only; the layer makes the decisions, this surfaces them.

Reads go through the repository's `load_bank()` snapshot, so the console reflects
persisted state when Supabase is configured and the seeded in-memory bank otherwise.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import repository
from app.wallet.repository import WalletRepository

router = APIRouter(prefix="/api/admin")


@router.get("/overview")
async def overview(repo: WalletRepository = Depends(repository)) -> dict:
    return (await repo.load_bank()).overview()


@router.get("/users")
async def users(repo: WalletRepository = Depends(repository)) -> list[dict]:
    return (await repo.load_bank()).directory()


@router.get("/users/{user_id}")
async def user_detail(
    user_id: str, repo: WalletRepository = Depends(repository)
) -> dict:
    profile = (await repo.load_bank()).profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="user not found")
    return profile


@router.get("/cases")
async def cases(
    status: str | None = None, repo: WalletRepository = Depends(repository)
) -> list[dict]:
    records = (await repo.load_bank()).all_cases()
    if status:
        records = [c for c in records if c.status == status]
    return [c.summary() for c in records]


@router.get("/cases/{case_id}")
async def case_detail(
    case_id: str, repo: WalletRepository = Depends(repository)
) -> dict:
    record = await repo.get_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="case not found")
    return record.detail()
