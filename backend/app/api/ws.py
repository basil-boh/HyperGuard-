"""WebSocket fan-out of swarm events to connected consoles.

On connect a client immediately receives a short replay of recent events (so a
console that joins mid-case isn't blank), then a live tail. Backpressure is handled
by the bus subscription, which drops oldest-first rather than stalling the swarm.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.integrations.event_bus import get_event_bus

logger = logging.getLogger("hyperguard.ws")
router = APIRouter()


@router.websocket("/ws/events")
async def events(websocket: WebSocket) -> None:
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
