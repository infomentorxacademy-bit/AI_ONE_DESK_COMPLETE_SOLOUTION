"""common/repositories/approvers.py : SQL for the `approvers` table (the humans who may approve refunds).

USED BY servers/orders_server.py issue_refund - to prove an approver really exists with that role.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from common.db import row_to_dict   # common/db.py: sqlite3.Row -> dict


def get(conn: sqlite3.Connection, approver_id: str) -> dict[str, Any] | None:
    """Return {id, name, role} or None."""
    return row_to_dict(conn.execute("SELECT * FROM approvers WHERE id = ?", (approver_id,)).fetchone())


def list_all(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every approver, so the web UI can offer a "who is approving?" choice. Reference data only."""
    return [dict(r) for r in conn.execute("SELECT * FROM approvers ORDER BY id").fetchall()]
