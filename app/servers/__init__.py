"""servers/ : the THREE MCP servers (one file per server, as required by NFR-14).

  orders_server.py     support operations : orders, customers, refunds, tickets, audit
  knowledge_server.py  policy team        : refund/security policy and FAQ (read-only)
  ops_server.py        platform team      : deployments, metrics, logs, incidents, rollback PROPOSALS

Each file is deliberately thin: it declares the MCP tools/resources/prompts (their names, arguments
and LLM-facing docstrings) and delegates the real work to common/repositories, common/stores and
common/rules.py. Run one with:   python -m servers.orders_server   (from the app/ folder)
"""
