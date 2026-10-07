"""common/repositories/audit.py : READ side of the audit log (the WRITE side is common/db.py audit()).

USED BY servers/orders_server.py get_audit_trail, tests
"""
from __future__ import annotations

import sqlite3
from typing import Any


def trail(conn: sqlite3.Connection, ticket_id: str | None, limit: int) -> list[dict[str, Any]]:
    """Audit events, NEWEST first, optionally for one ticket. Columns: ts, actor, ticket_id, action, detail."""
    cols = "ts, actor, ticket_id, action, detail"
    if ticket_id:
        rows = conn.execute(f"SELECT {cols} FROM audit_log WHERE ticket_id = ? ORDER BY id DESC LIMIT ?",
                            (ticket_id, limit))
    else:
        rows = conn.execute(f"SELECT {cols} FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(r) for r in rows.fetchall()]
