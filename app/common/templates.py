"""common/templates.py : customer reply wording (short, polite, each under 60 words).

WHAT   RESOURCE_TEMPLATES   the 7 templates served by the orders-server as reply://templates/{kind}
       INTERNAL_TEMPLATES   extra wording the agent needs (duplicate refund, policy answer...)
       render()             fills {placeholders}; a missing placeholder becomes "" instead of crashing
WHY    ONE copy of the wording, shared by the MCP server (so humans/other apps can read it) and by
       agent/llm/real.py (plain-template fallback). No wording is duplicated.
SAFETY None of these templates can contain a fraud flag, a phone number or another customer's data,
       because they only receive the safe `facts` built in agent/reply_facts.py.
USED BY servers/orders_server.py, agent/llm/real.py, agent/reply_facts.py
"""
from __future__ import annotations

from typing import Any

# The seven kinds required by section 10.3 of the requirements.
RESOURCE_TEMPLATES: dict[str, str] = {
    "status": (
        "Hello {name}, your order {order_id} ({item}) is currently {status}. {detail} "
        "Thank you for shopping with TechNova Retail."
    ),
    "refund_ok": (
        "Hello {name}, we have refunded Rs {amount} for order {order_id} ({item}). "
        "Your refund id is {refund_id}. The money reaches your original payment method in 5 to 7 working days."
    ),
    "refund_pending": (
        "Hello {name}, your refund request of Rs {amount} for order {order_id} is waiting for a team member's review. "
        "Nothing has been paid yet. We will update you as soon as there is a decision."
    ),
    "refund_declined": (
        "Hello {name}, we are sorry, but we cannot refund order {order_id} because {reason}. "
        "If you think this is a mistake, please reply and a team member will look again."
    ),
    "incident": (
        "Hello, we are sorry about the trouble with your payment{order_clause}. "
        "We found a problem on our side and our engineers are fixing it. You do not need to do anything. "
        "We will update you as soon as it is solved."
    ),
    "privacy_refusal": (
        "Hello, we are sorry, but we cannot share personal details of any customer, to keep everyone's data safe. "
        "We are happy to help with your own orders and account."
    ),
    "clarify": (
        "Hello, we found more than one account that could be yours. "
        "To help you safely, please tell us your city or the email address on your account."
    ),
}

# Extra wording used only inside the agent (not part of the 7 served kinds).
INTERNAL_TEMPLATES: dict[str, str] = {
    "refund_duplicate": (
        "Hello {name}, order {order_id} has already been refunded. "
        "Refund {refund_id} is {refund_status}. Each order can be refunded only once."
    ),
    "policy_answer": "Hello, here is our policy (section {section}): {text}",
    "injection_escalated": (
        "Hello, thank you for contacting us. We have passed your message to a specialist who will review it. "
        "No changes were made to any order."
    ),
    "order_not_found": (
        "Hello, we could not find order {order_id}. Please check the order id and reply, "
        "and a specialist will help you."
    ),
    # Graph B notes. engineer_note is technical; the customer message is RESOURCE_TEMPLATES["incident"].
    "engineer_note": (
        "INCIDENT NOTE - {incident_id} ({service})\n"
        "- {ticket_count} customer tickets about failed payments between {first_ticket_time} and {last_ticket_time}.\n"
        "- Error rate on {service} jumped from {baseline}% to {spike_value}% at {spike_time}.\n"
        "- {correlation}\n"
        "- {proposal}\n"
        "{log_warning}"
        "- No individual refunds were issued; all tickets are linked to {incident_id}."
    ),
}


class _SafeDict(dict):
    """dict that returns '' for any missing key, so str.format_map never raises KeyError."""

    def __missing__(self, key: str) -> str:
        return ""


def all_templates() -> dict[str, str]:
    """Every template (served + internal) in one dict; used by RealLLM."""
    return {**RESOURCE_TEMPLATES, **INTERNAL_TEMPLATES}


def render(kind: str, facts: dict[str, Any]) -> str:
    """Fill template `kind` with `facts`. Raises KeyError for an unknown kind."""
    templates = all_templates()
    if kind not in templates:
        raise KeyError(f"Unknown template '{kind}'. Valid kinds: {sorted(templates)}")
    return templates[kind].format_map(_SafeDict(facts)).strip()
