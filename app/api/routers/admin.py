"""api/routers/admin.py : audit log, approver list and (optional) demo reset.

GET  /api/audit?ticket_id=&limit=   audit trail, newest first
GET  /api/approvers                 who may approve (id, name, role) - reference data for the "acting as" menu
POST /api/admin/reset               rebuild opsdesk.db from the original data. DISABLED unless OPSDESK_ENABLE_RESET=1.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query   # fastapi: routing, dependencies, errors

import seed_db                                       # seed_db.py: rebuilds the database from the given data
from api.deps import get_state                       # api/deps.py: shared state dependency
from api.routers.config import reset_enabled         # api/routers/config.py: is reset switched on?
from api.state import AppState                       # api/state.py: shared objects
from common.db import get_conn                       # common/db.py: DB access (read-only reference data below)
from common.repositories import approvers as approvers_repo   # common/repositories/approvers.py: SQL for approvers

router = APIRouter(tags=["admin"])


@router.get("/audit")
async def audit_trail(ticket_id: str | None = None, limit: int = Query(50, ge=1, le=200),
                      state: AppState = Depends(get_state)) -> dict:
    """The audit log through the MCP tool."""
    return await state.belt.call("get_audit_trail", ticket_id=ticket_id, limit=limit)


@router.get("/approvers")
def list_approvers() -> dict:
    """Approver reference data (read-only). The server still verifies every approver when a refund is issued."""
    with get_conn() as conn:
        return {"items": approvers_repo.list_all(conn)}


@router.post("/admin/reset")
def reset_demo_data(state: AppState = Depends(get_state)) -> dict:
    """Reset the database to the original data and forget paused approvals (demo/testing only)."""
    if not reset_enabled():
        raise HTTPException(status_code=403, detail="Reset is disabled. Set OPSDESK_ENABLE_RESET=1 to allow it.")
    state.pending.clear()
    return {"counts": seed_db.main(quiet=True)}
