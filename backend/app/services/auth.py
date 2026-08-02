"""Credentials and sessions for the customer banking app.

A customer signs in with the pair they'd use at an ATM: their phone number and a
6-digit PIN. Everything here is stdlib, deliberately:

- **PIN at rest** — PBKDF2-HMAC-SHA256 with a per-PIN salt, compared in constant
  time. Never store or log the PIN itself.
- **Session** — a stateless HMAC-signed token (`payload.signature`). Stateless
  matters because the API runs with two interchangeable persistence backends and
  possibly several workers; there is no session table to keep in sync, and a
  restart doesn't sign everyone out as long as `AUTH_SECRET` is stable.

Nothing here is a substitute for a real IdP. It is a demo bank's front door: strong
enough that a PIN is never recoverable from the database, simple enough to read.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
import time
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger("hyperguard.auth")

PIN_LENGTH = 6
_PBKDF2_ITERATIONS = 120_000
_ALGO = "pbkdf2_sha256"


# ── Phone normalisation ────────────────────────────────────────────────────────
def normalize_phone(raw: str | None, default_country_code: str = "65") -> str:
    """Fold the many ways a phone is typed into the one stored form (E.164).

    "+65 8000 0001", "6580000001" and "80000001" all resolve to "+6580000001", so
    the sign-in field is forgiving without the lookup key ever being ambiguous.
    """
    if not raw:
        return ""
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    if not cleaned:
        return ""
    if cleaned.startswith("+"):
        return "+" + re.sub(r"\D", "", cleaned[1:])
    digits = re.sub(r"\D", "", cleaned)
    # A bare local number (8 digits in SG) gets the home calling code; anything
    # longer is assumed to already carry one.
    if len(digits) <= 8:
        return f"+{default_country_code}{digits}"
    return f"+{digits}"


# ── PIN hashing ────────────────────────────────────────────────────────────────
def is_valid_pin(pin: str | None) -> bool:
    return bool(pin) and bool(re.fullmatch(rf"\d{{{PIN_LENGTH}}}", pin or ""))


def hash_pin(pin: str, *, salt: bytes | None = None) -> str:
    """Encode as `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`."""
    salt = salt or uuid4().bytes
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_pin(pin: str | None, encoded: str | None) -> bool:
    """Constant-time check of a candidate PIN against a stored hash."""
    if not pin or not encoded:
        return False
    try:
        algo, iterations, salt_hex, digest_hex = encoded.split("$")
        if algo != _ALGO:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", pin.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate.hex(), digest_hex)


# ── Session tokens ─────────────────────────────────────────────────────────────
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def issue_token(user_id: str, *, secret: str, ttl_seconds: int) -> str:
    """Mint `base64(user_id:issued:expires).base64(hmac)`."""
    now = int(time.time())
    payload = f"{user_id}:{now}:{now + ttl_seconds}".encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(signature)}"


def verify_token(token: str | None, *, secret: str) -> str | None:
    """Return the user id a token vouches for, or None if forged or expired."""
    if not token or "." not in token:
        return None
    encoded_payload, _, encoded_signature = token.partition(".")
    try:
        payload = _unb64(encoded_payload)
        signature = _unb64(encoded_signature)
    except (ValueError, TypeError):
        return None
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        user_id, _issued, expires = payload.decode().rsplit(":", 2)
    except ValueError:
        return None
    if not expires.isdigit() or int(expires) < int(time.time()):
        return None
    return user_id or None


def token_expiry(token: str) -> int | None:
    """The token's expiry as a unix timestamp — for the client's clock, not a check."""
    try:
        _user_id, _issued, expires = _unb64(token.partition(".")[0]).decode().rsplit(":", 2)
        return int(expires)
    except (ValueError, TypeError):
        return None


# ── Brute-force throttle ───────────────────────────────────────────────────────
@dataclass
class _Attempts:
    count: int = 0
    locked_until: float = 0.0


@dataclass
class LoginThrottle:
    """In-process lockout after repeated failures against the same phone number.

    Per-worker rather than shared — enough to make a 6-digit PIN impractical to
    guess through the API, without adding a Redis round-trip to the login path.
    """

    max_attempts: int = 5
    lock_seconds: float = 60.0
    _by_key: dict[str, _Attempts] = field(default_factory=dict)

    def retry_after(self, key: str) -> int:
        """Seconds until `key` may try again; 0 when it is free to proceed."""
        record = self._by_key.get(key)
        if record is None:
            return 0
        remaining = record.locked_until - time.monotonic()
        return int(remaining) + 1 if remaining > 0 else 0

    def record_failure(self, key: str) -> None:
        record = self._by_key.setdefault(key, _Attempts())
        record.count += 1
        if record.count >= self.max_attempts:
            record.locked_until = time.monotonic() + self.lock_seconds
            record.count = 0
            logger.warning("login locked for %s (%.0fs)", key, self.lock_seconds)

    def record_success(self, key: str) -> None:
        self._by_key.pop(key, None)


_throttle = LoginThrottle()


def get_throttle() -> LoginThrottle:
    return _throttle
