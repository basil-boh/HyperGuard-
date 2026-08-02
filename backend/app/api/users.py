"""User management — the customer directory behind the control centre and the
mobile app's account picker.

Sign-in itself lives in `api/auth`: `POST /api/auth/register` is the route that
creates an account *with* a PIN. The `POST` here stays for tooling and the console,
and takes an optional PIN so a profile made this way can still be signed into.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import repository
from app.services.auth import PIN_LENGTH, hash_pin, is_valid_pin, normalize_phone
from app.wallet.repository import WalletRepository

router = APIRouter(prefix="/api/users")


class NewUser(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=3)
    age: int | None = None
    vulnerability_flags: list[str] = Field(default_factory=list)
    home_country: str = "SG"
    initial_balance: float = Field(default=1000.0, ge=0)
    # Optional: without one the profile exists but can't sign in until a PIN is set.
    pin: str | None = None


@router.get("")
async def list_users(repo: WalletRepository = Depends(repository)) -> list[dict]:
    return await repo.list_profiles()


@router.post("")
async def create_user(
    body: NewUser, repo: WalletRepository = Depends(repository)
) -> dict:
    if body.pin is not None and not is_valid_pin(body.pin):
        raise HTTPException(status_code=422, detail=f"PIN must be {PIN_LENGTH} digits")
    phone = normalize_phone(body.phone)
    if await repo.get_credentials(phone) is not None:
        raise HTTPException(status_code=409, detail="That phone number already has an account")
    return await repo.create_profile(
        name=body.name,
        phone=phone,
        age=body.age,
        vulnerability_flags=body.vulnerability_flags,
        home_country=body.home_country,
        initial_balance=body.initial_balance,
        pin_hash=hash_pin(body.pin) if body.pin else None,
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str, repo: WalletRepository = Depends(repository)
) -> dict:
    profile = await repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="user not found")
    return profile
