"""Shared API dependencies for user-scoping.

The mobile client identifies the active user with an `X-User-Id` header (chosen on
the profile picker). When absent we fall back to `settings.default_app_user_id`, so
the original single-user demo client keeps working unchanged.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.wallet.repository import WalletRepository, get_repository
from app.wallet.store import Account


def repository() -> WalletRepository:
    return get_repository()


async def current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    settings: Settings = Depends(get_settings),
) -> str:
    return x_user_id or settings.default_app_user_id


async def current_account(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> Account:
    acc = await repo.get_account(user_id)
    if acc is None:
        raise HTTPException(status_code=404, detail="user not found")
    return acc
