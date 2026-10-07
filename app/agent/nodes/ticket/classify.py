"""Node 1 of Graph A: classify. Read the ticket, label it, mark it in_progress.

TOOLS  get_ticket (orders-server), update_ticket_status (orders-server)
LLM    llm.classify() - ONE of the (at most) two LLM calls per ticket (NFR-16)
"""
from __future__ import annotations

import asyncio                                   # standard library: run the (maybe slow) LLM call off the event loop
from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: give this node only its allowed tools
from agent.state import TicketState              # agent/state.py: state shape

ALLOWED_TOOLS = ("get_ticket", "update_ticket_status")


def make_classify(tools: dict[str, Any], llm: Any) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the classify node. `tools` = all MCP tools; `llm` = an LLMClient (agent/llm/base.py)."""
    belt = restrict(tools, ALLOWED_TOOLS, "classify")

    async def classify(state: TicketState) -> dict[str, Any]:
        found = await belt.call("get_ticket", ticket_id=state["ticket_id"])           # orders-server tool
        if "error" in found:
            raise LookupError(found["message"])                                       # unknown ticket id: caller bug
        ticket = found["ticket"]
        verdict = await asyncio.to_thread(llm.classify, ticket)                       # label the ticket (kind + flags)
        # FR-27: every ticket we start working on becomes in_progress (an audit row is written by the server).
        await belt.call("update_ticket_status", ticket_id=ticket["id"], status="in_progress", actor="agent")
        return {"ticket": ticket, "kind": verdict["kind"], "flags": list(verdict.get("flags", [])),
                "incident_id": ticket.get("incident_id"), "approvals": []}

    return classify
