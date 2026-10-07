"""Node 4 of Graph B: link_tickets. Attach every clustered ticket to the open incident (FR-44). Harmless to repeat.

TOOLS  link_tickets_to_incident (ops-server) - idempotent on the server side
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import IncidentState            # agent/state.py: state shape

ALLOWED_TOOLS = ("link_tickets_to_incident",)


def make_link_tickets(tools: dict[str, Any]) -> Callable[[IncidentState], Awaitable[dict[str, Any]]]:
    """Build the link_tickets node."""
    belt = restrict(tools, ALLOWED_TOOLS, "link_tickets")

    async def link_tickets(state: IncidentState) -> dict[str, Any]:
        if not state.get("incident_id"):                 # no open incident for this service: nothing to link to
            return {"link_result": {"linked": [], "already_linked": []}}
        result = await belt.call("link_tickets_to_incident", incident_id=state["incident_id"],
                                 ticket_ids=state["cluster_ids"])
        return {"link_result": result}

    return link_tickets
