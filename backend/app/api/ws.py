"""Bidirectional WebSocket between the swarm and connected consoles.

Server → client: swarm events (with a replay on connect so a console that joins
mid-case isn't blank — pass `?since=<event_id>` to resume after a reconnect and
only receive what was missed), plus presence frames and heartbeat pongs.

Client → server: operator identity (`hello`), which case each console is viewing
(`presence`), heartbeats (`ping`), and operator overrides (`override`) — freeze
the transfer, escalate to the guardian, or hand the case to a human. Overrides
set flags the arbiter consults and are echoed onto the bus so every console sees
who did what.

Backpressure is handled by the bus subscription, which drops oldest-first rather
than stalling the swarm.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.domain.events import EventType, SwarmEvent
from app.integrations.event_bus import get_event_bus
from app.services.overrides import OVERRIDE_ACTIONS, get_override_registry

logger = logging.getLogger("hyperguard.ws")
router = APIRouter()

# Live console roster: websocket → {operator: {id, name}, viewing, connected_at, last_seen}
_consoles: dict[WebSocket, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _send(ws: WebSocket, frame: dict) -> None:
    with contextlib.suppress(Exception):
        await ws.send_json(frame)


async def _broadcast_presence() -> None:
    frame = {
        "type": "presence.updated",
        "payload": {
            "operators": [
                {**info["operator"], "viewing": info["viewing"], "since": info["connected_at"]}
                for info in _consoles.values()
            ]
        },
    }
    await asyncio.gather(*(_send(ws, frame) for ws in list(_consoles)))


async def _escalate_guardian(case_id: str, operator: dict) -> None:
    """Out-of-band guardian escalation at operator request: rebuild the case
    context from the bus replay and alert the top trusted contact immediately."""
    from app.graph import get_orchestrator  # lazy: avoid circular import at module load
    from app.schemas import TrustedContact

    bus = get_event_bus()
    rt = get_orchestrator().rt
    opened = next(
        (e for e in bus.replay(case_id) if e.type == EventType.case_opened), None
    )
    if opened is None:
        logger.warning("escalation requested for unknown case %s", case_id)
        return

    customer = opened.payload.get("customer") or {}
    txn = opened.payload.get("transaction") or {}
    contacts = sorted(
        (TrustedContact(**c) for c in customer.get("trusted_contacts", [])),
        key=lambda c: c.priority,
    )
    if not contacts:
        return

    target = contacts[0]
    message = (
        f"HyperGuard alert (operator {operator.get('name', 'console')} escalated): "
        f"{customer.get('name', 'your relative')} is attempting a "
        f"{txn.get('currency', '')} {txn.get('amount', 0):,.0f} transfer to "
        f"{txn.get('payee_name', 'an unverified payee')}. "
        f"Please reach them now to confirm this is genuinely intended."
    )
    alert = await rt.notify.send_sms(target, message)
    if not rt.notify.is_live:
        alert.acknowledged = True
        alert.status = "acknowledged"

    await bus.publish(
        SwarmEvent(
            type=EventType.guardian_alerted,
            case_id=case_id,
            agent="guardian",
            payload={"alert": alert.model_dump(mode="json"), "operator": operator},
        )
    )


async def _apply_override(case_id: str, action: str, operator: dict) -> None:
    registry = get_override_registry()
    flags = registry.for_case(case_id)
    name = operator.get("name")
    if action == "freeze_transfer":
        flags.frozen, flags.frozen_by = True, name
    elif action == "human_handoff":
        flags.handoff, flags.handoff_by = True, name
    elif action == "escalate_guardian":
        flags.escalated = True

    await get_event_bus().publish(
        SwarmEvent(
            type=EventType.operator_override,
            case_id=case_id,
            payload={"action": action, "operator": operator},
        )
    )
    if action == "escalate_guardian":
        await _escalate_guardian(case_id, operator)


async def _handle_client_frame(ws: WebSocket, raw: str) -> None:
    try:
        frame = json.loads(raw)
    except json.JSONDecodeError:
        return
    info = _consoles.get(ws)
    if info is None:
        return
    info["last_seen"] = _now()

    op = frame.get("op")
    if op == "hello":
        operator = frame.get("operator") or {}
        info["operator"] = {
            "id": str(operator.get("id", info["operator"]["id"]))[:64],
            "name": str(operator.get("name", info["operator"]["name"]))[:64],
        }
        info["viewing"] = frame.get("viewing")
        await _broadcast_presence()
    elif op == "presence":
        info["viewing"] = frame.get("viewing")
        await _broadcast_presence()
    elif op == "ping":
        await _send(ws, {"type": "pong", "at": _now()})
    elif op == "override":
        case_id = frame.get("case_id")
        action = frame.get("action")
        if not case_id or action not in OVERRIDE_ACTIONS:
            await _send(ws, {"type": "override.rejected", "payload": {"action": action}})
            return
        logger.info("operator override %s on %s by %s", action, case_id, info["operator"])
        await _apply_override(case_id, action, info["operator"])


async def _pump_events(ws: WebSocket, subscription) -> None:
    async for event in subscription.stream():
        await ws.send_json(event.envelope())


@router.websocket("/ws/events")
async def events(websocket: WebSocket) -> None:
    await websocket.accept()
    bus = get_event_bus()

    # Replay history so a late console catches the current case; a reconnecting
    # console passes the last event id it saw and only receives the gap.
    for event in bus.replay_since(websocket.query_params.get("since")):
        await websocket.send_json(event.envelope())

    n = len(_consoles) + 1
    _consoles[websocket] = {
        "operator": {"id": f"anon-{id(websocket):x}", "name": f"console-{n}"},
        "viewing": None,
        "connected_at": _now(),
        "last_seen": _now(),
    }
    await _broadcast_presence()

    with bus.subscribe() as subscription:
        pump = asyncio.create_task(_pump_events(websocket, subscription))
        try:
            while True:
                raw = await websocket.receive_text()
                await _handle_client_frame(websocket, raw)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("websocket session ended: %s", exc)
        finally:
            pump.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await pump
            _consoles.pop(websocket, None)
            await _broadcast_presence()
