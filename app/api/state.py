"""api/state.py : the objects shared by all requests (created once at startup).

WHAT   AppState holds: the 21 MCP tools (via a least-privilege ToolBelt), the chosen LLM, the two compiled
       graphs, and the list of paused approvals.
WHY    Starting the MCP servers costs about a second each, so they are started ONCE when the API starts and
       reused. Choosing a different LLM rebuilds the graphs but keeps the same checkpointer, so approvals that
       are already waiting for a human survive the switch.
USED BY api/main.py, api/routers/*.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from langgraph.checkpoint.memory import InMemorySaver      # langgraph: remembers paused runs (shared by both graphs)

from agent.graph_incident import build_incident_graph      # agent/graph_incident.py: Graph B
from agent.graph_ticket import build_ticket_graph          # agent/graph_ticket.py: Graph A
from agent.llm.base import LLMClient                       # agent/llm/base.py: the interface of an LLM backend
from agent.mcp_utils import ToolBelt, restrict             # agent/mcp_utils.py: least-privilege tool access

# The ONLY tools the web API itself may call directly. It cannot call issue_refund or propose_rollback:
# money moves only through the agent graph, never straight from an HTTP request (least privilege, G7).
API_TOOLS = ("get_ticket", "list_tickets", "create_ticket", "get_audit_trail", "find_customer",
             "list_incidents", "get_incident", "list_rollback_proposals")


class NoLlmChosen(RuntimeError):
    """Raised when an action needs the LLM but none has been selected yet."""


@dataclass
class AppState:
    """Everything the routers need. One instance lives on `app.state.ops`."""
    tools: dict[str, Any]                                    # all 21 MCP tools (graphs need them)
    llm_loader: Callable[[str], LLMClient]                   # builds an LLM for a provider name (injectable in tests)
    belt: ToolBelt = field(init=False)                       # the API's own restricted view of the tools
    llm: LLMClient | None = None
    ticket_graph: Any = None
    incident_graph: Any = None
    checkpointer: InMemorySaver = field(default_factory=InMemorySaver)
    pending: dict[str, dict[str, Any]] = field(default_factory=dict)   # thread_id -> {ticket_id, card}

    def __post_init__(self) -> None:
        self.belt = restrict(self.tools, API_TOOLS, "api")

    def select_llm(self, provider: str) -> LLMClient:
        """Create the LLM for `provider` and rebuild both graphs around it. Raises if the key is missing."""
        llm = self.llm_loader(provider)
        self.llm = llm
        self.ticket_graph = build_ticket_graph(self.tools, llm, self.checkpointer)
        self.incident_graph = build_incident_graph(self.tools, llm, self.checkpointer)
        return llm

    def require_llm(self) -> None:
        """Guard used by endpoints that run the agent."""
        if self.llm is None:
            raise NoLlmChosen("No LLM selected. Choose OpenAI or Groq first (POST /api/llm).")
