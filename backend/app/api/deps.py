"""Shared API dependencies: user-scoping and admin auth.

With `SESSION_SECRET` set, the mobile client must present a signed session token
(`Authorization: Bearer …`, minted via `POST /api/users/session`) and the raw
`X-User-Id` header is no longer trusted. Without it (local dev / demo), the legacy
header + `settings.default_app_user_id` fallback keeps the original client working.

`require_admin` guards the control-centre surface with `ADMIN_API_KEY`; when the
key is unset the surface only stays open in development.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.services.auth import check_shared_key, verify_session_token
from app.wallet.repository import WalletRepository, get_repository
from app.wallet.store import Account


def repository() -> WalletRepository:
    return get_repository()


def bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


async def current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    if settings.user_auth_enabled:
        token = bearer_token(authorization)
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="missing session token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = verify_session_token(token, settings.session_secret)
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="invalid or expired session token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    return x_user_id or settings.default_app_user_id


async def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.admin_auth_enabled:
        provided = x_admin_key or bearer_token(authorization)
        if not check_shared_key(provided, settings.admin_api_key):
            raise HTTPException(status_code=401, detail="invalid admin key")
        return
    if settings.is_production:
        # Fail closed rather than expose every customer to the open internet.
        raise HTTPException(
            status_code=503, detail="admin API disabled: set ADMIN_API_KEY"
        )


async def current_account(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> Account:
    acc = await repo.get_account(user_id)
    if acc is None:
        raise HTTPException(status_code=404, detail="user not found")
    return acc
