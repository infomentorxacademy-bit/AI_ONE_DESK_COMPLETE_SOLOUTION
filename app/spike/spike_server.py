"""spike/spike_server.py : the smallest possible MCP server (one tool: add). Used by spike_client.py.

A "spike" is a throwaway program that proves a technique works before we build on it.
"""
from fastmcp import FastMCP     # third-party: the MCP server framework

mcp = FastMCP("spike")


@mcp.tool
def add(a: int, b: int) -> dict:
    """Add two whole numbers. Returns {"result": a + b}."""
    return {"result": a + b}


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="WARNING")
