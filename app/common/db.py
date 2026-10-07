"""common/db.py : database access, the frozen clock and the audit writer.

WHAT   get_conn() opens SQLite, now()/today() give the frozen time, audit() writes
       one audit row, row_to_dict() converts a row into a plain dict.
WHY    One door to the database means foreign keys are always on and every
       module sees the same time. Always call now(); NEVER datetime.now() (G5).
USED BY common/repositories/*, seed_db.py, servers/*, agent/nodes/*, tests
"""
from __future__ import annotations

import sqlite3                              # standard library: the SQLite database driver
from contextlib import contextmanager       # standard library: lets get_conn() be used in a "with" block
from datetime import date, datetime         # standard library: date types for the clock helpers
from typing import Any, Iterator

# common/config.py -> FROZEN_NOW is the frozen clock value; db_path() tells us which file to open.
from common.config import FROZEN_NOW, db_path


def now() -> datetime:
    """Return the frozen current time (2026-10-07 14:30 IST). Use this instead of datetime.now()."""
    return FROZEN_NOW


def today() -> date:
    """Return the frozen current date (2026-10-07)."""
    return FROZEN_NOW.date()


def now_str() -> str:
    """Return the frozen time as 'YYYY-MM-DD HH:MM:SS', the format stored in the database."""
    return FROZEN_NOW.strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Open the database, yield the connection, then COMMIT and CLOSE it.

    If the block raises, everything done inside is rolled back, so a half-finished
    write can never be saved. Rows come back as sqlite3.Row (access by column name).
    """
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row           # columns readable by name
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores foreign keys unless this is set per connection
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert one database row to a dict (or None when there is no row)."""
    return dict(row) if row is not None else None


def audit(conn: sqlite3.Connection, actor: str, ticket_id: str | None, action: str, detail: str) -> None:
    """Write one audit_log row (NFR-13): who (actor) did what (action) to which ticket, and why (detail).

    It takes the caller's open connection so the audit row is saved in the SAME
    transaction as the change it describes: both happen or neither does.
    """
    conn.execute(
        "INSERT INTO audit_log (ts, actor, ticket_id, action, detail) VALUES (?, ?, ?, ?, ?)",
        (now_str(), actor, ticket_id, action, detail),
    )
