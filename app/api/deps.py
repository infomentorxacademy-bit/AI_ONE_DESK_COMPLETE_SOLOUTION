"""api/deps.py : FastAPI "dependencies" - small helpers the routers declare as parameters.

USED BY api/routers/*.py   Example:  def handler(state: AppState = Depends(get_state))
"""
from __future__ import annotations

from fastapi import HTTPException, Request   # fastapi: access the app and raise HTTP errors

from api.state import AppState               # api/state.py: the shared objects


def get_state(request: Request) -> AppState:
    """The shared AppState created at startup."""
    return request.app.state.ops


async def load_ticket(state: AppState, ticket_id: str) -> dict:
    """Fetch a ticket through the MCP tool, or raise HTTP 404 if it does not exist."""
    result = await state.belt.call("get_ticket", ticket_id=ticket_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["message"])
    return result["ticket"]
