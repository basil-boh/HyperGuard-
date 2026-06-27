"""User management — the identity surface for the mobile profile picker.

No passwords: a user is picked or created on first launch and the choice is stored on
the device. These endpoints back that flow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import repository
from app.wallet.repository import WalletRepository

router = APIRouter(prefix="/api/users")


class NewUser(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=3)
    age: int | None = None
    vulnerability_flags: list[str] = Field(default_factory=list)
    home_country: str = "SG"
    initial_balance: float = Field(default=1000.0, ge=0)


@router.get("")
async def list_users(repo: WalletRepository = Depends(repository)) -> list[dict]:
    return await repo.list_profiles()


@router.post("")
async def create_user(
    body: NewUser, repo: WalletRepository = Depends(repository)
) -> dict:
    return await repo.create_profile(
        name=body.name,
        phone=body.phone,
        age=body.age,
        vulnerability_flags=body.vulnerability_flags,
        home_country=body.home_country,
        initial_balance=body.initial_balance,
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str, repo: WalletRepository = Depends(repository)
) -> dict:
    profile = await repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="user not found")
    return profile
