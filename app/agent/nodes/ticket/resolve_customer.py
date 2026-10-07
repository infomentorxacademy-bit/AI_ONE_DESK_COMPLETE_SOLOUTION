"""Node 2 of Graph A: resolve_customer. Work out WHO the customer is. Never guess.

TOOLS  get_customer, find_customer (orders-server)
RULE   1 match => use it. 0 or 2+ matches => outcome needs_clarification (FR-38).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import TicketState              # agent/state.py: state shape
from agent.text_utils import find_self_name      # agent/text_utils.py: "I am First Last" -> "First Last"

ALLOWED_TOOLS = ("get_customer", "find_customer")


def make_resolve_customer(tools: dict[str, Any]) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the resolve_customer node."""
    belt = restrict(tools, ALLOWED_TOOLS, "resolve_customer")

    async def resolve_customer(state: TicketState) -> dict[str, Any]:
        unclear = {"customer": None, "outcome": "needs_clarification"}
        # An explicit customer_id wins (a customer who clarified), then the id stored on the ticket.
        customer_id = state.get("customer_id") or state["ticket"].get("customer_id")
        if not customer_id:
            name = find_self_name(state["ticket"]["text"])
            if not name:
                return unclear
            matches = (await belt.call("find_customer", query=name))["items"]          # orders-server tool
            if len(matches) != 1:                                                      # none or ambiguous: ask
                return unclear
            customer_id = matches[0]["id"]
        found = await belt.call("get_customer", customer_id=customer_id)               # masked details + fraud_flag
        return unclear if "error" in found else {"customer": found["customer"]}

    return resolve_customer
