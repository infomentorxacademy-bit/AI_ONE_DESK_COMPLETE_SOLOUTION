"""agent/ : the LangGraph AI agent. It is the MCP CLIENT of the three servers in servers/.

  state.py          shared data shapes (TicketState, IncidentState, outcomes)
  mcp_utils.py      connect to the 3 servers once, restrict tools per node, unwrap results
  llm/              the "LLM seam": FakeLLM (offline), OpenAI and Groq behind one interface
  reply_facts.py    turns graph state into SAFE facts for reply drafting
  nodes/ticket/     one file per node of Graph A (one customer ticket)
  nodes/incident/   one file per node of Graph B (outage detector)
  graph_ticket.py   wires Graph A together
  graph_incident.py wires Graph B together
"""
