"""agent/llm/factory.py : choose the LLM backend from configuration (the single switch).

HOW    export LLM_PROVIDER=fake     (default: offline, free)
       export LLM_PROVIDER=openai   and OPENAI_API_KEY=...
       export LLM_PROVIDER=groq     and GROQ_API_KEY=...        (Groq Cloud, not xAI Grok)
       (legacy: USE_REAL_LLM=1 means openai)   run_queue.py also accepts  --llm fake|openai|groq
USED BY run_queue.py, tests
"""
from __future__ import annotations

from agent.llm.base import LLMClient          # agent/llm/base.py: the interface type returned
from agent.llm.fake import FakeLLM            # agent/llm/fake.py: offline backend
from agent.llm.real import RealLLM            # agent/llm/real.py: OpenAI / Groq backend
from common.config import llm_provider        # common/config.py: reads LLM_PROVIDER / USE_REAL_LLM


def get_llm(provider: str | None = None) -> LLMClient:
    """Return the LLM backend. `provider` overrides the environment (used by the --llm flag)."""
    choice = (provider or llm_provider()).lower()
    if choice == "fake":
        return FakeLLM()
    return RealLLM(choice)                    # raises a clear error for unknown names or a missing API key
