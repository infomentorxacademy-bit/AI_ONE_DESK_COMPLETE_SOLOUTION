"""api/routers/approvals.py : the human-in-the-loop part. See the waiting approval cards and answer them.

GET  /api/approvals               every paused run: {thread_id, ticket_id, card}
POST /api/approvals/{thread_id}   answer a card (approve / reject / edit_amount / cancel). The graph resumes on
                                  the SAME thread; it may finish, or pause again (e.g. finance is still needed).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException   # fastapi: routing, dependencies, errors

from agent.runtime import resume                         # agent/runtime.py: Command(resume=...) on the same thread
from api.deps import get_state                           # api/deps.py: shared state dependency
from api.routers.tickets import to_run_result            # api/routers/tickets.py: graph result -> API shape
from api.schemas import ApprovalAnswer, RunResult        # api/schemas.py: request/response shapes
from api.state import AppState                           # api/state.py: shared objects

router = APIRouter(tags=["approvals"])


@router.get("/approvals")
async def list_approvals(state: AppState = Depends(get_state)) -> dict:
    """Runs that are waiting for a human decision."""
    return {"items": [{"thread_id": tid, **info} for tid, info in state.pending.items()]}


@router.post("/approvals/{thread_id}", response_model=RunResult)
async def answer_approval(thread_id: str, answer: ApprovalAnswer,
                          state: AppState = Depends(get_state)) -> RunResult:
    """Send the human's decision into the paused graph."""
    state.require_llm()
    waiting = state.pending.get(thread_id)
    if waiting is None:
        raise HTTPException(status_code=404, detail="No approval is waiting for this thread (already answered?)")
    config = {"configurable": {"thread_id": thread_id}}
    result = await resume(state.ticket_graph, config, answer.model_dump(exclude_none=True))
    return to_run_result(waiting["ticket_id"], thread_id, result, state)
