"""common/repositories/tickets.py : SQL for the `tickets` table.

USED BY servers/orders_server.py (ticket tools, issue_refund) and servers/ops_server.py (linking).
"""
from __future__ import annotations

import sqlite3
from typing import Any

# common/db.py -> now_str(): the frozen timestamp; row_to_dict(): Row -> dict.
from common.db import now_str, row_to_dict

# The only statuses a ticket may have (section 8.1). The same list is used by the server's Literal type.
TICKET_STATUSES = ("new", "in_progress", "pending_approval", "resolved", "declined", "escalated", "linked_to_incident")

# A ticket's incident id comes from the link table; a sub-select keeps the ticket row query simple.
_SELECT = ("SELECT t.*, (SELECT incident_id FROM incident_tickets it WHERE it.ticket_id = t.id "
           "ORDER BY incident_id LIMIT 1) AS incident_id FROM tickets t")


def get(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any] | None:
    """Return a ticket with its `incident_id` (or None inside the dict) - this is how anyone re-checks status later."""
    return row_to_dict(conn.execute(_SELECT + " WHERE t.id = ?", (ticket_id,)).fetchone())


def create(conn: sqlite3.Connection, text: str, customer_id: str | None) -> dict[str, Any]:
    """Insert a new ticket with status 'new'. Id = 'T' + (highest T-number + 1), so the first new one is T15."""
    highest = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 2) AS INTEGER)) FROM tickets WHERE id LIKE 'T%'").fetchone()[0] or 0
    ticket_id = f"T{highest + 1}"
    conn.execute(
        "INSERT INTO tickets (id, customer_id, text, created_at, status, resolution, updated_at) "
        "VALUES (?, ?, ?, ?, 'new', NULL, ?)",
        (ticket_id, customer_id, text, now_str(), now_str()),
    )
    return get(conn, ticket_id)  # type: ignore[return-value]


def set_status(conn: sqlite3.Connection, ticket_id: str, status: str, resolution: str | None) -> None:
    """Update status + resolution and refresh updated_at."""
    conn.execute("UPDATE tickets SET status = ?, resolution = ?, updated_at = ? WHERE id = ?",
                 (status, resolution, now_str(), ticket_id))


def list_by_status(conn: sqlite3.Connection, status: str | None, limit: int) -> list[dict[str, Any]]:
    """Tickets (oldest first), optionally filtered by status."""
    if status:
        rows = conn.execute(_SELECT + " WHERE t.status = ? ORDER BY t.created_at, t.id LIMIT ?", (status, limit))
    else:
        rows = conn.execute(_SELECT + " ORDER BY t.created_at, t.id LIMIT ?", (limit,))
    return [dict(r) for r in rows.fetchall()]


def linked_to_open_incident(conn: sqlite3.Connection, ticket_id: str) -> bool:
    """True when this ticket is linked to an incident whose status is 'open' (rule R9 input)."""
    row = conn.execute(
        "SELECT 1 FROM incident_tickets it JOIN incidents i ON i.id = it.incident_id "
        "WHERE it.ticket_id = ? AND i.status = 'open' LIMIT 1", (ticket_id,)).fetchone()
    return row is not None
