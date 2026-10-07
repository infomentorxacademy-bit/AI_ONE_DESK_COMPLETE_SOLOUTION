"""tests/test_db.py : is the given database correct? (3 tests)"""
from common.db import get_conn, now, today   # common/db.py: DB connection and the frozen clock


def test_row_counts():
    expected = {"customers": 26, "orders": 32, "refunds": 1, "tickets": 26, "approvers": 3,
                "deployments": 3, "incidents": 2, "incident_tickets": 0, "rollback_proposals": 0, "audit_log": 1}
    with get_conn() as conn:
        for table, count in expected.items():
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == count, table


def test_key_facts_and_foreign_keys():
    with get_conn() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        names = [r[0] for r in conn.execute("SELECT name FROM customers WHERE id IN ('C001','C011')")]
        assert names == ["Asha Rao", "Asha Rao"]                                   # ambiguous name (S11)
        assert conn.execute("SELECT fraud_flag FROM customers WHERE id='C012'").fetchone()[0] == 1
        assert conn.execute("SELECT amount, status FROM refunds WHERE id='R9001'").fetchone()[:] == (399, "completed")
        t11 = conn.execute("SELECT customer_id FROM tickets WHERE id='T11'").fetchone()[0]
        assert t11 is None                                                          # T11 has no customer
        assert conn.execute("SELECT COUNT(*) FROM tickets WHERE status != 'new'").fetchone()[0] == 0


def test_frozen_clock():
    assert today().isoformat() == "2026-10-07"
    assert now().strftime("%H:%M") == "14:30"
