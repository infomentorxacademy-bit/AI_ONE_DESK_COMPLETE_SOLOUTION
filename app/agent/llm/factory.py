"""agent/llm/factory.py : choose which LLM to use. There is no default and no offline fake: you must pick one.

HOW    export LLM_PROVIDER=openai   and OPENAI_API_KEY=...
       export LLM_PROVIDER=groq     and GROQ_API_KEY=...        (Groq Cloud, not xAI Grok)
       or pass  python run_queue.py --llm openai|groq   (run_queue also asks you if neither is given)
USED BY run_queue.py, tests
"""
from __future__ import annotations

from agent.llm.base import LLMClient          # agent/llm/base.py: the interface type returned
from agent.llm.real import PROVIDERS, RealLLM # agent/llm/real.py: the OpenAI / Groq backend + provider table
from common.config import llm_provider        # common/config.py: reads LLM_PROVIDER from the environment


def get_llm(provider: str | None = None) -> LLMClient:
    """Return the LLM backend for `provider` (or LLM_PROVIDER). Raises a clear error if none was chosen."""
    choice = (provider or llm_provider()).lower()
    if not choice:
        raise RuntimeError(f"No LLM chosen. Set LLM_PROVIDER in app/.env or use --llm. Options: {', '.join(PROVIDERS)}")
    return RealLLM(choice)                    # raises a clear error for unknown names or a missing API key
