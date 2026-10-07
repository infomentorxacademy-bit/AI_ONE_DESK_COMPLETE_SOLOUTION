"""agent/mcp_utils.py : how the agent talks to the three MCP servers.

WHAT   open_tools()   start the 3 servers ONCE and return all 21 tools by name
       restrict()     give a graph node ONLY the tools it is allowed to call (least privilege, G7)
       unwrap()       turn a tool result into a plain dict
WHY    Opening a new connection per tool call starts a new Python process each time (about 1 second).
       We keep one session per server open for the whole run. restrict() makes it impossible for,
       say, the draft node to call issue_refund, even by mistake (NFR-06).
USED BY run_queue.py, tests/conftest.py, spike/*
"""
from __future__ import annotations

import json                                   # standard library: decode the JSON text a tool returns
import os                                     # standard library: pass the OPSDESK_* settings to the servers
import sys                                    # standard library: sys.executable = the current Python
from contextlib import AsyncExitStack, asynccontextmanager   # standard library: keep several sessions open together
from typing import Any, AsyncIterator

# langchain-mcp-adapters: MultiServerMCPClient knows how to start MCP servers; load_mcp_tools converts
# the MCP tools of an open session into LangChain tools that LangGraph nodes can call.
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from common.config import APP_ROOT            # common/config.py: the app/ folder (servers run from here)

# server name -> Python module that runs it. Started with "python -m <module>" from the app/ folder.
SERVERS: dict[str, str] = {
    "orders": "servers.orders_server",
    "knowledge": "servers.knowledge_server",
    "ops": "servers.ops_server",
}


def _connection(module: str) -> dict[str, Any]:
    """How to launch one server over STDIO (the agent starts the process and talks over stdin/stdout)."""
    # Servers only receive OPSDESK_* settings (database / data folder). Secrets such as OPENAI_API_KEY or
    # GROQ_API_KEY are NOT passed on: the MCP servers never need an LLM key (least privilege, G9).
    env = {k: v for k, v in os.environ.items() if k.startswith("OPSDESK_")}
    return {"transport": "stdio", "command": sys.executable, "args": ["-m", module],
            "cwd": str(APP_ROOT), "env": env}


@asynccontextmanager
async def open_tools() -> AsyncIterator[dict[str, Any]]:
    """Start all three servers once; yield {tool_name: LangChain tool} (21 tools); close them on exit.

    Usage:  async with open_tools() as tools:  ...  await tools["get_order"].ainvoke({"order_id": "O1001"})
    """
    client = MultiServerMCPClient({name: _connection(module) for name, module in SERVERS.items()})
    async with AsyncExitStack() as stack:
        tools: dict[str, Any] = {}
        for name in SERVERS:
            session = await stack.enter_async_context(client.session(name))   # one long-lived session per server
            for tool in await load_mcp_tools(session):
                tools[tool.name] = tool
        yield tools


class ToolBelt:
    """A read-only view of a few tools. Asking for any other tool raises a clear error (least privilege)."""

    def __init__(self, tools: dict[str, Any], allowed: tuple[str, ...], owner: str) -> None:
        missing = [n for n in allowed if n not in tools]
        if missing:
            raise KeyError(f"{owner}: tools not available: {missing}")
        self._tools = {name: tools[name] for name in allowed}
        self._owner = owner

    async def call(self, name: str, **arguments: Any) -> dict[str, Any]:
        """Call an allowed tool and return its result as a dict."""
        if name not in self._tools:
            raise PermissionError(f"Node '{self._owner}' may not call tool '{name}'. Allowed: {sorted(self._tools)}")
        return unwrap(await self._tools[name].ainvoke(arguments))


def restrict(tools: dict[str, Any], allowed: tuple[str, ...], owner: str) -> ToolBelt:
    """Build a ToolBelt for one graph node. `owner` is the node name (used in error messages)."""
    return ToolBelt(tools, allowed, owner)


def unwrap(result: Any) -> dict[str, Any]:
    """Convert whatever a tool returns (dict, JSON text, or a list of content blocks) into ONE dict.

    Every server tool returns a dict (ground rule G2), so after unwrapping we always get a dict back.
    """
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        return json.loads(result)
    if isinstance(result, list):                       # list of {"type": "text", "text": "<json>"} blocks
        for block in result:
            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
            if text:
                return json.loads(text)
    raise ValueError(f"Cannot unwrap tool result: {result!r}")
