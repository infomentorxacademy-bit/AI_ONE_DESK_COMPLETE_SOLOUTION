"""Node 7 of Graph A: answer_policy. Answer a policy question ONLY from the policy text (FR-29).

TOOLS  search_policy (knowledge-server)
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import TicketState              # agent/state.py: state shape

ALLOWED_TOOLS = ("search_policy",)


def make_answer_policy(tools: dict[str, Any]) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the answer_policy node."""
    belt = restrict(tools, ALLOWED_TOOLS, "answer_policy")

    async def answer_policy(state: TicketState) -> dict[str, Any]:
        hits = (await belt.call("search_policy", keyword="30 days")).get("items", [])
        # No hit => draft_reply uses the policy team's required "I am not sure" wording.
        return {"policy_hit": hits[0] if hits else None, "outcome": "answered"}

    return answer_policy
