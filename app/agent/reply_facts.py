"""agent/reply_facts.py : choose the reply template and the SAFE facts for it.

WHAT   build_reply(state) -> (template_name, facts)
WHY    The LLM only ever sees facts built here. Because this function never includes the fraud flag,
       a phone number, an address or another customer's data, the reply cannot leak them (FR-36, FR-39).
       Keeping this in one file also means a reviewer can audit "what can reach the customer" in one place.
USED BY agent/nodes/ticket/draft_reply.py, agent/nodes/ticket/incident_reply.py
"""
from __future__ import annotations

from typing import Any

from agent.text_utils import find_order_id     # agent/text_utils.py: order id from ticket text
from agent.state import TicketState            # agent/state.py: the state shape

# Customer-safe reasons for a decline. They explain the rule WITHOUT revealing internal flags.
DECLINE_REASONS = {
    "NOT_DELIVERED": "the order has not been delivered yet",
    "LATE": "the 30-day refund window after delivery has passed",
    "OVER_PRICE": "the requested amount is more than the order price",
    "REJECTED": "our team reviewed the request and could not approve it",
    "BLOCKED": "we could not complete this refund under our policy",
}


def _status_detail(order: dict[str, Any]) -> str:
    """One sentence about where the order is, built only from get_order data (FR-28)."""
    if order["status"] == "shipped":
        return f"It is on its way and the expected delivery date is {order['expected_on']}."
    if order["status"] == "delivered":
        return f"It was delivered on {order['delivered_on']}."
    if order["status"] == "cancelled":
        return "It was cancelled."
    return f"We are preparing it and the expected date is {order['expected_on']}."


def build_reply(state: TicketState) -> tuple[str, dict[str, Any]]:
    """Return (template name from common/templates.py, facts dict) for the ticket's outcome."""
    outcome = state.get("outcome", "")
    customer = state.get("customer") or {}
    order = state.get("order") or {}
    name = customer.get("name", "there")
    base = {"name": name, "order_id": order.get("id") or state.get("requested_order_id") or "",
            "item": order.get("item", "")}

    if outcome == "answered" and state.get("kind") == "policy":
        hit = state.get("policy_hit") or {}
        if not hit:
            return "policy_answer", {"section": "n/a", "text": "I am not sure, a support lead will help."}
        return "policy_answer", {"section": hit["section"], "text": hit["text"]}
    if outcome == "answered":
        return "status", {**base, "status": order["status"], "detail": _status_detail(order)}
    if outcome == "refund_issued":
        refund = state["refund"]
        return "refund_ok", {**base, "amount": refund["amount"], "refund_id": refund["id"]}
    if outcome == "refund_duplicate":
        refund = state["existing_refund"]
        return "refund_duplicate", {**base, "refund_id": refund["id"], "refund_status": refund["status"]}
    if outcome == "refund_declined":
        return "refund_declined", {**base, "reason": state.get("decline_reason", DECLINE_REASONS["BLOCKED"])}
    if outcome == "refused_privacy":
        return "privacy_refusal", {}
    if outcome == "pending_approval":
        return "refund_pending", {**base, "amount": state.get("amount", "")}
    if outcome == "needs_clarification":
        return "clarify", {}
    if outcome == "ignored_injection":
        return "injection_escalated", {}
    if outcome == "order_not_found":
        return "order_not_found", base
    if outcome == "linked_incident":
        order_id = find_order_id(state.get("ticket", {}).get("text", ""))
        return "incident", {"order_clause": f" for order {order_id}" if order_id else ""}
    return "status", base          # unreachable in normal flows; harmless default
