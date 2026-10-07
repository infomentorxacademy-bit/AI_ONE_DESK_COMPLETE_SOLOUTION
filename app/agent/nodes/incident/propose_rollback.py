"""Node 5 of Graph B: propose_rollback. Only PROPOSE; a human decides (FR-45, ground rule G8).

TOOLS  propose_rollback (ops-server) - records a proposal with status 'awaiting_approval'; executes nothing.
EVIDENCE  must contain the error-rate numbers, the spike time, and the deployment id and time.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import IncidentState            # agent/state.py: state shape

ALLOWED_TOOLS = ("propose_rollback",)


def make_propose_rollback(tools: dict[str, Any]) -> Callable[[IncidentState], Awaitable[dict[str, Any]]]:
    """Build the propose_rollback node."""
    belt = restrict(tools, ALLOWED_TOOLS, "propose_rollback")

    async def propose_rollback(state: IncidentState) -> dict[str, Any]:
        deployment, spike = state.get("correlated"), state["spike"]
        if not deployment:                                # no suspect deployment => nothing to propose
            return {"proposal": None}
        evidence = (f"{state['service']} error rate rose from {spike['baseline']}% to {spike['value']}% at "
                    f"{spike['first_time']}; deployment {deployment['id']} ({deployment['version']}) went live at "
                    f"{deployment['at'][-5:]}, {deployment['minutes_before_spike']} minutes earlier.")
        result = await belt.call("propose_rollback", deployment_id=deployment["id"], evidence=evidence)
        return {"proposal": result.get("proposal")}

    return propose_rollback
