"""agent/graph_ticket.py : GRAPH A - wires the 11 ticket nodes into one LangGraph StateGraph.

This file contains NO business logic. It only answers "which node runs next?" (section 13.2):

  START > classify, then route by the kind of ticket:
    privacy / injection        -> safe_reply -> draft_reply -> finish
    policy                     -> answer_policy -> draft_reply -> finish
    incident_report            -> incident_reply -> finish
    status / refund            -> resolve_customer
      unclear who              -> draft_reply
      otherwise                -> fetch_order
        not found / not theirs / status ticket -> draft_reply
        refund                 -> check_rules
          duplicate / declined / incident       -> draft_reply
          OK_AUTO / OK_APPROVED                 -> issue_refund -> draft_reply
          NEEDS_* / BAD_APPROVALS               -> approval_gate (interrupt)
            approve / edit_amount -> check_rules (loop back);  reject -> draft_reply;  cancel -> finish
  draft_reply -> finish -> END

The graph is compiled WITH a checkpointer (InMemorySaver) so interrupt() can pause and resume.
"""
from __future__ import annotations

from typing import Any

# langgraph: StateGraph builds the graph; START/END are its entry and exit; InMemorySaver stores paused runs.
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agent.state import TicketState                        # agent/state.py: the state shape
# One factory per node, each in its own file under agent/nodes/ticket/.
from agent.nodes.ticket.answer_policy import make_answer_policy
from agent.nodes.ticket.approval_gate import make_approval_gate
from agent.nodes.ticket.check_rules import make_check_rules
from agent.nodes.ticket.classify import make_classify
from agent.nodes.ticket.draft_reply import make_draft_reply
from agent.nodes.ticket.fetch_order import make_fetch_order
from agent.nodes.ticket.finish import make_finish
from agent.nodes.ticket.incident_reply import make_incident_reply
from agent.nodes.ticket.issue_refund import make_issue_refund
from agent.nodes.ticket.resolve_customer import make_resolve_customer
from agent.nodes.ticket.safe_reply import make_safe_reply


# ----------------------------------------------------------------------------- routing functions
def _after_classify(state: TicketState) -> str:
    """Pick the branch from the ticket kind."""
    return {"privacy": "safe_reply", "injection": "safe_reply", "policy": "answer_policy",
            "incident_report": "incident_reply"}.get(state["kind"], "resolve_customer")


def _after_resolve(state: TicketState) -> str:
    """If we could not tell who the customer is, go straight to drafting the clarifying question."""
    return "draft_reply" if state.get("outcome") else "fetch_order"


def _after_fetch(state: TicketState) -> str:
    """An outcome already exists (not found / not theirs / status answered): just draft the reply."""
    return "draft_reply" if state.get("outcome") else "check_rules"


def _after_check(state: TicketState) -> str:
    """Duplicate/declined/incident => reply; allowed => pay; otherwise a human must decide."""
    if state.get("outcome"):
        return "draft_reply"
    return "issue_refund" if state["rule"]["allowed"] else "approval_gate"


def _after_gate(state: TicketState) -> str:
    """approve/edit => re-check the rules; reject => reply; cancel => finish (ticket stays pending_approval)."""
    action = state.get("gate_action")
    if action in ("approve", "edit_amount"):
        return "check_rules"
    return "draft_reply" if action == "reject" else "finish"


def build_ticket_graph(tools: dict[str, Any], llm: Any, checkpointer: Any = None):
    """Build and compile Graph A. `tools` = all 21 MCP tools by name; `llm` = LLMClient (agent/llm/base.py)."""
    g = StateGraph(TicketState)

    # --- register the 11 nodes (each factory returns an async function) ---
    g.add_node("classify", make_classify(tools, llm))
    g.add_node("resolve_customer", make_resolve_customer(tools))
    g.add_node("fetch_order", make_fetch_order(tools))
    g.add_node("check_rules", make_check_rules())
    g.add_node("approval_gate", make_approval_gate(tools))
    g.add_node("issue_refund", make_issue_refund(tools))
    g.add_node("answer_policy", make_answer_policy(tools))
    g.add_node("safe_reply", make_safe_reply())
    g.add_node("incident_reply", make_incident_reply(llm))
    g.add_node("draft_reply", make_draft_reply(llm))
    g.add_node("finish", make_finish(tools))

    # --- wire them ---
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", _after_classify,
                            ["safe_reply", "answer_policy", "incident_reply", "resolve_customer"])
    g.add_edge("safe_reply", "draft_reply")
    g.add_edge("answer_policy", "draft_reply")
    g.add_edge("incident_reply", "finish")
    g.add_conditional_edges("resolve_customer", _after_resolve, ["draft_reply", "fetch_order"])
    g.add_conditional_edges("fetch_order", _after_fetch, ["draft_reply", "check_rules"])
    g.add_conditional_edges("check_rules", _after_check, ["draft_reply", "issue_refund", "approval_gate"])
    g.add_conditional_edges("approval_gate", _after_gate, ["check_rules", "draft_reply", "finish"])
    g.add_edge("issue_refund", "draft_reply")
    g.add_edge("draft_reply", "finish")
    g.add_edge("finish", END)

    return g.compile(checkpointer=checkpointer or InMemorySaver())
