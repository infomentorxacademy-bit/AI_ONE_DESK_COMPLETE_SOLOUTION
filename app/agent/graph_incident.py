"""agent/graph_incident.py : GRAPH B - the outage detector. Wires 6 nodes (section 13.3). No business logic here.

  START > collect_tickets > cluster --(fewer than 3 similar tickets)--> END
                              | 3 or more
                              v
          correlate > link_tickets > propose_rollback > draft_notes > END

Input: {} (it looks at the whole queue). Compiled with a checkpointer like Graph A.
"""
from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver   # langgraph: in-memory run storage
from langgraph.graph import END, START, StateGraph      # langgraph: graph builder + entry/exit markers

from agent.state import IncidentState                   # agent/state.py: state shape
from agent.nodes.incident.cluster import make_cluster                       # one file per node
from agent.nodes.incident.collect_tickets import make_collect_tickets
from agent.nodes.incident.correlate import make_correlate
from agent.nodes.incident.draft_notes import make_draft_notes
from agent.nodes.incident.link_tickets import make_link_tickets
from agent.nodes.incident.propose_rollback import make_propose_rollback


def _after_cluster(state: IncidentState) -> str:
    """A cluster needs 3 or more tickets; otherwise this is not an outage and the graph ends."""
    return "correlate" if state.get("cluster_ids") else END


def build_incident_graph(tools: dict[str, Any], llm: Any, checkpointer: Any = None):
    """Build and compile Graph B. `tools` = all MCP tools by name; `llm` = LLMClient."""
    g = StateGraph(IncidentState)
    g.add_node("collect_tickets", make_collect_tickets(tools))
    g.add_node("cluster", make_cluster(llm))
    g.add_node("correlate", make_correlate(tools))
    g.add_node("link_tickets", make_link_tickets(tools))
    g.add_node("propose_rollback", make_propose_rollback(tools))
    g.add_node("draft_notes", make_draft_notes(llm))

    g.add_edge(START, "collect_tickets")
    g.add_edge("collect_tickets", "cluster")
    g.add_conditional_edges("cluster", _after_cluster, ["correlate", END])
    g.add_edge("correlate", "link_tickets")
    g.add_edge("link_tickets", "propose_rollback")
    g.add_edge("propose_rollback", "draft_notes")
    g.add_edge("draft_notes", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
