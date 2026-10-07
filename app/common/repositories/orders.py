"""common/repositories/orders.py : SQL for the `orders` table.

USED BY servers/orders_server.py (get_order, list_customer_orders, issue_refund)
"""
from __future__ import annotations

import sqlite3
from typing import Any

from common.db import row_to_dict   # common/db.py: sqlite3.Row -> dict


def get(conn: sqlite3.Connection, order_id: str) -> dict[str, Any] | None:
    """Return one order (all columns) or None."""
    return row_to_dict(conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone())


def list_for_customer(conn: sqlite3.Connection, customer_id: str) -> list[dict[str, Any]]:
    """Orders that belong to ONE customer, newest id first (never another customer's orders)."""
    rows = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC", (customer_id,)).fetchall()
    return [dict(r) for r in rows]
