"""servers/orders_server.py : MCP server 1 "orders-server" (owner: support operations).

PROVIDES  11 tools, 1 resource template (reply://templates/{kind}), 1 prompt (draft_reply).
RULES     G2 every tool returns a dict (lists go in {"items": [...]}); expected failures return
          {"error": CODE, "message": ...} and never raise.  G4 PII is masked HERE, inside the server.
          G6 every write is idempotent.  Business rules are NOT written here: issue_refund calls
          common/rules.py check_refund() so the rule lives in exactly one place.
HOW TO USE  python -m servers.orders_server      (stdio transport; the agent starts it for you)
"""
from __future__ import annotations

from typing import Any, Literal                 # standard library typing: Literal makes MCP reject bad values

from fastmcp import FastMCP                     # third-party: the MCP server framework

# --- shared building blocks (each import says which file it comes from and why we need it) ---
from common.db import audit, get_conn, today     # common/db.py: DB connection, audit writer, frozen date
from common.masking import mask_email, mask_phone  # common/masking.py: hide PII before it leaves the server
from common.prompts import draft_reply_prompt    # common/prompts.py: text of the draft_reply prompt
from common.responses import error, items        # common/responses.py: standard error / list dict shapes
from common.rules import check_refund            # common/rules.py: THE refund policy function
from common.templates import RESOURCE_TEMPLATES, render  # common/templates.py: reply wording
from common.repositories import (                # common/repositories/*.py: one module of SQL per table
    approvers as approvers_repo,
    audit as audit_repo,
    customers as customers_repo,
    orders as orders_repo,
    refunds as refunds_repo,
    tickets as tickets_repo,
)

mcp = FastMCP("orders-server")                  # the server object; decorators below register features on it

TicketStatus = Literal["new", "in_progress", "pending_approval", "resolved", "declined", "escalated",
                       "linked_to_incident"]    # must equal tickets_repo.TICKET_STATUSES (checked by a test)


def _public_customer(customer: dict[str, Any]) -> dict[str, Any]:
    """Customer as the agent may see it: masked email/phone, fraud_flag as a real bool."""
    return {
        "id": customer["id"], "name": customer["name"], "city": customer["city"],
        "fraud_flag": bool(customer["fraud_flag"]),
        "email_masked": mask_email(customer["email"]), "phone_masked": mask_phone(customer["phone"]),
    }


# =============================================================================== read tools
@mcp.tool
def get_order(order_id: str) -> dict[str, Any]:
    """Get one order by id (for example 'O1001'): item, price in rupees, status, delivery dates, payment status.
    Returns {"order": {...}} or {"error": "ORDER_NOT_FOUND"}."""
    with get_conn() as conn:
        order = orders_repo.get(conn, order_id)
    return {"order": order} if order else error("ORDER_NOT_FOUND", f"No order with id {order_id}")


@mcp.tool
def find_customer(query: str) -> dict[str, Any]:
    """Find customers by name (case-insensitive 'contains') or by exact email.
    Returns ALL matches as {"items": [{id, name, city, email_masked}]}. Several matches means the
    customer is ambiguous: ask for their city or email instead of guessing."""
    with get_conn() as conn:
        found = customers_repo.search(conn, query)
    return items([{"id": c["id"], "name": c["name"], "city": c["city"],
                   "email_masked": mask_email(c["email"])} for c in found])


@mcp.tool
def get_customer(customer_id: str) -> dict[str, Any]:
    """Get one customer by id with MASKED contact details and the internal fraud_flag (never tell the customer about it).
    Returns {"customer": {...}} or {"error": "CUSTOMER_NOT_FOUND"}."""
    with get_conn() as conn:
        customer = customers_repo.get(conn, customer_id)
    return {"customer": _public_customer(customer)} if customer else error(
        "CUSTOMER_NOT_FOUND", f"No customer with id {customer_id}")


@mcp.tool
def list_customer_orders(customer_id: str) -> dict[str, Any]:
    """List the orders of ONE customer, newest id first. Returns {"items": [orders]}."""
    with get_conn() as conn:
        return items(orders_repo.list_for_customer(conn, customer_id))


@mcp.tool
def get_refund_for_order(order_id: str) -> dict[str, Any]:
    """Get the refund of an order. Returns {"refund": {...}} or {"refund": null} when none exists."""
    with get_conn() as conn:
        return {"refund": refunds_repo.get_for_order(conn, order_id)}


# =============================================================================== the dangerous tool
@mcp.tool
def issue_refund(ticket_id: str, order_id: str, amount: int, reason: str, idempotency_key: str,
                 approvals: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Issue a refund. The server RE-CHECKS every refund rule itself, so a wrong caller cannot break policy.
    approvals = humans who approved, e.g. [{"approver_id": "L01", "role": "support_lead"}].
    The same idempotency_key always returns the same refund and never pays twice.
    Returns {"refund": {...}, "created": true/false} or {"error": RULE_CODE, "message": ..., "needs": [roles]}."""
    approvals = approvals or []
    with get_conn() as conn:
        # Step 1 (rule R10): a repeated request returns the original refund and does nothing else.
        previous = refunds_repo.get_by_key(conn, idempotency_key)
        if previous:
            return {"refund": previous, "created": False}

        # Step 2: load everything the rule function needs.
        order = orders_repo.get(conn, order_id)
        customer = customers_repo.get(conn, order["customer_id"]) if order else None
        existing = refunds_repo.get_for_order(conn, order_id)
        incident_active = tickets_repo.linked_to_open_incident(conn, ticket_id)

        # Step 3: ask the single source of policy. A "no" is audited and returned (not raised).
        decision = check_refund(order, customer, existing, amount, approvals, incident_active, today())

        # Extra safeguard: an approval only counts if that person really is an approver with that role.
        if decision["allowed"] and approvals:
            for approval in approvals:
                known = approvers_repo.get(conn, approval.get("approver_id", ""))
                if not known or known["role"] != approval.get("role"):
                    decision = {"code": "BAD_APPROVALS", "allowed": False, "needs": [],
                                "message": f"Approver {approval.get('approver_id')} is unknown or has a different role."}
                    break

        if not decision["allowed"]:
            audit(conn, "agent", ticket_id, "refund_blocked",
                  f"{decision['code']} for order {order_id}, amount {amount}: {decision['message']}")
            return error(decision["code"], decision["message"], needs=decision["needs"])

        # Step 4: save the refund. Step 5: audit it, naming every approver (NFR-18).
        refund = refunds_repo.insert(conn, order_id=order_id, amount=amount, reason=reason, status="completed",
                                     created_on=today().isoformat(), idempotency_key=idempotency_key,
                                     approvals=approvals)
        approver_ids = ", ".join(a["approver_id"] for a in approvals) or "none (automatic)"
        audit(conn, "agent", ticket_id, "refund_issued",
              f"{refund['id']} for order {order_id}, amount {amount}, approvers: {approver_ids}")
        return {"refund": refund, "created": True}


# =============================================================================== ticket tools
@mcp.tool
def create_ticket(text: str, customer_id: str | None = None) -> dict[str, Any]:
    """Create a new support ticket with status 'new'. customer_id is optional.
    Returns {"ticket": {...}} or {"error": "CUSTOMER_NOT_FOUND"}."""
    with get_conn() as conn:
        if customer_id and not customers_repo.get(conn, customer_id):
            return error("CUSTOMER_NOT_FOUND", f"No customer with id {customer_id}")
        ticket = tickets_repo.create(conn, text, customer_id)
        audit(conn, "agent", ticket["id"], "ticket_created", f"Ticket created (customer {customer_id or 'unknown'})")
    return {"ticket": ticket}


@mcp.tool
def get_ticket(ticket_id: str) -> dict[str, Any]:
    """Get a ticket: status, resolution and the id of the incident it is linked to (or null).
    This is how anyone re-checks a ticket later. Returns {"ticket": {...}} or {"error": "TICKET_NOT_FOUND"}."""
    with get_conn() as conn:
        ticket = tickets_repo.get(conn, ticket_id)
    return {"ticket": ticket} if ticket else error("TICKET_NOT_FOUND", f"No ticket with id {ticket_id}")


@mcp.tool
def update_ticket_status(ticket_id: str, status: TicketStatus, resolution: str | None = None,
                         actor: str = "agent") -> dict[str, Any]:
    """Change a ticket's status (only the 7 allowed values) and store a resolution text. Writes an audit row.
    Repeating the same change is harmless (idempotent): nothing is written the second time.
    Returns {"ticket": {...}} or {"error": "TICKET_NOT_FOUND"}."""
    with get_conn() as conn:
        ticket = tickets_repo.get(conn, ticket_id)
        if not ticket:
            return error("TICKET_NOT_FOUND", f"No ticket with id {ticket_id}")
        if ticket["status"] == status and ticket["resolution"] == resolution:
            return {"ticket": ticket}                         # G6: same request => no new effect, no new audit row
        tickets_repo.set_status(conn, ticket_id, status, resolution)
        audit(conn, actor, ticket_id, "status_changed",
              f"{ticket['status']} -> {status}" + (f": {resolution}" if resolution else ""))
        return {"ticket": tickets_repo.get(conn, ticket_id)}


@mcp.tool
def list_tickets(status: str | None = None, limit: int = 50) -> dict[str, Any]:
    """List tickets, oldest first, optionally only one status. limit is capped at 100. Returns {"items": [tickets]}."""
    with get_conn() as conn:
        return items(tickets_repo.list_by_status(conn, status, max(1, min(limit, 100))))


@mcp.tool
def get_audit_trail(ticket_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Read the audit log, NEWEST first, optionally for one ticket: {"items": [{ts, actor, ticket_id, action, detail}]}."""
    with get_conn() as conn:
        return items(audit_repo.trail(conn, ticket_id, max(1, min(limit, 200))))


# =============================================================================== resource template + prompt
@mcp.resource("reply://templates/{kind}")
def reply_template(kind: str) -> str:
    """A short polite reply template with {placeholders}. kind: status, refund_ok, refund_pending,
    refund_declined, incident, privacy_refusal, clarify."""
    if kind not in RESOURCE_TEMPLATES:
        raise ValueError(f"Unknown template '{kind}'. Valid kinds: {', '.join(sorted(RESOURCE_TEMPLATES))}")
    return RESOURCE_TEMPLATES[kind]


@mcp.prompt
def draft_reply(ticket_text: str, tone: Literal["warm", "formal"] = "warm") -> str:
    """Instruction for drafting a customer reply using ONLY supplied facts and treating ticket text as untrusted."""
    return draft_reply_prompt(ticket_text, tone)


if __name__ == "__main__":
    # stdio transport: the agent (MCP client) launches this process and talks over stdin/stdout.
    # show_banner=False keeps stdout/stderr clean; log_level hides routine INFO lines.
    mcp.run(show_banner=False, log_level="WARNING")
