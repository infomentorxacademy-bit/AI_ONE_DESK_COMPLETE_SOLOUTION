"""common/masking.py : hide personal data (PII) INSIDE the server (ground rule G4, NFR-04).

WHAT   mask_email() and mask_phone().
WHY    The agent must never see raw email/phone, because once raw PII crosses
       the wire it can leak into replies or logs. We mask before returning.
USED BY servers/orders_server.py (find_customer, get_customer)
"""
from __future__ import annotations


def mask_email(email: str) -> str:
    """'asha1@example.com' -> 'a***@example.com' (first letter, three stars, full domain)."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def mask_phone(phone: str) -> str:
    """'+91-98001-43037' -> '+91-*****-***37' (country code kept, only the last 2 digits shown)."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"+91-*****-***{digits[-2:]}"
