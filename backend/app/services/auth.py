"""Signed session tokens and shared-secret checks.

There are still no passwords in the product — a profile is picked on the device —
so a "session" is an HMAC-signed, expiring statement of which user this client is.
It replaces trusting a raw `X-User-Id` header: tokens can only be minted through
the API against an existing profile, expire, and are revoked wholesale by rotating
`SESSION_SECRET`. This is the seam where a real login flow slots in later.

Token format: ``hg1.<b64url(user_id)>.<expiry-unix>.<hmac-sha256-hex>``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

TOKEN_PREFIX = "hg1"


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _b64encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _b64decode(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode()).decode()


def mint_session_token(user_id: str, secret: str, ttl_seconds: int) -> tuple[str, int]:
    """Return (token, expiry_unix) for the given user."""
    expiry = int(time.time()) + ttl_seconds
    payload = f"{_b64encode(user_id)}.{expiry}"
    return f"{TOKEN_PREFIX}.{payload}.{_sign(secret, payload)}", expiry


def verify_session_token(token: str, secret: str) -> str | None:
    """Return the user id for a valid, unexpired token; None otherwise."""
    try:
        prefix, encoded_uid, expiry_raw, signature = token.split(".")
    except ValueError:
        return None
    if prefix != TOKEN_PREFIX:
        return None
    payload = f"{encoded_uid}.{expiry_raw}"
    if not hmac.compare_digest(_sign(secret, payload), signature):
        return None
    try:
        if int(expiry_raw) < time.time():
            return None
        return _b64decode(encoded_uid)
    except (ValueError, UnicodeDecodeError):
        return None


def check_shared_key(provided: str | None, expected: str | None) -> bool:
    """Constant-time comparison; False whenever either side is missing."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)
