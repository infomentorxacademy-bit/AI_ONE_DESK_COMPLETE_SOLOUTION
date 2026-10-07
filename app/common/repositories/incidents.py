"""common/repositories/incidents.py : SQL for incidents, their ticket links, deployments and rollback proposals.

USED BY servers/ops_server.py only (the platform team's server).
"""
from __future__ import annotations

import sqlite3
from typing import Any

from common.db import now_str, row_to_dict   # common/db.py: frozen timestamp, Row -> dict


# ----------------------------------------------------------------------------- deployments
def list_deployments(conn: sqlite3.Connection, service: str | None) -> list[dict[str, Any]]:
    """Deployments, newest first, optionally for one service."""
    if service:
        rows = conn.execute("SELECT * FROM deployments WHERE service = ? ORDER BY at DESC", (service,))
    else:
        rows = conn.execute("SELECT * FROM deployments ORDER BY at DESC")
    return [dict(r) for r in rows.fetchall()]


def get_deployment(conn: sqlite3.Connection, deployment_id: str) -> dict[str, Any] | None:
    """One deployment or None."""
    return row_to_dict(conn.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,)).fetchone())


# ----------------------------------------------------------------------------- incidents
def list_incidents(conn: sqlite3.Connection, status: str | None) -> list[dict[str, Any]]:
    """Incidents with `ticket_count` (number of linked tickets), optionally filtered by status."""
    sql = ("SELECT i.id, i.service, i.severity, i.status, i.opened, i.title, "
           "(SELECT COUNT(*) FROM incident_tickets it WHERE it.incident_id = i.id) AS ticket_count FROM incidents i")
    if status:
        rows = conn.execute(sql + " WHERE i.status = ? ORDER BY i.id", (status,))
    else:
        rows = conn.execute(sql + " ORDER BY i.id")
    return [dict(r) for r in rows.fetchall()]


def get_incident(conn: sqlite3.Connection, incident_id: str) -> dict[str, Any] | None:
    """One incident including `ticket_ids` (the linked tickets), or None."""
    incident = row_to_dict(conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone())
    if incident is None:
        return None
    incident["ticket_ids"] = [r[0] for r in conn.execute(
        "SELECT ticket_id FROM incident_tickets WHERE incident_id = ? ORDER BY ticket_id", (incident_id,))]
    return incident


def link_ticket(conn: sqlite3.Connection, incident_id: str, ticket_id: str) -> bool:
    """Link a ticket to an incident. Returns True if NEW, False if it was already linked (idempotent)."""
    cursor = conn.execute("INSERT OR IGNORE INTO incident_tickets (incident_id, ticket_id) VALUES (?, ?)",
                          (incident_id, ticket_id))
    return cursor.rowcount == 1


# ----------------------------------------------------------------------------- rollback proposals
def get_proposal_for_deployment(conn: sqlite3.Connection, deployment_id: str) -> dict[str, Any] | None:
    """The existing proposal for a deployment, or None (so a second request returns the same one)."""
    return row_to_dict(conn.execute(
        "SELECT * FROM rollback_proposals WHERE deployment_id = ?", (deployment_id,)).fetchone())


def create_proposal(conn: sqlite3.Connection, deployment_id: str, evidence: str) -> dict[str, Any]:
    """Record a rollback PROPOSAL (status 'awaiting_approval'). Nothing is executed - ever (G8)."""
    n = (conn.execute("SELECT COUNT(*) FROM rollback_proposals").fetchone()[0]) + 1
    proposal_id = f"RB-{n:03d}"
    conn.execute(
        "INSERT INTO rollback_proposals (id, deployment_id, created_at, status, evidence) "
        "VALUES (?, ?, ?, 'awaiting_approval', ?)", (proposal_id, deployment_id, now_str(), evidence))
    return row_to_dict(conn.execute("SELECT * FROM rollback_proposals WHERE id = ?", (proposal_id,)).fetchone())  # type: ignore[return-value]


def list_proposals(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """All rollback proposals, oldest first."""
    return [dict(r) for r in conn.execute("SELECT * FROM rollback_proposals ORDER BY id").fetchall()]
