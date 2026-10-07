"""Node 5 of Graph A: approval_gate. PAUSE for a human, then apply the human's answer.

TOOLS  update_ticket_status (orders-server) - to mark the ticket pending_approval
HOW    langgraph.types.interrupt(card) pauses the graph and hands `card` to the caller. The caller
       resumes with Command(resume=answer) on the SAME thread_id; interrupt() then returns `answer`.
       NOTE: on resume LangGraph re-runs this node from the top, so everything before interrupt()
       must be repeatable. It is: the status update is idempotent and the card is rebuilt identically.
CARD   facts first, recommendation last (NFR-17). ANSWERS  approve | edit_amount | reject | cancel.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Awaitable, Callable

from langgraph.types import interrupt            # langgraph: pause the graph and wait for a human answer

from agent.mcp_utils import restrict             # agent/mcp_utils.py: least-privilege tool access
from agent.reply_facts import DECLINE_REASONS    # agent/reply_facts.py: reason text for a rejection
from agent.state import TicketState              # agent/state.py: state shape
from common.db import today                      # common/db.py: the frozen date
from common.rules import check_refund            # common/rules.py: used to recompute "needs" after a bad approval

ALLOWED_TOOLS = ("update_ticket_status",)
ALLOWED_ACTIONS = ["approve", "reject", "edit_amount", "cancel"]


def _recommendation(state: TicketState, amount: int, needs: list[str]) -> str:
    """One plain sentence for the approver (computed from data, not written by the LLM)."""
    order = state["order"]
    days = (today() - date.fromisoformat(order["delivered_on"])).days
    roles = " and ".join(role.replace("_", " ") for role in needs)
    text = (f"Delivered {days} days ago, within the 30-day window; Rs {amount:,} is within the order price of "
            f"Rs {order['price']:,}; needs {roles}.")
    if "fraud_flag" in state.get("flags", []):
        text += " The account is flagged for extra review."
    return text + " Approve if the claim looks genuine."


def make_approval_gate(tools: dict[str, Any]) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the approval_gate node."""
    belt = restrict(tools, ALLOWED_TOOLS, "approval_gate")

    async def approval_gate(state: TicketState) -> dict[str, Any]:
        approvals = list(state.get("approvals", []))
        flags = list(state.get("flags", []))
        rule = state["rule"]

        # The same person approved twice: drop the repeat, remember why, and recompute what is still missing.
        if rule["code"] == "BAD_APPROVALS":
            approvals = approvals[:-1]
            if "duplicate_approver_rejected" not in flags:
                flags.append("duplicate_approver_rejected")
            rule = check_refund(state["order"], state["customer"], state.get("existing_refund"), state["amount"],
                                approvals, incident_active=bool(state.get("incident_id")), today=today())

        amount = state["amount"]
        needs = rule["needs"]
        await belt.call("update_ticket_status", ticket_id=state["ticket_id"], status="pending_approval",
                        resolution=f"Waiting for approval from: {', '.join(needs)}", actor="agent")

        card = {
            "ticket_id": state["ticket_id"], "order_id": state["order"]["id"], "item": state["order"]["item"],
            "amount": amount, "needs": needs, "rule": rule["code"], "flags": flags,
            "recommendation": _recommendation(state, amount, needs), "allowed_actions": ALLOWED_ACTIONS,
        }
        answer = interrupt(card)            # <-- the graph PAUSES here until a human answers

        action = answer.get("action") if isinstance(answer, dict) else None
        update: dict[str, Any] = {"approvals": approvals, "flags": flags, "gate_action": action or "cancel"}
        if action in ("approve", "edit_amount") and answer.get("approver_id") and answer.get("role"):
            update["approvals"] = approvals + [{"approver_id": answer["approver_id"], "role": answer["role"]}]
            if action == "edit_amount":
                update["amount"] = int(answer["amount"])        # re-checked by check_rules (above price => refused)
        elif action == "reject":
            update.update(outcome="refund_declined", decline_reason=DECLINE_REASONS["REJECTED"])
        else:                                                    # cancel, unknown action or incomplete answer
            update.update(gate_action="cancel", outcome="pending_approval")   # safest: nothing is paid
        return update

    return approval_gate
