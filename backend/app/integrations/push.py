"""Expo push notifications.

The mobile app registers its Expo push token (`POST /api/users/push-token`); this
module keeps a per-user token set in memory and delivers notifications through
Expo's push API. A `PushDispatcher` subscribes to the swarm bus (same pattern as
the intervention registry) and turns key events into pushes:

- ``case.opened``     → victim: "transfer paused, expect a call"
- ``guardian.alerted``→ any registered user whose phone matches the alerted
                        next-of-kin: tap-through to the guardian live view
- ``decision.made``   → victim: the verdict

Everything is best-effort by design — a missing token or a failed HTTP call must
never stall the swarm.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re

import httpx

from app.domain.events import EventType, SwarmEvent
from app.integrations.event_bus import get_event_bus

logger = logging.getLogger("hyperguard.push")

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# user_id -> Expo push tokens (a user may run several devices)
_tokens: dict[str, set[str]] = {}


def register_token(user_id: str, token: str) -> int:
    """Bind a device token to a user. A device that switches profiles must stop
    receiving the previous profile's alerts, so the token is moved, not copied."""
    for owned in _tokens.values():
        owned.discard(token)
    _tokens.setdefault(user_id, set()).add(token)
    count = len(_tokens[user_id])
    logger.info("push token registered for %s (%d device(s))", user_id, count)
    return count


def _drop_token(token: str) -> None:
    for owned in _tokens.values():
        owned.discard(token)


async def send_push(user_id: str, title: str, body: str, data: dict | None = None) -> None:
    tokens = list(_tokens.get(user_id, ()))
    if not tokens:
        return
    messages = [
        {
            "to": t,
            "title": title,
            "body": body,
            "sound": "default",
            "priority": "high",
            "data": data or {},
        }
        for t in tokens
    ]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(_EXPO_PUSH_URL, json=messages)
            res.raise_for_status()
            tickets = (res.json() or {}).get("data", [])
            for token, ticket in zip(tokens, tickets):
                details = ticket.get("details") or {}
                if details.get("error") == "DeviceNotRegistered":
                    _drop_token(token)
    except Exception as exc:
        logger.warning("push to %s failed: %s", user_id, exc)


def send_push_bg(user_id: str, title: str, body: str, data: dict | None = None) -> None:
    """Fire-and-forget wrapper for call sites inside request handlers."""
    asyncio.create_task(send_push(user_id, title, body, data))


# ── Event-driven dispatch ───────────────────────────────────────────────────────
def phone_key(phone: str | None) -> str | None:
    """Comparable form of a phone number: digits only, last 8 (drops country code
    formatting differences like +65 8000 0010 vs 80000010)."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits[-8:] if len(digits) >= 8 else digits or None


class PushDispatcher:
    """Bus consumer that converts swarm events into push notifications."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        # case_id -> context captured from case.opened
        self._cases: dict[str, dict] = {}

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _consume(self) -> None:
        bus = get_event_bus()
        with bus.subscribe() as sub:
            try:
                async for event in sub.stream():
                    try:
                        await self._handle(event)
                    except Exception as exc:  # never let one bad event kill the tail
                        logger.warning("push dispatch for %s failed: %s", event.type, exc)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("push dispatcher ended: %s", exc)

    async def _handle(self, event: SwarmEvent) -> None:
        p = event.payload or {}
        if event.type == EventType.case_opened:
            customer = p.get("customer") or {}
            txn = p.get("transaction") or {}
            ctx = {
                "user_id": customer.get("id"),
                "name": customer.get("name"),
                "amount": txn.get("amount"),
                "currency": txn.get("currency", "SGD"),
                "payee": txn.get("payee_name"),
            }
            self._cases[event.case_id] = ctx
            if len(self._cases) > 200:  # bound memory
                self._cases.pop(next(iter(self._cases)))
            if ctx["user_id"]:
                await send_push(
                    ctx["user_id"],
                    "Transfer paused",
                    f"HyperGuard paused your {ctx['currency']} {ctx['amount']:,.0f} "
                    f"transfer to {ctx['payee']} for a safety check. Expect a call.",
                    {"caseId": event.case_id, "role": "victim"},
                )

        elif event.type == EventType.guardian_alerted:
            ctx = self._cases.get(event.case_id) or {}
            alert = p.get("alert") or {}
            contact = alert.get("contact") or {}
            guardian_id = await self._user_by_phone(contact.get("phone"))
            if guardian_id:
                ward = ctx.get("name") or "a family member"
                await send_push(
                    guardian_id,
                    f"{ward} may be getting scammed",
                    alert.get("message")
                    or f"HyperGuard flagged a suspicious transfer by {ward}. Tap to watch live and step in.",
                    {"caseId": event.case_id, "role": "guardian", "ward": ward},
                )

        elif event.type == EventType.decision_made:
            ctx = self._cases.get(event.case_id) or {}
            if not ctx.get("user_id"):
                return
            decision = p.get("decision")
            titles = {
                "block": "Transfer blocked",
                "hold": "Transfer held for review",
                "approve": "Transfer approved",
            }
            bodies = {
                "block": "This looked like a scam. Your money stayed in your account.",
                "hold": "We've held the transfer pending your confirmation.",
                "approve": "The transfer checked out and was sent securely.",
            }
            await send_push(
                ctx["user_id"],
                titles.get(decision, "Review complete"),
                bodies.get(decision, "Open the app to see the outcome."),
                {"caseId": event.case_id, "role": "victim"},
            )

    async def _user_by_phone(self, phone: str | None) -> str | None:
        """Resolve a next-of-kin phone number to a registered app user, so guardian
        pushes land on the guardian's own device."""
        key = phone_key(phone)
        if key is None:
            return None
        from app.wallet.repository import get_repository

        try:
            profiles = await get_repository().list_profiles()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("guardian phone lookup failed: %s", exc)
            return None
        for row in profiles:
            if phone_key(row.get("phone")) == key:
                return row.get("id")
        return None


_dispatcher: PushDispatcher | None = None


def get_push_dispatcher() -> PushDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = PushDispatcher()
    return _dispatcher
