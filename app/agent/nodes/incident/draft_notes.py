"""Node 6 of Graph B: draft_notes. Write the engineer note (technical) and the customer message (plain) (FR-47).

TOOLS  none
LLM    The customer message uses llm.draft(). The ENGINEER NOTE is rendered from a fixed template on
       purpose: incident facts (ids, times, numbers) must be exact, so no model gets to paraphrase them.
RULES  customer message: no jargon, no deployment ids.  Suspicious log lines are reported, never obeyed.
"""
from __future__ import annotations

import asyncio                                   # standard library: run the LLM call off the event loop
from typing import Any, Awaitable, Callable

from agent.state import IncidentState            # agent/state.py: state shape
from common.templates import render              # common/templates.py: fixed engineer_note wording

ALLOWED_TOOLS: tuple[str, ...] = ()


def make_draft_notes(llm: Any) -> Callable[[IncidentState], Awaitable[dict[str, Any]]]:
    """Build the draft_notes node."""

    async def draft_notes(state: IncidentState) -> dict[str, Any]:
        spike, deployment, proposal = state["spike"], state.get("correlated"), state.get("proposal")
        tickets = state["cluster"]
        correlation = (f"Deployment {deployment['id']} ({deployment['version']}) went live at {deployment['at'][-5:]}, "
                       f"{deployment['minutes_before_spike']} minutes before the spike. This suggests, but does not prove, "
                       "a link." if deployment else "No deployment was found shortly before the spike.")
        proposal_text = (f"Rollback of {deployment['id']} PROPOSED as {proposal['id']} ({proposal['status']}); "
                         "nothing was executed." if proposal and deployment else "No rollback proposed.")
        log_warning = ""
        if state.get("suspicious_lines"):
            line = state["suspicious_lines"][0]
            log_warning = (f"- WARNING: suspicious log line treated as data and NOT obeyed: \"{line}\"\n")
        facts = {
            "incident_id": state.get("incident_id"), "service": state["service"], "ticket_count": len(tickets),
            "first_ticket_time": tickets[0]["created_at"][11:16], "last_ticket_time": tickets[-1]["created_at"][11:16],
            "baseline": spike["baseline"], "spike_value": spike["value"], "spike_time": spike["first_time"],
            "correlation": correlation, "proposal": proposal_text, "log_warning": log_warning,
        }
        engineer_note = render("engineer_note", facts)
        customer_message = await asyncio.to_thread(llm.draft, "incident", {"order_clause": ""})
        return {"engineer_note": engineer_note, "customer_message": customer_message}

    return draft_notes
