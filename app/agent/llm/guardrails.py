"""agent/llm/guardrails.py : safety checks done by plain CODE around the LLM (the model is never trusted alone).

WHAT   is_injection(text): does a ticket try to give the AI new orders ("ignore your rules ...")?
WHY    Ground rules G1/G3: a model can be fooled by a clever ticket, code cannot. RealLLM.classify()
       applies this check ON TOP of the model's answer, so an injection is always flagged (scenario S6).
       This is NOT a language model; it is a fixed pattern check.
USED BY agent/llm/real.py
"""
from __future__ import annotations

import re   # standard library: pattern matching on ticket text

_INJECTION = re.compile(
    r"ignore (all |any )?(your |the |previous |prior )?(rules|instructions|policy|policies)"
    r"|disregard .{0,30}(rules|instructions)|system prompt|you are now|override (the )?(rules|policy)"
    r"|act as (an? )?(admin|manager)", re.I)


def is_injection(text: str) -> bool:
    """True if the text looks like it is trying to give the AI new orders."""
    return bool(_INJECTION.search(text))
