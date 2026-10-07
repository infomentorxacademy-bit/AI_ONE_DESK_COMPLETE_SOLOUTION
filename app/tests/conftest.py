"""tests/conftest.py : shared fixtures for every test file.

WHAT   * points the app at a TEMPORARY database (so tests never touch your real opsdesk.db)
       * re-seeds that database before EVERY test (tests never depend on each other)
       * `call` : call a server tool in-process (fast, no subprocess)
       * `tools`: all 21 MCP tools over real STDIO (started once per test session)
       * `ticket_graph` / `incident_graph` / `run_ticket` : the agent, ready to use
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from fastmcp import Client                                    # fastmcp: in-process MCP client (no subprocess needed)

# IMPORTANT: set the env var BEFORE importing app modules or starting servers; subprocess servers inherit it.
_TMP = tempfile.mkdtemp(prefix="opsdesk-tests-")
os.environ["OPSDESK_DB"] = str(Path(_TMP) / "test_opsdesk.db")

import seed_db                                                # noqa: E402  seed_db.py: rebuild the test database
from agent.approvers import ScriptedApprover                  # noqa: E402  agent/approvers.py: auto-answers cards
from agent.graph_incident import build_incident_graph         # noqa: E402  agent/graph_incident.py: Graph B
from agent.graph_ticket import build_ticket_graph             # noqa: E402  agent/graph_ticket.py: Graph A
from agent.llm.fake import FakeLLM                            # noqa: E402  agent/llm/fake.py: offline LLM
from agent.mcp_utils import open_tools, unwrap                # noqa: E402  agent/mcp_utils.py: servers + result unwrap
from agent.runtime import run_incident, run_ticket            # noqa: E402  agent/runtime.py: pause/resume loop
from servers.knowledge_server import mcp as knowledge_mcp     # noqa: E402  the three server objects, used in-process
from servers.ops_server import mcp as ops_mcp                 # noqa: E402
from servers.orders_server import mcp as orders_mcp           # noqa: E402

_SERVERS = {"orders": orders_mcp, "knowledge": knowledge_mcp, "ops": ops_mcp}


@pytest.fixture(autouse=True)
def fresh_db() -> None:
    """Rebuild the database before every test (the requirements promise this)."""
    seed_db.main(quiet=True)


@pytest.fixture
def call():
    """call("orders", "get_order", order_id="O1001") -> dict. Runs the tool in-process."""
    async def _call(server: str, tool: str, **arguments):
        async with Client(_SERVERS[server]) as client:
            result = await client.call_tool(tool, arguments)
            return result.structured_content
    return _call


@pytest.fixture
def client_for():
    """client_for("knowledge") -> an async context manager for resource/prompt/inventory tests."""
    return lambda server: Client(_SERVERS[server])


@pytest_asyncio.fixture(scope="session")
async def tools():
    """All 21 tools over real STDIO. A background task owns the connection so it opens and closes in ONE task."""
    ready: asyncio.Future = asyncio.get_running_loop().create_future()
    stop = asyncio.Event()

    async def owner() -> None:
        async with open_tools() as opened:
            ready.set_result(opened)
            await stop.wait()

    task = asyncio.create_task(owner())
    yield await ready
    stop.set()
    await task


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def ticket_graph(tools, llm):
    return build_ticket_graph(tools, llm)


@pytest.fixture
def incident_graph(tools, llm):
    return build_incident_graph(tools, llm)


@pytest.fixture
def run(ticket_graph):
    """run("T2") -> TicketRun that stops at the first approval pause; run("T3", ScriptedApprover()) answers cards."""
    async def _run(ticket_id: str, approver=None, customer_id: str | None = None):
        return await run_ticket(ticket_graph, ticket_id, approver, customer_id)
    return _run


@pytest.fixture
def scripted() -> ScriptedApprover:
    return ScriptedApprover()


@pytest.fixture
def ticket_of(tools):
    """ticket_of("T2") -> the current ticket row, read through the real get_ticket tool (like a later re-check)."""
    async def _get(ticket_id: str):
        return unwrap(await tools["get_ticket"].ainvoke({"ticket_id": ticket_id}))["ticket"]
    return _get


@pytest.fixture
def run_incident_flow(incident_graph):
    async def _go():
        return await run_incident(incident_graph)
    return _go
