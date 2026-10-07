"""agent/llm/ : the LLM seam. The graphs only use get_llm() and the two methods classify()/draft().

  base.py        the interface              real.py       OpenAI + Groq backend (PROVIDERS table = the models)
  guardrails.py  code-level safety checks   factory.py    chooses OpenAI or Groq from LLM_PROVIDER / --llm
"""
from agent.llm.factory import get_llm   # re-exported so callers can write: from agent.llm import get_llm

__all__ = ["get_llm"]
