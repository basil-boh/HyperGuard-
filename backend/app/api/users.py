"""User management — the identity surface for the mobile profile picker.

No passwords: a user is picked or created on first launch and the choice is stored on
the device. These endpoints back that flow. `POST /session` exchanges a profile id
for a signed, expiring session token which the client then presents as a Bearer
header — the server never trusts a raw user-id header once `SESSION_SECRET` is set.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import current_user_id, repository
from app.config import Settings, get_settings
from app.integrations.push import register_token
from app.services.auth import mint_session_token
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


class SessionRequest(BaseModel):
    user_id: str = Field(min_length=1)


@router.post("/session")
async def create_session(
    body: SessionRequest,
    repo: WalletRepository = Depends(repository),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Mint a signed session token for an existing profile.

    Minting is deliberately unauthenticated for now (there are no credentials in
    the product) — the win over the old header is that identity is now a signed,
    expiring claim bound to a real profile, revocable by rotating the secret, and
    this endpoint is the seam where a passcode/OTP check slots in later.
    """
    if await repo.get_profile(body.user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    if not settings.user_auth_enabled:
        # Auth not configured — the legacy X-User-Id path is in effect.
        return {"user_id": body.user_id, "token": None, "expires_at": None}
    token, expires_at = mint_session_token(
        body.user_id, settings.session_secret, settings.session_ttl_hours * 3600
    )
    return {"user_id": body.user_id, "token": token, "expires_at": expires_at}


class PushToken(BaseModel):
    token: str = Field(min_length=8)


@router.post("/push-token")
async def push_token(
    body: PushToken, user_id: str = Depends(current_user_id)
) -> dict:
    """Bind this device's Expo push token to the active profile so HyperGuard can
    reach the user (or their guardians) when the app is backgrounded."""
    devices = register_token(user_id, body.token)
    return {"user_id": user_id, "devices": devices}


@router.get("/{user_id}")
async def get_user(
    user_id: str, repo: WalletRepository = Depends(repository)
) -> dict:
    profile = await repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="user not found")
    return profile
