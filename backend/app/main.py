"""FastAPI application entrypoint.

Wires the event bus lifecycle, CORS, structured logging, and the REST + WebSocket
routers. Run with: `uvicorn app.main:app --reload`.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, routes, twilio_voice, users, wallet, ws
from app.config import get_settings
from app.integrations.event_bus import get_event_bus
from app.wallet.registry import get_registry
from app.wallet.repository import get_repository
from app.wallet.seed_supabase import ensure_seeded

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("hyperguard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    bus = get_event_bus()
    await bus.connect()
    registry = get_registry()
    await registry.start()
    if settings.persistence_enabled:
        await ensure_seeded(get_repository())
    logger.info(
        "HyperGuard online, capabilities: %s",
        ", ".join(f"{k}={v}" for k, v in settings.capability_report().items()),
    )
    yield
    await registry.stop()
    await bus.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HyperGuard, Fraud Intervention Swarm",
        version="1.0.0",
        description="A multi-agent swarm that intervenes in social-engineering fraud in real time.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes.router)
    app.include_router(wallet.router)
    app.include_router(users.router)
    app.include_router(admin.router)
    app.include_router(ws.router)
    app.include_router(twilio_voice.router)

    @app.get("/")
    async def root() -> dict:
        return {"service": settings.app_name, "docs": "/docs", "events": "/ws/events"}

    return app


app = create_app()
