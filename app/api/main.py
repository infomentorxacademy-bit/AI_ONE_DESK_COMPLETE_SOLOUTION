"""api/main.py : creates the FastAPI application and wires startup / shutdown / error handling.

STARTUP  1) start the three MCP servers once  2) if LLM_PROVIDER is set in the environment, select it
         (if its key is missing the API still starts; the UI then asks you to choose).
RUN      uvicorn api.main:app --reload --port 8000        interactive docs: http://localhost:8000/docs
SECURITY This demo API has NO login. Bind it to localhost only. Anyone who can reach it can act as an approver.
"""
from __future__ import annotations

import logging                                   # standard library: report startup problems
import os                                        # standard library: read the allowed web origin
from contextlib import asynccontextmanager       # standard library: lifespan (startup + shutdown in one function)
from typing import AsyncIterator, Callable

from fastapi import FastAPI, Request             # fastapi: the web framework
from fastapi.middleware.cors import CORSMiddleware   # fastapi: lets the Vite dev server call the API
from fastapi.responses import JSONResponse       # fastapi: build error responses

from agent.llm import get_llm                    # agent/llm/factory.py: builds the OpenAI / Groq client
from agent.llm.base import LLMClient             # agent/llm/base.py: type of an LLM backend
from agent.llm.real import LLMError              # agent/llm/real.py: raised when the model is unusable
from agent.mcp_utils import open_tools           # agent/mcp_utils.py: starts the 3 MCP servers once
from api.routers import admin, approvals, config, incidents, tickets   # one router file per area
from api.state import AppState, NoLlmChosen      # api/state.py: shared objects
from common.config import llm_provider           # common/config.py: LLM_PROVIDER from the environment

log = logging.getLogger("opsdesk.api")


def create_app(llm_loader: Callable[[str], LLMClient] = get_llm) -> FastAPI:
    """Build the app. `llm_loader` is injectable so tests can plug in a test double instead of a paid API."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with open_tools() as tools:                      # servers stay up for the whole life of the API
            state = AppState(tools=tools, llm_loader=llm_loader)
            if provider := llm_provider():
                try:
                    state.select_llm(provider)
                except Exception as exc:                       # e.g. API key not set: start anyway, UI will ask
                    log.warning("LLM '%s' not ready: %s", provider, exc)
            app.state.ops = state
            yield

    app = FastAPI(title="OpsDesk Standard API", version="1.0.0", lifespan=lifespan,
                  description="HTTP API for the TechNova support agent. See /docs.")
    # The React dev server (Vite) runs on another port; allow exactly that origin (override with OPSDESK_WEB_ORIGIN).
    app.add_middleware(CORSMiddleware, allow_origins=[os.environ.get("OPSDESK_WEB_ORIGIN", "http://localhost:5173")],
                       allow_methods=["*"], allow_headers=["*"])

    for module in (config, tickets, approvals, incidents, admin):
        app.include_router(module.router, prefix="/api")

    # --- turn known problems into clear JSON errors instead of a 500 stack trace ---
    @app.exception_handler(NoLlmChosen)
    async def _no_llm(_: Request, exc: NoLlmChosen) -> JSONResponse:
        return JSONResponse(status_code=409, content={"error": "NO_LLM", "detail": str(exc)})

    @app.exception_handler(LLMError)
    async def _llm_error(_: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"error": "LLM_ERROR", "detail": str(exc)})

    return app


app = create_app()          # the object uvicorn imports: `uvicorn api.main:app`
