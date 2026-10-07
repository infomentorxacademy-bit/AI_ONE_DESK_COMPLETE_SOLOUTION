"""common/rules.py : check_refund(), the SINGLE source of refund policy (requirements section 9).

WHAT   One pure-Python function that decides whether a refund is allowed, and
       if not, why and which approver roles are still missing.
WHY    Ground rule G1: the LLM may read, classify and draft, but it may NEVER
       decide an amount limit, an approver or a policy date. Those live here,
       so a clever ticket cannot talk the code into breaking a rule (NFR-08).
CALLED BY (1) agent/nodes/ticket/check_rules.py  - to decide what to do next
          (2) servers/orders_server.py issue_refund - to ENFORCE the rules even
              if the agent is wrong (defence in depth).
PURE   No database, no network, no LLM. Same input => same output, always.

THE TEN BUSINESS RULES
  R1 only delivered orders       R6 2,001..25,000 needs one support lead
  R2 within 30 days of delivery  R7 above 25,000 needs lead AND finance (two people)
  R3 never above price, never <=0 R8 fraud-flag customer needs a lead at ANY amount
  R4 one refund per order        R9 ticket linked to an open incident: no refund
  R5 <= 2,000 is automatic       R10 same idempotency key never pays twice (see issue_refund)

THE ORDER OF CHECKS (first match wins) - the order matters, see section 9.2:
  1 NOT_DELIVERED  2 ALREADY_REFUNDED  3 LATE  4 OVER_PRICE  5 INCIDENT_ACTIVE
  6 BAD_APPROVALS  7 NEEDS_LEAD / NEEDS_FINANCE / NEEDS_LEAD_AND_FINANCE
  8 OK_AUTO        9 OK_APPROVED
"""
from __future__ import annotations

from datetime import date, datetime        # standard library: date arithmetic for the 30-day window
from typing import Any

# common/db.py -> today(): the frozen date, used when the caller does not pass `today`.
from common.db import today as frozen_today

# ---- policy constants (policy refs: 2.1, 3.1, 3.2, 3.3) -------------------------------------
REFUND_WINDOW_DAYS = 30        # policy 2.1/2.2: day 30 is OK, day 31 is late
AUTO_LIMIT = 2000              # policy 3.1: up to and including Rs 2,000 is automatic
LEAD_LIMIT = 25000             # policy 3.2/3.3: up to and including Rs 25,000 needs ONE lead
ROLE_LEAD = "support_lead"
ROLE_FINANCE = "finance"
VALID_ROLES = {ROLE_LEAD, ROLE_FINANCE}


def _result(code: str, allowed: bool, message: str, needs: list[str] | None = None,
            flags: list[str] | None = None) -> dict[str, Any]:
    """Build the standard return dict so every branch returns the same shape."""
    return {"code": code, "allowed": allowed, "needs": needs or [], "message": message, "flags": flags or []}


def _as_date(value: Any) -> date:
    """Accept a date, a datetime or an ISO 'YYYY-MM-DD' string and return a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def check_refund(
    order: dict | None,
    customer: dict | None,
    existing_refund: dict | None,
    amount: int,
    approvals: list[dict] | None,
    incident_active: bool = False,
    today: Any = None,
) -> dict[str, Any]:
    """Decide a refund. Returns {"code", "allowed", "needs", "message", "flags"}.

    order            order row as a dict (None if the order does not exist)
    customer         customer row as a dict (only `fraud_flag` is used)
    existing_refund  refund row for this order, or None
    amount           requested refund in whole rupees
    approvals        humans who already approved: [{"approver_id": "L01", "role": "support_lead"}]
    incident_active  True when the ticket is linked to an OPEN incident (rule R9)
    today            override for tests; defaults to the frozen date
    """
    approvals = approvals or []
    today_date = _as_date(today) if today is not None else frozen_today()
    fraud = bool(customer and customer.get("fraud_flag"))
    flags = ["fraud_flag"] if fraud else []

    # 1. R1 - only delivered orders (checked FIRST: a shipped order must say NOT_DELIVERED even for Rs 5).
    if not order or order.get("status") != "delivered" or not order.get("delivered_on"):
        return _result("NOT_DELIVERED", False, "Only delivered orders can be refunded (policy 1.1).", flags=flags)

    # 2. R4 - one refund per order (before LATE: an old duplicate must say ALREADY_REFUNDED).
    if existing_refund is not None:
        return _result("ALREADY_REFUNDED", False,
                       f"Order {order['id']} already has refund {existing_refund['id']} (policy 4.1).", flags=flags)

    # 3. R2 - 30 day window. Day 30 passes, day 31 fails.
    days = (today_date - _as_date(order["delivered_on"])).days
    if days > REFUND_WINDOW_DAYS:
        return _result("LATE", False,
                       f"Delivered {days} days ago; the refund window is {REFUND_WINDOW_DAYS} days (policy 2.1).",
                       flags=flags)

    # 4. R3 - never above the price, never zero or negative.
    if amount <= 0 or amount > order["price"]:
        return _result("OVER_PRICE", False,
                       f"Amount {amount} must be above 0 and at most the order price {order['price']} (policy 3.4).",
                       flags=flags)

    # 5. R9 - the ticket belongs to an open incident: no individual refunds.
    if incident_active:
        return _result("INCIDENT_ACTIVE", False,
                       "Ticket is linked to an open incident; no individual refund (policy 6.1).", flags=flags)

    # 6. Approval hygiene: the same person twice, or an unknown role, is never accepted.
    ids = [a.get("approver_id") for a in approvals]
    if len(ids) != len(set(ids)) or any(a.get("role") not in VALID_ROLES for a in approvals):
        return _result("BAD_APPROVALS", False,
                       "The same approver appears twice, or a role is invalid. Two different people are needed.",
                       flags=flags)

    # 7. R5/R6/R7/R8 - which roles are REQUIRED for this amount, and which are still MISSING?
    if amount > LEAD_LIMIT:
        required = [ROLE_LEAD, ROLE_FINANCE]                     # R7
    elif amount > AUTO_LIMIT or fraud:
        required = [ROLE_LEAD]                                   # R6 and R8
    else:
        required = []                                            # R5
    present = {a["role"] for a in approvals}
    missing = [role for role in required if role not in present]
    if missing:
        code = ("NEEDS_LEAD_AND_FINANCE" if len(missing) == 2
                else "NEEDS_LEAD" if missing == [ROLE_LEAD] else "NEEDS_FINANCE")
        return _result(code, False, f"Approval still needed from: {', '.join(missing)}.", needs=missing, flags=flags)

    # 8 / 9. Nothing missing: automatic if nothing was required, otherwise approved by humans.
    if not required:
        return _result("OK_AUTO", True, f"Rs {amount} is within the automatic limit (policy 3.1).", flags=flags)
    return _result("OK_APPROVED", True, "All required approvals are present.", flags=flags)
