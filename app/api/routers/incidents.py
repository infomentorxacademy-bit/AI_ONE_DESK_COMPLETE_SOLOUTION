"""api/routers/incidents.py : the outage detector (Graph B) and incident/rollback views.

POST /api/incident/run   run Graph B over the queue (needs an LLM): cluster, correlate, link, PROPOSE a rollback
GET  /api/incidents      incidents with ticket counts          GET /api/incidents/{id}  one incident + ticket ids
GET  /api/rollbacks      rollback proposals (always awaiting human approval; nothing is ever executed)
"""
from __future__ import annotations

import uuid                                      # standard library: unique thread id for the run

from fastapi import APIRouter, Depends, HTTPException   # fastapi: routing, dependencies, errors

from agent.runtime import run_incident           # agent/runtime.py: run Graph B once
from api.deps import get_state                   # api/deps.py: shared state dependency
from api.state import AppState                   # api/state.py: shared objects

router = APIRouter(tags=["incidents"])

# The fields of Graph B's result that the UI shows.
_RESULT_KEYS = ("cluster_ids", "spike", "correlated", "incident_id", "flags", "proposal",
                "engineer_note", "customer_message")


@router.post("/incident/run")
async def run_incident_detection(state: AppState = Depends(get_state)) -> dict:
    """Run the outage detector. Returns {"cluster_ids": []} when there is no outage."""
    state.require_llm()
    result = await run_incident(state.incident_graph)
    return {key: result.get(key) for key in _RESULT_KEYS if key in result} or {"cluster_ids": []}


@router.get("/incidents")
async def list_incidents(status: str | None = None, state: AppState = Depends(get_state)) -> dict:
    """All incidents (optionally by status) with ticket_count."""
    return await state.belt.call("list_incidents", status=status)


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, state: AppState = Depends(get_state)) -> dict:
    """One incident including the ids of its linked tickets."""
    result = await state.belt.call("get_incident", incident_id=incident_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("/rollbacks")
async def list_rollbacks(state: AppState = Depends(get_state)) -> dict:
    """Rollback PROPOSALS (never executed)."""
    return await state.belt.call("list_rollback_proposals")
