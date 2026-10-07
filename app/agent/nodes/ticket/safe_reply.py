"""Node 8 of Graph A: safe_reply. Handle tickets that must NOT be acted on: privacy requests and injections.

TOOLS  none
PRIVACY    asking for another person's data  => outcome refused_privacy (FR-36)
INJECTION  text that tries to give orders    => outcome ignored_injection + flag possible_injection (FR-37)
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from agent.state import TicketState              # agent/state.py: state shape

ALLOWED_TOOLS: tuple[str, ...] = ()


def make_safe_reply() -> Callable[[TicketState], Awaitable[dict[str, Any]]]:
    """Build the safe_reply node."""

    async def safe_reply(state: TicketState) -> dict[str, Any]:
        if state["kind"] == "privacy":
            return {"outcome": "refused_privacy"}
        flags = sorted(set(state.get("flags", [])) | {"possible_injection"})
        return {"outcome": "ignored_injection", "flags": flags}

    return safe_reply
