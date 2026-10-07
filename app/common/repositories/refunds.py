"""common/repositories/refunds.py : SQL for the `refunds` table.

USED BY servers/orders_server.py (get_refund_for_order, issue_refund)
"""
from __future__ import annotations

import json                       # standard library: approvals are stored as JSON text
import sqlite3
from typing import Any


def _hydrate(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Row -> dict, turning the JSON `approvals` text back into a Python list."""
    if row is None:
        return None
    refund = dict(row)
    refund["approvals"] = json.loads(refund["approvals"] or "[]")
    return refund


def get_for_order(conn: sqlite3.Connection, order_id: str) -> dict[str, Any] | None:
    """The refund for an order, or None (rule R4: at most one per order)."""
    return _hydrate(conn.execute("SELECT * FROM refunds WHERE order_id = ?", (order_id,)).fetchone())


def get_by_key(conn: sqlite3.Connection, idempotency_key: str) -> dict[str, Any] | None:
    """The refund created with this idempotency key, or None (rule R10)."""
    return _hydrate(conn.execute("SELECT * FROM refunds WHERE idempotency_key = ?", (idempotency_key,)).fetchone())


def next_id(conn: sqlite3.Connection) -> str:
    """Next refund id: 'R' + (highest number + 1). The seed has R9001, so the first new one is R9002."""
    highest = conn.execute("SELECT MAX(CAST(SUBSTR(id, 2) AS INTEGER)) FROM refunds").fetchone()[0] or 9000
    return f"R{highest + 1}"


def insert(conn: sqlite3.Connection, *, order_id: str, amount: int, reason: str, status: str,
           created_on: str, idempotency_key: str, approvals: list[dict]) -> dict[str, Any]:
    """Insert a refund row and return it."""
    refund_id = next_id(conn)
    conn.execute(
        "INSERT INTO refunds (id, order_id, amount, reason, status, created_on, idempotency_key, approvals) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (refund_id, order_id, amount, reason, status, created_on, idempotency_key, json.dumps(approvals)),
    )
    return get_by_key(conn, idempotency_key)  # type: ignore[return-value]
