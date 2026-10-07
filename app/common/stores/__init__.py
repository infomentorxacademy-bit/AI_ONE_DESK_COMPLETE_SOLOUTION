"""common/stores/ : READ-ONLY readers for files in data/ (policies, metrics, logs, runbooks).

Each store has an allow-list so raw user text can never become a file path (NFR-03), and
data/internal/ is deliberately not reachable from any store (NFR-02).
"""
