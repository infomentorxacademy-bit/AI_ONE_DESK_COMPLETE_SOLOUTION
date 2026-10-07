"""Node 10 of Graph A: draft_reply. Turn the outcome into customer wording.

TOOLS  none
LLM    llm.draft() - the second (and last) LLM call allowed per ticket (NFR-16). Skipped if a reply already exists.
SAFE   The LLM receives only the facts built by agent/reply_facts.py (no fraud flag, no PII).
"""
from __future__ import annotations

import asyncio                                   # standard library: run the LLM call off the event loop
from typing import Any, Awaitable, Callable

from agent.reply_facts import build_reply        # agent/reply_facts.py: (template, safe facts) for this outcome
from agent.state import TicketState              # agent/state.py: state shape

ALLOWED_TOOLS: tuple[str, ...] = ()


def make_draft_reply(llm: Any) -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the draft_reply node."""

    async def draft_reply(state: TicketState) -> dict[str, Any]:
        if state.get("reply"):
            return {}
        template, facts = build_reply(state)
        return {"reply": await asyncio.to_thread(llm.draft, template, facts)}

    return draft_reply
