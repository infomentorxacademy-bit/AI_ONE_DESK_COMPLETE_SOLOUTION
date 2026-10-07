"""api/ : the FastAPI backend (LAYER 4) that the React UI talks to.

It adds NO business logic. It exposes the existing agent over HTTP:
  * reads (tickets, audit, incidents) go through the MCP tools, like the agent does;
  * "run a ticket" starts Graph A; a paused approval is stored here and answered with a second request;
  * "run incident detection" runs Graph B.
Layout:  main.py (app + startup)  state.py (shared objects)  schemas.py (request/response shapes)
         routers/ (one file per area: config, tickets, approvals, incidents, admin)
Run:     uvicorn api.main:app --reload --port 8000      (from the app/ folder)
"""
