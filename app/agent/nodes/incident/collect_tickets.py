"""Node 1 of Graph B: collect_tickets. Load every ticket that is still 'new' (limit 100).

TOOLS  list_tickets (orders-server)
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import IncidentState            # agent/state.py: state shape

ALLOWED_TOOLS = ("list_tickets",)


def make_collect_tickets(tools: dict[str, Any]) -> Callable[[IncidentState], Awaitable[dict[str, Any]]]:
    """Build the collect_tickets node."""
    belt = restrict(tools, ALLOWED_TOOLS, "collect_tickets")

    async def collect_tickets(state: IncidentState) -> dict[str, Any]:
        return {"tickets": (await belt.call("list_tickets", status="new", limit=100))["items"]}

    return collect_tickets
