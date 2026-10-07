"""spike/spike_client.py : proves that a LangGraph NODE can call an MCP TOOL.

Run from app/:  python spike/spike_client.py      Expected: "tools discovered: ['add']" then "RESULT: ... 5"
"""
import asyncio                                   # standard library: the graph is async
import sys                                       # standard library: sys.executable = this Python
from pathlib import Path                         # standard library: locate spike_server.py

# langchain-mcp-adapters: start the server over stdio and turn its tools into LangChain tools.
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import END, START, StateGraph   # langgraph: build a tiny one-node graph
from typing import TypedDict

SERVER = str(Path(__file__).with_name("spike_server.py"))


class State(TypedDict, total=False):
    result: str


async def main() -> None:
    client = MultiServerMCPClient({"spike": {"transport": "stdio", "command": sys.executable, "args": [SERVER]}})
    async with client.session("spike") as session:
        tools = {t.name: t for t in await load_mcp_tools(session)}
        print("tools discovered:", list(tools))

        async def call_add(state: State) -> State:          # the NODE: it calls the MCP tool
            return {"result": str(await tools["add"].ainvoke({"a": 2, "b": 3}))}

        graph = StateGraph(State)
        graph.add_node("call_add", call_add)
        graph.add_edge(START, "call_add")
        graph.add_edge("call_add", END)
        print("RESULT:", (await graph.compile().ainvoke({}))["result"])


asyncio.run(main())
