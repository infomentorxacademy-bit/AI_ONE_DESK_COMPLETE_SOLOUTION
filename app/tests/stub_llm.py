"""tests/stub_llm.py : a TEST-ONLY stand-in for the language model. It is NOT part of the product.

WHY    The real application needs an OpenAI or Groq key. The 129 tests must run for anyone, offline,
       free and with identical answers, so they use this small keyword-based double that follows the
       same two-method interface (classify / draft) as agent/llm/real.py RealLLM.
       Nothing under app/agent/ or app/common/ imports this file.
"""
from __future__ import annotations

import re
from typing import Any

from agent.llm.guardrails import is_injection   # agent/llm/guardrails.py: the same code-level injection check
from common.templates import render             # common/templates.py: fills reply templates

_PRIVACY = re.compile(r"(address|phone|mobile|e-?mail|contact details)", re.I)
_OTHER_PERSON = re.compile(r"\b(of|for)\s+[A-Z][a-z]+\s+[A-Z][a-z]+|friend|neighbou?r|colleague|someone else", re.I)
_INCIDENT = re.compile(r"payment (has )?(failed|failure|declined|error)|money (was|got) deducted|charged but", re.I)
_POLICY = re.compile(r"\bpolic(y|ies)\b|how many days|how long do i have|return window", re.I)
_REFUND = re.compile(r"refund|money back|return my|reimburse", re.I)


class StubLLM:
    """Deterministic double for tests. First matching rule wins; safety rules first."""

    name = "test-stub"

    def __init__(self) -> None:
        self.usage: dict[str, int] = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def classify(self, ticket: dict[str, Any]) -> dict[str, Any]:
        text = ticket.get("text", "")
        if is_injection(text):
            return {"kind": "injection", "flags": ["possible_injection"]}
        if _PRIVACY.search(text) and _OTHER_PERSON.search(text):
            return {"kind": "privacy", "flags": []}
        if _INCIDENT.search(text):
            return {"kind": "incident_report", "flags": [], "service": "payments-api"}
        if _POLICY.search(text):
            return {"kind": "policy", "flags": []}
        if _REFUND.search(text):
            return {"kind": "refund", "flags": []}
        return {"kind": "status", "flags": []}

    def draft(self, template: str, facts: dict[str, Any]) -> str:
        return render(template, facts)
