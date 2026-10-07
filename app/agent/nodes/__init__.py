"""agent/nodes/ : the individual graph nodes, ONE FILE PER NODE.

Every node module follows the same pattern so it is easy to review:
  ALLOWED_TOOLS      the exact MCP tools this node may call (least privilege, G7 / NFR-06)
  make_<node>(...)   a factory that receives the tools (and the LLM if needed) and returns the
                     async node function LangGraph will run. A node takes the state and returns ONLY
                     the keys it changes.
"""
