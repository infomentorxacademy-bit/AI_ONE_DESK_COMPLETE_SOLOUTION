"""agent/state.py : the data that flows through the graphs, plus the outcome vocabulary.

WHAT   TicketState (Graph A), IncidentState (Graph B), OUTCOMES, OUTCOME_TO_STATUS.
WHY    LangGraph passes one "state" dict from node to node. Each node returns only the keys it
       changes. Declaring the keys here gives every reviewer one place to see what the agent knows.
USED BY agent/nodes/*, agent/graph_ticket.py, agent/graph_incident.py, run_queue.py, tests
"""
from __future__ import annotations

from typing import Any, TypedDict   # standard library typing: TypedDict documents the state keys

# Every way a ticket can end (section 13.1) and the ticket status it maps to.
OUTCOME_TO_STATUS: dict[str, str] = {
    "answered": "resolved",                 # status or policy question answered
    "refund_issued": "resolved",            # refund created (automatic or after approval)
    "refund_duplicate": "resolved",         # already refunded; customer told which refund
    "refund_declined": "declined",          # late, not delivered, over price, or rejected by an approver
    "refused_privacy": "declined",          # asked for someone else's data / an order that is not theirs
    "pending_approval": "pending_approval", # a human has not decided yet (or cancelled)
    "needs_clarification": "in_progress",   # could not tell who the customer is; asked a question
    "ignored_injection": "escalated",       # ticket tried to give orders; ignored and flagged
    "order_not_found": "escalated",         # order id does not exist
    "linked_incident": "linked_to_incident",# ticket belongs to an active incident
    "needs_incident_flow": "escalated",     # payment-failure ticket not yet linked: hand to Graph B
}
OUTCOMES: tuple[str, ...] = tuple(OUTCOME_TO_STATUS)


class TicketState(TypedDict, total=False):
    """State of Graph A. `total=False` because nodes fill keys in gradually."""
    # ---- input
    ticket_id: str                    # which ticket to process, e.g. "T3"
    customer_id: str                  # OPTIONAL override: a customer who clarified who they are
    # ---- filled by classify
    ticket: dict[str, Any]            # the ticket row from get_ticket
    kind: str                         # status | refund | policy | privacy | injection | incident_report
    flags: list[str]                  # safety flags, e.g. "possible_injection", "fraud_flag"
    incident_id: str | None           # incident the ticket is linked to (if any)
    # ---- filled by resolve_customer / fetch_order
    requested_order_id: str | None    # the order id mentioned in the ticket (used in "order not found" replies)
    customer: dict[str, Any] | None
    order: dict[str, Any] | None
    existing_refund: dict[str, Any] | None
    amount: int                       # amount we intend to refund (starts at the order price)
    # ---- approval loop
    rule: dict[str, Any]              # last result of check_refund()
    approvals: list[dict[str, str]]   # humans who approved so far
    gate_action: str                  # approve | edit_amount | reject | cancel (last human answer)
    # ---- result
    policy_hit: dict[str, Any] | None # section + text found by answer_policy
    refund: dict[str, Any] | None     # the refund that was issued
    decline_reason: str               # customer-safe reason used in a decline reply
    outcome: str                      # one of OUTCOMES
    reply: str                        # the drafted customer reply
    final_status: str                 # status written by finish


class IncidentState(TypedDict, total=False):
    """State of Graph B (the outage detector)."""
    tickets: list[dict[str, Any]]     # all tickets with status "new"
    service: str                      # affected service (payments-api)
    cluster: list[dict[str, Any]]     # tickets that look like one outage
    cluster_ids: list[str]
    spike: dict[str, Any]             # result of find_spike
    deployments: list[dict[str, Any]]
    correlated: dict[str, Any] | None # the deployment that happened 0-10 minutes BEFORE the spike
    incident_id: str | None
    flags: list[str]                  # e.g. "suspicious_log_line"
    suspicious_lines: list[str]
    link_result: dict[str, Any]
    proposal: dict[str, Any] | None
    engineer_note: str
    customer_message: str
