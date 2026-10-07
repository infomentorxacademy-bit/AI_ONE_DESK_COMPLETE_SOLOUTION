"""Node 6 of Graph A: issue_refund. Ask the orders-server to pay. The SERVER re-checks every rule again.

TOOLS  issue_refund (orders-server)
KEY    idempotency_key = "refund-<ticket>-<order>": running the same ticket twice never pays twice (S20, R10).
ERROR  A tool error (a rule said no) becomes outcome refund_declined with a customer-safe reason.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.reply_facts import DECLINE_REASONS    # agent/reply_facts.py: customer-safe decline reasons
from agent.state import TicketState              # agent/state.py: state shape

ALLOWED_TOOLS = ("issue_refund",)


def make_issue_refund(tools: dict[str, Any]) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the issue_refund node."""
    belt = restrict(tools, ALLOWED_TOOLS, "issue_refund")

    async def issue_refund(state: TicketState) -> dict[str, Any]:
        order = state["order"]
        result = await belt.call(
            "issue_refund", ticket_id=state["ticket_id"], order_id=order["id"], amount=state["amount"],
            reason=f"Customer refund request for {order['item']}",
            idempotency_key=f"refund-{state['ticket_id']}-{order['id']}", approvals=state.get("approvals", []))
        if "error" in result:
            return {"outcome": "refund_declined", "decline_reason": DECLINE_REASONS["BLOCKED"]}
        return {"refund": result["refund"], "outcome": "refund_issued"}

    return issue_refund
