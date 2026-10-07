"""Node 3 of Graph A: fetch_order. Find the order the ticket is about and load what the rules need.

TOOLS  get_order, list_customer_orders, get_refund_for_order (orders-server)
ORDER  1) an order id in the text (O + 4 digits)  2) the customer's order whose item name is in the text
       3) the customer's first order.
SAFE   An order that belongs to someone else => refused_privacy (FR-36). Unknown order => order_not_found (FR-40).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.state import TicketState              # agent/state.py: state shape
from agent.text_utils import find_order_id       # agent/text_utils.py: order id from text

ALLOWED_TOOLS = ("get_order", "list_customer_orders", "get_refund_for_order")


def make_fetch_order(tools: dict[str, Any]) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the fetch_order node."""
    belt = restrict(tools, ALLOWED_TOOLS, "fetch_order")

    async def fetch_order(state: TicketState) -> dict[str, Any]:
        text = state["ticket"]["text"]
        customer = state["customer"]
        order_id = find_order_id(text)
        order = None

        if order_id:
            found = await belt.call("get_order", order_id=order_id)
            if "error" in found:
                return {"order": None, "requested_order_id": order_id, "outcome": "order_not_found"}
            order = found["order"]
        else:
            orders = (await belt.call("list_customer_orders", customer_id=customer["id"]))["items"]
            by_item = [o for o in orders if o["item"].lower() in text.lower()]
            order = (by_item or orders or [None])[0]
            if order is None:
                return {"order": None, "requested_order_id": None, "outcome": "order_not_found"}

        if order["customer_id"] != customer["id"]:        # somebody else's order: never reveal anything about it
            return {"order": None, "requested_order_id": order_id, "outcome": "refused_privacy"}

        if state["kind"] == "status":                      # status tickets only need the order itself
            return {"order": order, "requested_order_id": order["id"], "outcome": "answered"}

        refund = (await belt.call("get_refund_for_order", order_id=order["id"]))["refund"]
        flags = list(state.get("flags", []))
        if customer.get("fraud_flag") and "fraud_flag" not in flags:
            flags.append("fraud_flag")                     # internal flag: shown on the approval card, never to the customer
        return {"order": order, "requested_order_id": order["id"], "existing_refund": refund,
                "amount": state.get("amount") or order["price"], "flags": flags}

    return fetch_order
