"""Node 11 of Graph A: finish. ALWAYS write the final ticket status so it can be re-checked later (FR-41, BO-6).

TOOLS  update_ticket_status (orders-server)
MAP    outcome -> status comes from agent/state.py OUTCOME_TO_STATUS; resolution = the reply text.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import OUTCOME_TO_STATUS, TicketState   # agent/state.py: outcome vocabulary + state shape

ALLOWED_TOOLS = ("update_ticket_status",)

# Used as the stored resolution when no customer reply exists for the outcome.
_FALLBACK = {
    "pending_approval": "Refund awaiting human approval; no decision recorded. Nothing has been paid.",
    "needs_incident_flow": "Payment-failure ticket handed to the incident flow (Graph B).",
}


def make_finish(tools: dict[str, Any]) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the finish node."""
    belt = restrict(tools, ALLOWED_TOOLS, "finish")

    async def finish(state: TicketState) -> dict[str, Any]:
        outcome = state["outcome"]
        status = OUTCOME_TO_STATUS[outcome]
        resolution = state.get("reply") or _FALLBACK.get(outcome, outcome)
        await belt.call("update_ticket_status", ticket_id=state["ticket_id"], status=status,
                        resolution=resolution, actor="agent")
        return {"final_status": status}

    return finish
