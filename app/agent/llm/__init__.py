"""agent/llm/ : the LLM seam. The graphs only use get_llm() and the two methods classify()/draft().

  base.py     the interface            fake.py   offline deterministic backend (default)
  real.py     OpenAI and Groq backend  factory.py chooses a backend from LLM_PROVIDER / --llm
"""
from agent.llm.factory import get_llm   # re-exported so callers can write: from agent.llm import get_llm

__all__ = ["get_llm"]
