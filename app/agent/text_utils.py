"""agent/text_utils.py : tiny helpers that pull facts out of ticket text.

WHY    Several nodes need the same patterns (order id, customer name). Keeping them here means the
       regular expressions exist exactly once.
USED BY agent/nodes/ticket/resolve_customer.py, fetch_order.py, incident_reply.py
NOTE   These only EXTRACT ids; they never decide anything. Ids are always verified against the servers.
"""
from __future__ import annotations

import re

ORDER_ID = re.compile(r"\bO\d{4}\b")                                  # e.g. O1003
SELF_NAME = re.compile(r"\bI(?: am|'m)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)")   # "I am Asha Rao"


def find_order_id(text: str) -> str | None:
    """First order id (letter O + 4 digits) in the text, or None."""
    match = ORDER_ID.search(text)
    return match.group(0) if match else None


def find_self_name(text: str) -> str | None:
    """The name a customer gives with 'I am First Last', or None."""
    match = SELF_NAME.search(text)
    return match.group(1) if match else None
