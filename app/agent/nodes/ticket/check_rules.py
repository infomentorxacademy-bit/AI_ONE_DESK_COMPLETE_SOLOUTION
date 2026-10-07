"""Node 4 of Graph A: check_rules. Ask the rule function what to do next. NO tools, NO LLM.

WHY    G1: money decisions are plain Python. This node only calls common/rules.py check_refund() and
       translates its code into a ticket outcome (or leaves outcome empty so the graph keeps going).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.reply_facts import DECLINE_REASONS    # agent/reply_facts.py: customer-safe decline reasons
from agent.state import TicketState              # agent/state.py: state shape
from common.db import today                      # common/db.py: the frozen date
from common.rules import check_refund            # common/rules.py: THE refund policy function

ALLOWED_TOOLS: tuple[str, ...] = ()              # pure Python: this node calls no tools at all

# rule code -> (ticket outcome, decline-reason key). Codes not listed here keep the graph moving.
_TERMINAL = {
    "ALREADY_REFUNDED": ("refund_duplicate", None),
    "NOT_DELIVERED": ("refund_declined", "NOT_DELIVERED"),
    "LATE": ("refund_declined", "LATE"),
    "OVER_PRICE": ("refund_declined", "OVER_PRICE"),
    "INCIDENT_ACTIVE": ("linked_incident", None),
}


def make_check_rules() -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the check_rules node."""

    async def check_rules(state: TicketState) -> dict[str, Any]:
        rule = check_refund(
            state["order"], state["customer"], state.get("existing_refund"), state["amount"],
            state.get("approvals", []), incident_active=bool(state.get("incident_id")), today=today(),
        )
        flags = sorted(set(state.get("flags", [])) | set(rule["flags"]))
        update: dict[str, Any] = {"rule": rule, "flags": flags}
        if rule["code"] in _TERMINAL:
            outcome, reason_key = _TERMINAL[rule["code"]]
            update["outcome"] = outcome
            if reason_key:
                update["decline_reason"] = DECLINE_REASONS[reason_key]
        return update

    return check_rules
