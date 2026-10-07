"""Node 9 of Graph A: incident_reply. Payment-failure tickets: reply if linked to an incident, else hand over to Graph B.

TOOLS  none (the ticket's incident id was already loaded by classify)
LLM    llm.draft("incident", ...) - the one draft call for this ticket. No refund is ever issued here.
"""
from __future__ import annotations

import asyncio                                   # standard library: run the LLM call off the event loop
from typing import Any, Awaitable, Callable

from agent.reply_facts import build_reply        # agent/reply_facts.py: safe facts for the template
from agent.state import TicketState              # agent/state.py: state shape

ALLOWED_TOOLS: tuple[str, ...] = ()


def make_incident_reply(llm: Any) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the incident_reply node."""

    async def incident_reply(state: TicketState) -> dict[str, Any]:
        if not state.get("incident_id"):
            return {"outcome": "needs_incident_flow"}        # not linked yet: Graph B must cluster and link first
        template, facts = build_reply({**state, "outcome": "linked_incident"})
        reply = await asyncio.to_thread(llm.draft, template, facts)
        return {"outcome": "linked_incident", "reply": reply}

    return incident_reply
