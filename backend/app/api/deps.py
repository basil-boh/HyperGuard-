"""Shared API dependencies for user-scoping.

Identity is resolved in three steps, most trustworthy first:

1. `Authorization: Bearer <token>` — a signed session token from `POST /api/auth/login`.
   This is what the mobile app sends once a customer has signed in.
2. `X-User-Id: acc_…` — the pre-login header, still honoured so curl demos and the
   original single-user client keep working. Set `ALLOW_HEADER_USER_OVERRIDE=false`
   to require a real token.
3. `settings.default_app_user_id` — the demo account, when neither is present.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.services.auth import verify_token
from app.wallet.repository import WalletRepository, get_repository
from app.wallet.store import Account


def repository() -> WalletRepository:
    return get_repository()


async def current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    settings: Settings = Depends(get_settings),
) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        user_id = verify_token(authorization[7:].strip(), secret=settings.auth_signing_key)
        if user_id:
            return user_id
        # A token that was sent but doesn't verify is an expired or tampered session:
        # say so, rather than silently falling through to the demo account.
        raise HTTPException(
            status_code=401,
            detail="Session expired, please sign in again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if x_user_id and settings.allow_header_user_override:
        return x_user_id
    if not settings.allow_header_user_override:
        raise HTTPException(
            status_code=401,
            detail="Sign in required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return settings.default_app_user_id


async def current_account(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> Account:
    acc = await repo.get_account(user_id)
    if acc is None:
        raise HTTPException(status_code=404, detail="user not found")
    return acc
