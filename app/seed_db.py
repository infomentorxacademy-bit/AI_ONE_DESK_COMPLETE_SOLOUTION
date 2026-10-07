"""seed_db.py : create or RESET opsdesk.db from schema.sql + data/standard_data.json.

Run it any time you want a clean start:   python seed_db.py
WHY    Tests, the demo and a fresh clone all need identical data. Never edit
       data/standard_data.json; re-run this script instead.
"""
from __future__ import annotations

import json                                  # standard library: read standard_data.json
import sqlite3                               # standard library: SQLite driver

# common/config.py -> where the schema file, data folder and database file live.
from common.config import DATA_DIR, SCHEMA_FILE, db_path
# common/db.py -> get_conn opens the DB; audit writes the first audit row.
from common.db import audit, get_conn

# Order matters: parents must be inserted before rows that point to them (foreign keys).
_TABLES = ["customers", "orders", "refunds", "tickets", "approvers", "deployments", "incidents"]


def _insert(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    """Insert a list of dicts into `table`; the dict keys are the column names."""
    for row in rows:
        cols = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))


def main(quiet: bool = False) -> dict[str, int]:
    """Rebuild the database and return {table: row_count}. `quiet` suppresses printing (used by run_queue/tests)."""
    db_path().parent.mkdir(parents=True, exist_ok=True)
    data = json.loads((DATA_DIR / "standard_data.json").read_text(encoding="utf-8"))
    with get_conn() as conn:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))  # drops + recreates the 10 tables
        for table in _TABLES:
            _insert(conn, table, data[table])
        audit(conn, "system", None, "seed", "Database created from standard_data.json")
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in _TABLES + ["incident_tickets", "rollback_proposals", "audit_log"]}
    if not quiet:
        print("Table row counts:")
        for table, n in counts.items():
            print(f"  {table:<20}{n}")
        print("Setup done")
    return counts


if __name__ == "__main__":
    main()
