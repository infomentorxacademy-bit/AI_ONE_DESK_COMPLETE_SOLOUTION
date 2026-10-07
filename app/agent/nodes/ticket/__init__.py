"""agent/nodes/ticket/ : the 11 nodes of Graph A (one customer ticket).

classify -> (resolve_customer -> fetch_order -> check_rules -> approval_gate -> issue_refund)
         -> answer_policy / safe_reply / incident_reply -> draft_reply -> finish
Wiring (which node leads to which) is in agent/graph_ticket.py.
"""
