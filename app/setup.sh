#!/usr/bin/env bash
# setup.sh : one command to get a working project (NFR-15).
#   1. creates a virtual environment (.venv)   2. installs the pinned libraries
#   3. builds opsdesk.db from ../data           4. creates .env from .env.example (if missing)
# Run from the app/ folder:   bash setup.sh      then:   source .venv/bin/activate
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"'

[ -d .venv ] || "$PYTHON" -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
[ -f .env ] || cp .env.example .env
.venv/bin/python seed_db.py
echo "Setup done. Next:  source .venv/bin/activate && pytest -q && python run_queue.py"
