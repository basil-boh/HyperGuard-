"""Sign-in for the customer banking app.

Phone number + 6-digit PIN in, a bearer token out. The token is stateless and
HMAC-signed (`services/auth`), so it works the same whether the wallet is backed by
Supabase or the in-memory bank, and survives a restart.

Failed attempts are throttled per phone number. Errors are deliberately uniform —
"Incorrect phone number or PIN" whether the account is unknown or the PIN is wrong —
so the endpoint can't be used to enumerate customers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import current_user_id, repository
from app.config import Settings, get_settings
from app.services.auth import (
    PIN_LENGTH,
    get_throttle,
    hash_pin,
    is_valid_pin,
    issue_token,
    normalize_phone,
    token_expiry,
    verify_pin,
)
from app.wallet.repository import CredentialStoreUnavailable, WalletRepository
from app.wallet.seed_profiles import demo_credentials

logger = logging.getLogger("hyperguard.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

_BAD_CREDENTIALS = "Incorrect phone number or PIN"
# A well-formed hash of a PIN nobody is issued, verified against when the phone
# number is unknown so a miss costs the same wall-clock as a wrong PIN.
_DUMMY_HASH = hash_pin("000000")


# ── Payloads ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    phone: str = Field(min_length=3)
    pin: str = Field(min_length=PIN_LENGTH, max_length=PIN_LENGTH)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    phone: str = Field(min_length=3)
    pin: str = Field(min_length=PIN_LENGTH, max_length=PIN_LENGTH)
    age: int | None = None
    vulnerability_flags: list[str] = Field(default_factory=list)
    home_country: str = "SG"
    initial_balance: float = Field(default=1000.0, ge=0)


class ChangePinRequest(BaseModel):
    current_pin: str = Field(min_length=PIN_LENGTH, max_length=PIN_LENGTH)
    new_pin: str = Field(min_length=PIN_LENGTH, max_length=PIN_LENGTH)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _session(user_id: str, name: str, settings: Settings) -> dict:
    token = issue_token(
        user_id,
        secret=settings.auth_signing_key,
        ttl_seconds=settings.auth_token_ttl_hours * 3600,
    )
    return {
        "token": token,
        "expires_at": token_expiry(token),
        "user": {"id": user_id, "name": name},
    }


# ── Routes ─────────────────────────────────────────────────────────────────────
@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    repo: WalletRepository = Depends(repository),
    settings: Settings = Depends(get_settings),
) -> dict:
    phone = normalize_phone(body.phone)
    throttle = get_throttle()

    retry_after = throttle.retry_after(phone)
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        credentials = await repo.get_credentials(phone)
    except CredentialStoreUnavailable as exc:
        logger.error("%s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Verify unconditionally against a dummy hash when the account is unknown, so a
    # miss costs the same wall-clock as a wrong PIN and can't be timed apart.
    stored = (credentials or {}).get("pin_hash")
    if not verify_pin(body.pin, stored or _DUMMY_HASH) or not credentials or not stored:
        throttle.record_failure(phone)
        logger.info("login failed for %s (from %s)", phone, request.client.host if request.client else "?")
        raise HTTPException(status_code=401, detail=_BAD_CREDENTIALS)

    throttle.record_success(phone)
    logger.info("login ok: %s (%s)", credentials["name"], credentials["id"])
    return _session(credentials["id"], credentials["name"], settings)


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    repo: WalletRepository = Depends(repository),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not is_valid_pin(body.pin):
        raise HTTPException(status_code=422, detail=f"PIN must be {PIN_LENGTH} digits")
    phone = normalize_phone(body.phone)
    if len(phone) < 8:
        raise HTTPException(status_code=422, detail="Enter a valid phone number")
    if await repo.get_credentials(phone) is not None:
        raise HTTPException(status_code=409, detail="That phone number already has an account")

    profile = await repo.create_profile(
        name=body.name.strip(),
        phone=phone,
        age=body.age,
        vulnerability_flags=body.vulnerability_flags,
        home_country=body.home_country,
        initial_balance=body.initial_balance,
        pin_hash=hash_pin(body.pin),
    )
    return {**_session(profile["id"], profile["name"], settings), "profile": profile}


@router.get("/me")
async def me(
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    account = await repo.get_account(user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "id": account.owner.id,
        "name": account.owner.name,
        "phone": account.owner.phone,
        "account_number": account.account_number,
        "balance": round(account.balance, 2),
        "currency": account.currency,
        "age": account.owner.age,
        "vulnerability_flags": account.owner.vulnerability_flags,
    }


@router.post("/pin")
async def change_pin(
    body: ChangePinRequest,
    user_id: str = Depends(current_user_id),
    repo: WalletRepository = Depends(repository),
) -> dict:
    if not is_valid_pin(body.new_pin):
        raise HTTPException(status_code=422, detail=f"PIN must be {PIN_LENGTH} digits")
    account = await repo.get_account(user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="user not found")
    if not verify_pin(body.current_pin, account.pin_hash):
        raise HTTPException(status_code=401, detail="Current PIN is incorrect")
    await repo.set_pin(user_id, hash_pin(body.new_pin))
    return {"updated": True}


@router.post("/logout")
async def logout() -> dict:
    """Tokens are stateless, so signing out is a client-side discard.

    The endpoint exists so the app has one thing to call, and so a future
    revocation list has somewhere to live.
    """
    return {"signed_out": True}


@router.get("/demo-accounts")
async def demo_accounts(settings: Settings = Depends(get_settings)) -> list[dict]:
    """The seeded phone/PIN pairs, for the sign-in screen's test-account picker.

    Gated by `EXPOSE_DEMO_CREDENTIALS` — turn it off and this 404s.
    """
    if not settings.expose_demo_credentials:
        raise HTTPException(status_code=404, detail="not found")
    return demo_credentials()
