"""api/routers/config.py : which LLM is active, which are available, and choosing one ("which to use").

GET  /api/config   current LLM + the list of providers (name, model, whether its API key is set) + feature flags
POST /api/llm      choose OpenAI or Groq. API keys are NEVER sent through the API: they come from app/.env.
"""
from __future__ import annotations

import os                                        # standard library: check whether a key / flag is set (never returned)

from fastapi import APIRouter, Depends, HTTPException   # fastapi: routing, dependencies, errors

from agent.llm.real import PROVIDERS             # agent/llm/real.py: the table of providers and models
from api.deps import get_state                   # api/deps.py: shared state dependency
from api.schemas import SelectLlmRequest         # api/schemas.py: request body
from api.state import AppState                   # api/state.py: shared objects

router = APIRouter(tags=["config"])


def reset_enabled() -> bool:
    """The demo-data reset button is only available when OPSDESK_ENABLE_RESET=1 (off by default)."""
    return os.environ.get("OPSDESK_ENABLE_RESET", "0") == "1"


@router.get("/config")
async def get_config(state: AppState = Depends(get_state)) -> dict:
    """Current LLM and what can be chosen. Reports only whether a key exists, never the key itself."""
    providers = [{"name": name, "model": os.environ.get(model_var) or default_model,
                  "configured": bool(os.environ.get(key_var))}
                 for name, (_url, key_var, model_var, default_model) in PROVIDERS.items()]
    return {"llm": state.llm.name if state.llm else None, "providers": providers, "reset_enabled": reset_enabled()}


@router.post("/llm")
async def select_llm(body: SelectLlmRequest, state: AppState = Depends(get_state)) -> dict:
    """Choose the LLM. 400 with a clear message if that provider's API key is not set."""
    try:
        llm = state.select_llm(body.provider)
    except RuntimeError as exc:                 # e.g. "GROQ_API_KEY is not set..."
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"llm": llm.name}
