-- =============================================================================
-- schema.sql : the 10 tables of opsdesk.db (requirements section 8).
-- WHO USES IT : seed_db.py runs this file to (re)create an empty database.
-- RULE        : do not change the schema; tools and tests rely on these names.
-- =============================================================================
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS rollback_proposals;
DROP TABLE IF EXISTS incident_tickets;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS deployments;
DROP TABLE IF EXISTS approvers;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS refunds;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

-- People who buy from TechNova. fraud_flag is INTERNAL: never shown to customers.
CREATE TABLE customers (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    phone       TEXT NOT NULL,
    city        TEXT NOT NULL,
    fraud_flag  INTEGER NOT NULL DEFAULT 0 CHECK (fraud_flag IN (0, 1))
);

-- What customers bought. price is a whole number of rupees.
CREATE TABLE orders (
    id             TEXT PRIMARY KEY,
    customer_id    TEXT NOT NULL REFERENCES customers(id),
    item           TEXT NOT NULL,
    price          INTEGER NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('placed', 'shipped', 'delivered', 'cancelled')),
    delivered_on   TEXT,            -- YYYY-MM-DD, only for delivered orders
    expected_on    TEXT,            -- YYYY-MM-DD, only for orders still on the way
    payment_status TEXT NOT NULL CHECK (payment_status IN ('paid', 'failed'))
);

-- Money given back. idempotency_key is UNIQUE so the same request never pays twice (rule R10).
CREATE TABLE refunds (
    id               TEXT PRIMARY KEY,
    order_id         TEXT NOT NULL REFERENCES orders(id),
    amount           INTEGER NOT NULL,
    reason           TEXT NOT NULL,
    status           TEXT NOT NULL,
    created_on       TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL UNIQUE,
    approvals        TEXT NOT NULL DEFAULT '[]'   -- JSON text: [{"approver_id": "L01", "role": "support_lead"}]
);

-- Support tickets. customer_id may be NULL (customer not identified yet).
CREATE TABLE tickets (
    id           TEXT PRIMARY KEY,
    customer_id  TEXT REFERENCES customers(id),
    text         TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'new' CHECK (status IN
                 ('new', 'in_progress', 'pending_approval', 'resolved', 'declined', 'escalated', 'linked_to_incident')),
    resolution   TEXT,
    updated_at   TEXT NOT NULL
);

-- Humans allowed to approve refunds. role is support_lead or finance.
CREATE TABLE approvers (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    role  TEXT NOT NULL CHECK (role IN ('support_lead', 'finance'))
);

-- Software releases of platform services (evidence for outage correlation).
CREATE TABLE deployments (
    id       TEXT PRIMARY KEY,
    service  TEXT NOT NULL,
    version  TEXT NOT NULL,
    at       TEXT NOT NULL,     -- 'YYYY-MM-DD HH:MM'
    author   TEXT NOT NULL
);

-- Platform incidents (outages).
CREATE TABLE incidents (
    id          TEXT PRIMARY KEY,
    service     TEXT NOT NULL,
    severity    TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
    opened      TEXT NOT NULL,
    title       TEXT NOT NULL,
    resolution  TEXT
);

-- Which tickets belong to which incident. The pair is unique => linking twice is harmless.
CREATE TABLE incident_tickets (
    incident_id  TEXT NOT NULL REFERENCES incidents(id),
    ticket_id    TEXT NOT NULL REFERENCES tickets(id),
    PRIMARY KEY (incident_id, ticket_id)
);

-- Rollbacks are only ever PROPOSED (ground rule G8). Nothing here executes anything.
CREATE TABLE rollback_proposals (
    id             TEXT PRIMARY KEY,
    deployment_id  TEXT NOT NULL REFERENCES deployments(id),
    created_at     TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'awaiting_approval',
    evidence       TEXT NOT NULL
);

-- One row per important event: who did what, to which ticket, and why (NFR-13).
CREATE TABLE audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    actor      TEXT NOT NULL,
    ticket_id  TEXT,
    action     TEXT NOT NULL,
    detail     TEXT NOT NULL
);
