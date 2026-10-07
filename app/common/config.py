"""common/config.py : the ONE place where paths and environment settings are read.

WHAT   Resolves folder locations (app root, data folder, database file), the
       frozen business clock, and the LLM provider settings.
WHY    Every other module imports from here instead of calling os.environ or
       building paths itself. That keeps secrets out of code (ground rule G9,
       NFR-01) and lets tests point the app at a temporary database.
USED BY common/db.py, common/stores/*, agent/llm/*, run_queue.py, tests/conftest.py
"""
from __future__ import annotations

import os                                   # standard library: read environment variables
from datetime import datetime, timedelta, timezone  # standard library: build the frozen clock
from pathlib import Path                    # standard library: safe path handling

# python-dotenv loads a local ".env" file (git-ignored) into os.environ so that API
# keys never appear in source code. It is optional: if the package is missing we simply skip it.
try:
    from dotenv import load_dotenv          # third-party: reads KEY=VALUE lines from .env
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover - only hit when python-dotenv is not installed
    pass

# --------------------------------------------------------------------------- paths
APP_ROOT: Path = Path(__file__).resolve().parent.parent          # .../app
# data/ sits NEXT TO app/ (the company's raw material). OPSDESK_DATA_DIR overrides it for tests.
DATA_DIR: Path = Path(os.environ.get("OPSDESK_DATA_DIR", APP_ROOT.parent / "data"))
SCHEMA_FILE: Path = APP_ROOT / "schema.sql"


def db_path() -> Path:
    """Return the SQLite file path. Read on every call so tests can switch databases."""
    return Path(os.environ.get("OPSDESK_DB", APP_ROOT / "opsdesk.db"))


# --------------------------------------------------------------------------- clock
# The whole project is frozen at Wednesday 7 Oct 2026, 14:30 IST so every run gives identical answers (G5).
IST = timezone(timedelta(hours=5, minutes=30))
FROZEN_NOW: datetime = datetime(2026, 10, 7, 14, 30, 0, tzinfo=IST)

# --------------------------------------------------------------------------- LLM settings
# LLM_PROVIDER decides which "brain" drafts replies. Allowed values:
#   fake   -> built-in deterministic FakeLLM (default, free, offline)
#   openai -> OpenAI API            (needs OPENAI_API_KEY)
#   groq   -> Groq Cloud API        (needs GROQ_API_KEY)  NOTE: Groq (groq.com), NOT xAI "Grok"
# For backward compatibility with the requirements document, USE_REAL_LLM=1 means "use openai".


def llm_provider() -> str:
    """Return the selected provider name: 'fake', 'openai' or 'groq'."""
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if not provider:
        provider = "openai" if os.environ.get("USE_REAL_LLM") == "1" else "fake"
    return provider
