"""agent/llm/base.py : the interface (contract) every LLM backend must follow.

WHAT   LLMClient: a Protocol with exactly two methods, classify() and draft(), plus a `usage` counter.
WHY    The graphs only know this interface, so we can swap FakeLLM / OpenAI / Groq with one setting
       and the graph code never changes (the "LLM seam", section 13.6). NFR-16 limits us to at most
       two LLM calls per ticket: one classify + one draft.
USED BY agent/llm/fake.py, agent/llm/real.py, agent/llm/factory.py, agent/nodes/*
"""
from __future__ import annotations

from typing import Any, Protocol   # standard library typing: Protocol = "anything with these methods"

# The six ticket kinds the classifier may return.
KINDS = ("status", "refund", "policy", "privacy", "injection", "incident_report")


class LLMClient(Protocol):
    """What the graphs expect from an LLM backend."""

    name: str                       # e.g. "fake", "openai:gpt-4o-mini", "groq:llama-3.3-70b-versatile"
    usage: dict[str, int]           # running totals: {"calls": n, "prompt_tokens": n, "completion_tokens": n}

    def classify(self, ticket: dict[str, Any]) -> dict[str, Any]:
        """Return {"kind": one of KINDS, "flags": [...], "service": "payments-api" (incident tickets only)}."""
        ...

    def draft(self, template: str, facts: dict[str, Any]) -> str:
        """Return the customer-facing text for `template` filled with the SAFE `facts`."""
        ...
