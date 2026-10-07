"""api/routers/tickets.py : list, read, create and RUN tickets.

GET  /api/tickets?status=&limit=   the queue (oldest first)
GET  /api/tickets/{id}             one ticket + its audit trail (status history)
POST /api/tickets                  create a ticket (status "new")
POST /api/tickets/{id}/run         run Graph A on the ticket (needs an LLM). Either finishes, or PAUSES with an
                                   approval card; answer it with POST /api/approvals/{thread_id}
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query   # fastapi: routing, dependencies, query validation

from agent.runtime import interrupt_card, start_ticket   # agent/runtime.py: start Graph A, read an approval card
from api.deps import get_state, load_ticket              # api/deps.py: shared state + 404 helper
from api.schemas import CreateTicketRequest, RunResult   # api/schemas.py: request/response shapes
from api.state import AppState                           # api/state.py: shared objects

router = APIRouter(tags=["tickets"])


def to_run_result(ticket_id: str, thread_id: str, result: dict[str, Any], state: AppState) -> RunResult:
    """Convert a graph result into the API shape, and remember/forget the paused approval."""
    card = interrupt_card(result)
    if card is not None:
        state.pending[thread_id] = {"ticket_id": ticket_id, "card": card}
        return RunResult(ticket_id=ticket_id, thread_id=thread_id, state="paused", kind=result.get("kind"),
                         flags=card.get("flags", []), card=card)
    state.pending.pop(thread_id, None)
    return RunResult(ticket_id=ticket_id, thread_id=thread_id, state="finished", kind=result.get("kind"),
                     outcome=result.get("outcome"), final_status=result.get("final_status"),
                     reply=result.get("reply"), flags=result.get("flags", []))


@router.get("/tickets")
async def list_tickets(status: str | None = None, limit: int = Query(50, ge=1, le=100),
                       state: AppState = Depends(get_state)) -> dict:
    """The ticket queue, optionally filtered by status."""
    return await state.belt.call("list_tickets", status=status, limit=limit)


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, state: AppState = Depends(get_state)) -> dict:
    """One ticket plus the audit trail for it (newest first)."""
    ticket = await load_ticket(state, ticket_id)
    trail = await state.belt.call("get_audit_trail", ticket_id=ticket_id, limit=100)
    return {"ticket": ticket, "audit": trail["items"]}


@router.post("/tickets", status_code=201)
async def create_ticket(body: CreateTicketRequest, state: AppState = Depends(get_state)) -> dict:
    """Create a new ticket. 404 if the given customer id does not exist."""
    result = await state.belt.call("create_ticket", text=body.text, customer_id=body.customer_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.post("/tickets/{ticket_id}/run", response_model=RunResult)
async def run_ticket(ticket_id: str, customer_id: str | None = None,
                     state: AppState = Depends(get_state)) -> RunResult:
    """Run the agent on a ticket. `customer_id` is the optional clarification (e.g. after 'which Asha Rao?')."""
    state.require_llm()                                          # 409 if no LLM is chosen yet
    await load_ticket(state, ticket_id)                          # 404 if the ticket does not exist
    result, config = await start_ticket(state.ticket_graph, ticket_id, customer_id)
    return to_run_result(ticket_id, config["configurable"]["thread_id"], result, state)
