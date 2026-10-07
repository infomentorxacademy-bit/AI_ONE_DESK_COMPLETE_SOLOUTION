"""common/responses.py : the standard shape of every tool result (ground rule G2).

WHAT   error() builds {"error": CODE, "message": ...}; items() builds {"items": [...]}.
WHY    Through the MCP adapter an empty list and None both arrive as []. A dict
       always arrives intact, so callers can tell "empty" from "failed".
USED BY servers/orders_server.py, servers/knowledge_server.py, servers/ops_server.py
"""
from __future__ import annotations

from typing import Any


def error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    """Expected failure (not found, rule refused...). Returned, never raised, so the agent can react."""
    return {"error": code, "message": message, **extra}


def items(rows: list[Any], **extra: Any) -> dict[str, Any]:
    """Wrap a list so an empty list is still a dict: {"items": []}."""
    return {"items": rows, **extra}
