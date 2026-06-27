"""Event transport for the swarm.

The console is fed by an in-process fan-out so it works with zero infrastructure.
When `REDIS_URL` is configured every event is additionally mirrored to a Redis
Stream, that buys durability and cross-restart replay, and is the seam where a
multi-worker deployment would consume events. Local websocket fan-out stays
in-process either way, which is exactly what a single backend needs.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import deque
from collections.abc import AsyncIterator

from app.domain.events import SwarmEvent

logger = logging.getLogger("hyperguard.bus")

_REPLAY_DEPTH = 256
_STREAM_KEY = "hyperguard:events"


class Subscription:
    """A bounded queue that drops the oldest event under backpressure rather than
    stalling the publisher, a slow console must never block the swarm."""

    def __init__(self, maxsize: int = 512) -> None:
        self._queue: asyncio.Queue[SwarmEvent] = asyncio.Queue(maxsize=maxsize)

    def offer(self, event: SwarmEvent) -> None:
        if self._queue.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                self._queue.get_nowait()
        self._queue.put_nowait(event)

    async def stream(self) -> AsyncIterator[SwarmEvent]:
        while True:
            yield await self._queue.get()


class EventBus:
    def __init__(self, redis_url: str | None = None) -> None:
        self._subscribers: set[Subscription] = set()
        self._replay: deque[SwarmEvent] = deque(maxlen=_REPLAY_DEPTH)
        self._redis_url = redis_url
        self._redis = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if not self._redis_url:
            return
        try:
            import redis.asyncio as redis  # imported lazily so the dep is optional

            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("Event bus mirroring to Redis stream %s", _STREAM_KEY)
        except Exception as exc:  # pragma: no cover - infra optional
            logger.warning("Redis unavailable (%s); using in-process bus only", exc)
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.aclose()

    async def publish(self, event: SwarmEvent) -> None:
        self._replay.append(event)
        for sub in tuple(self._subscribers):
            sub.offer(event)
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.xadd(
                    _STREAM_KEY,
                    {"data": event.model_dump_json()},
                    maxlen=10_000,
                    approximate=True,
                )

    def replay(self, case_id: str | None = None) -> list[SwarmEvent]:
        if case_id is None:
            return list(self._replay)
        return [e for e in self._replay if e.case_id == case_id]

    @contextlib.contextmanager
    def subscribe(self):
        sub = Subscription()
        self._subscribers.add(sub)
        try:
            yield sub
        finally:
            self._subscribers.discard(sub)


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        from app.config import get_settings

        _bus = EventBus(get_settings().redis_url)
    return _bus
