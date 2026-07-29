"""Operator authentication for the control centre.

A single shared `ADMIN_PASSWORD` gates the bank-side surface: the admin API, the
event websocket, and the scenario launcher. Login exchanges the password for a
short-lived HS256 JWT (signed with stdlib hmac — no extra dependency), which the
console sends as a `Bearer` header on REST calls and as the first websocket frame
(browsers cannot set headers on cross-host websocket upgrades).

When `ADMIN_PASSWORD` is unset every guard is a no-op, preserving the zero-config
demo posture. Swapping this for NextAuth/Clerk later only replaces `login` and
`verify_admin_token`; the `require_admin` guard and the WS handshake stay put.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(prefix="/api/admin")


# ── Token signing (compact HS256 JWT) ──────────────────────────────────────────
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _secret(settings: Settings) -> bytes:
    if settings.admin_token_secret:
        return settings.admin_token_secret.encode()
    return hashlib.sha256(f"hyperguard-operator:{settings.admin_password}".encode()).digest()


def create_admin_token(settings: Settings) -> tuple[str, int]:
    now = int(time.time())
    ttl = settings.admin_token_ttl_seconds
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(
        json.dumps(
            {"sub": "operator", "iat": now, "exp": now + ttl}, separators=(",", ":")
        ).encode()
    )
    signature = _b64url(
        hmac.new(_secret(settings), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{signature}", ttl


def verify_admin_token(token: str, settings: Settings) -> bool:
    try:
        header, payload, signature = token.split(".")
        expected = hmac.new(
            _secret(settings), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url_decode(signature), expected):
            return False
        claims = json.loads(_b64url_decode(payload))
        return float(claims.get("exp", 0)) > time.time()
    except Exception:
        return False


# ── Login ──────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(req: LoginRequest, settings: Settings = Depends(get_settings)) -> dict:
    if not settings.admin_auth_enabled:
        raise HTTPException(
            status_code=503, detail="operator auth is not configured (set ADMIN_PASSWORD)"
        )
    if not hmac.compare_digest(req.password.encode(), settings.admin_password.encode()):
        raise HTTPException(status_code=401, detail="invalid password")
    token, ttl = create_admin_token(settings)
    return {"token": token, "token_type": "bearer", "expires_in": ttl}


# ── Guard ──────────────────────────────────────────────────────────────────────
async def require_admin(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.admin_auth_enabled:
        return
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token or not verify_admin_token(token, settings):
        raise HTTPException(
            status_code=401,
            detail="operator token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
