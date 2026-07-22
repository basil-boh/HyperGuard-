"""WebSocket fan-out of swarm events to connected consoles.

When operator auth is configured the client must authenticate with its first frame
(`{"token": "<jwt>"}` within a few seconds, else the socket closes with 4401) —
browsers cannot set headers on a cross-host websocket upgrade, so header auth is
not an option here. The socket is send-only after that handshake; any operator
command rides the (guarded) REST API, never the socket.

On connect a client immediately receives a short replay of recent events (so a
console that joins mid-case isn't blank), then a live tail. Backpressure is handled
by the bus subscription, which drops oldest-first rather than stalling the swarm.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.auth import verify_admin_token
from app.config import get_settings
from app.integrations.event_bus import get_event_bus

logger = logging.getLogger("hyperguard.ws")
router = APIRouter()

AUTH_DEADLINE_SECONDS = 5.0
POLICY_VIOLATION = 4401  # app-level "unauthorized", mirrors HTTP 401


async def _authenticate(websocket: WebSocket) -> bool:
    """First-message auth: expect `{"token": ...}` before the deadline."""
    try:
        first = await asyncio.wait_for(websocket.receive_json(), timeout=AUTH_DEADLINE_SECONDS)
    except WebSocketDisconnect:
        return False
    except Exception:  # timeout, non-JSON frame, binary frame
        await websocket.close(code=POLICY_VIOLATION, reason="operator token required")
        return False
    token = first.get("token") if isinstance(first, dict) else None
    if not token or not verify_admin_token(token, get_settings()):
        await websocket.close(code=POLICY_VIOLATION, reason="invalid operator token")
        return False
    await websocket.send_json({"type": "auth.ok"})
    return True


@router.websocket("/ws/events")
async def events(websocket: WebSocket) -> None:
    await websocket.accept()
    if get_settings().admin_auth_enabled and not await _authenticate(websocket):
        return
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
