"""common/repositories/customers.py : SQL for the `customers` table.

USED BY servers/orders_server.py (find_customer, get_customer, issue_refund)
"""
from __future__ import annotations

import sqlite3
from typing import Any

# common/db.py -> converts a sqlite3.Row into a plain dict.
from common.db import row_to_dict


def get(conn: sqlite3.Connection, customer_id: str) -> dict[str, Any] | None:
    """Return one customer (raw row, includes email/phone: the SERVER masks it) or None."""
    return row_to_dict(conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone())


def search(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    """Find customers by name (case-insensitive 'contains') or by exact email. Returns ALL matches."""
    q = query.strip()
    like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"   # escape LIKE wildcards
    rows = conn.execute(
        "SELECT * FROM customers WHERE name LIKE ? ESCAPE '\\' OR lower(email) = lower(?) ORDER BY id",
        (like, q),
    ).fetchall()
    return [dict(r) for r in rows]
