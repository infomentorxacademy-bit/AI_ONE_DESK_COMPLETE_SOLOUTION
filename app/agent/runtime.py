"""agent/runtime.py : run a graph, and handle the pause/resume (human approval) loop.

WHAT   run_ticket()   run Graph A for one ticket and keep answering approval cards until it finishes.
       run_incident() run Graph B once.
WHY    LangGraph pauses with interrupt(); the caller must resume with Command(resume=answer) on the
       SAME thread_id (NFR-10). That protocol lives here once, so run_queue.py and the tests do not repeat it.
USED BY run_queue.py, tests/test_scenarios.py
"""
from __future__ import annotations

import uuid                                   # standard library: unique thread ids for each run
from dataclasses import dataclass, field
from typing import Any

from langgraph.types import Command           # langgraph: Command(resume=...) continues a paused graph


@dataclass
class TicketRun:
    """What happened when one ticket went through Graph A."""
    ticket_id: str
    first: dict[str, Any]                                       # result of the FIRST invoke (before any human answer)
    final: dict[str, Any]                                       # result after all cards were answered
    cards: list[dict[str, Any]] = field(default_factory=list)   # every approval card shown
    thread_id: str = ""

    @property
    def paused_first(self) -> bool:
        return "__interrupt__" in self.first

    @property
    def first_label(self) -> str:
        """'paused' if a human was needed, otherwise the outcome."""
        return "paused" if self.paused_first else self.first.get("outcome", "?")


def interrupt_card(result: dict[str, Any]) -> dict[str, Any] | None:
    """The approval card if the graph is paused, else None."""
    pending = result.get("__interrupt__")
    return pending[0].value if pending else None


async def start_ticket(graph: Any, ticket_id: str, customer_id: str | None = None,
                       thread_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Begin Graph A for a ticket. Returns (result, config); keep `config` to resume with the same thread."""
    config = {"configurable": {"thread_id": thread_id or f"{ticket_id}-{uuid.uuid4().hex[:8]}"}}
    payload: dict[str, Any] = {"ticket_id": ticket_id}
    if customer_id:
        payload["customer_id"] = customer_id
    return await graph.ainvoke(payload, config), config


async def resume(graph: Any, config: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """Send a human's answer into a paused graph (same thread_id) and continue."""
    return await graph.ainvoke(Command(resume=answer), config)


async def run_ticket(graph: Any, ticket_id: str, approver: Any | None = None,
                     customer_id: str | None = None) -> TicketRun:
    """Run one ticket. If `approver` is given, answer every approval card with it; otherwise stop at the first pause."""
    first, config = await start_ticket(graph, ticket_id, customer_id)
    run = TicketRun(ticket_id, first, first, thread_id=config["configurable"]["thread_id"])
    result = first
    while (card := interrupt_card(result)) is not None:
        run.cards.append(card)
        if approver is None:
            break
        result = await resume(graph, config, approver.answer(card))
    run.final = result
    return run


async def run_incident(graph: Any) -> dict[str, Any]:
    """Run Graph B over the whole queue once."""
    return await graph.ainvoke({}, {"configurable": {"thread_id": f"incident-{uuid.uuid4().hex[:8]}"}})
