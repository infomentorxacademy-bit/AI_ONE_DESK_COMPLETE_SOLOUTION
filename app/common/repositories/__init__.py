"""common/repositories/ : one small module per database table (the "data access layer").

Each function receives an OPEN sqlite3 connection as its first argument. That lets a
server tool do several steps (check, insert refund, write audit row) in ONE transaction.
Repositories contain SQL only: no business rules (those are in common/rules.py) and no
masking (that is done by the servers).
"""
