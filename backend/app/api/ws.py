"""WebSocket fan-out of swarm events to connected consoles.

On connect a client immediately receives a short replay of recent events (so a
console that joins mid-case isn't blank), then a live tail. Backpressure is handled
by the bus subscription, which drops oldest-first rather than stalling the swarm.

The stream carries every customer's case activity, so it is guarded like the admin
surface: connect with `?token=<ADMIN_API_KEY>` (the console) or a signed user
session token. With neither secret configured it only stays open in development.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.config import Settings, get_settings
from app.integrations.event_bus import get_event_bus
from app.services.auth import check_shared_key, verify_session_token

logger = logging.getLogger("hyperguard.ws")
router = APIRouter()


def _authorized(token: str | None, settings: Settings) -> bool:
    if settings.admin_auth_enabled and check_shared_key(token, settings.admin_api_key):
        return True
    if (
        settings.user_auth_enabled
        and token
        and verify_session_token(token, settings.session_secret) is not None
    ):
        return True
    if settings.admin_auth_enabled or settings.user_auth_enabled:
        return False
    return not settings.is_production


@router.websocket("/ws/events")
async def events(
    websocket: WebSocket, settings: Settings = Depends(get_settings)
) -> None:
    if not _authorized(websocket.query_params.get("token"), settings):
        # Denied before accept — the handshake is refused with a 403.
        await websocket.close(code=4401)
        return
    await websocket.accept()
    bus = get_event_bus()

    # Replay recent history so a late console catches the current case.
    for event in bus.replay():
        await websocket.send_json(event.envelope())

    with bus.subscribe() as subscription:
        try:
            async for event in subscription.stream():
                await websocket.send_json(event.envelope())
        except (WebSocketDisconnect, asyncio.CancelledError):
            return
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("websocket stream ended: %s", exc)
            return
