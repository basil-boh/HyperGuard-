"""REST surface.

Deliberately thin: it validates input, delegates to the orchestrator, and returns
the structured outcome. All live narration happens out-of-band over the websocket,
so a console subscribes first and then triggers a run.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.data.seed_data import build_scenario, get_customer, list_scenarios
from app.graph import get_orchestrator
from app.schemas import InterventionOutcome

router = APIRouter(prefix="/api")


class RunRequest(BaseModel):
    scenario_id: str


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "capabilities": settings.capability_report(),
    }


@router.get("/scenarios")
async def scenarios() -> list[dict]:
    return list_scenarios()


@router.get("/customers/{customer_id}")
async def customer(customer_id: str) -> dict:
    profile = get_customer(customer_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return profile.model_dump(mode="json")


@router.post("/interventions/run", response_model=InterventionOutcome)
async def run_intervention(req: RunRequest) -> InterventionOutcome:
    try:
        customer_profile, txn = build_scenario(req.scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown scenario")
    return await get_orchestrator().run(customer_profile, txn)
