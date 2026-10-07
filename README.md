# OpsDesk Standard - AI Customer-Support Platform for TechNova Retail

An AI agent that reads support tickets, answers or resolves the safe ones with company tools and policy,
sends risky ones to the right human with a clear recommendation, keeps every ticket's status in a database,
and notices when many tickets point to one outage.

Built from `OpsDesk_Standard_Project_Requirements.docx`: **3 MCP servers (21 tools, 7 resources, 3 prompts)**,
**1 pure-Python rule module**, **1 LangGraph agent = 2 graphs (11 + 6 nodes)**, SQLite (10 tables), human approval
with `interrupt()` / resume, and a choice of LLM: **OpenAI or Groq** (you pick one; there is no offline fake in the product).

> **Groq vs Grok.** The Groq option uses **Groq Cloud (groq.com)** through its OpenAI-compatible API.
> It is *not* xAI's "Grok".

---------------------------------------------------------------------------------------------------

## 1. Quick start (about 2 minutes; the demo needs an OpenAI or Groq API key)

```bash
cd app
bash setup.sh                 # creates .venv, installs pinned libraries, builds opsdesk.db, creates .env
# edit app/.env: set LLM_PROVIDER=groq (or openai) and the matching API key
source .venv/bin/activate
pytest -q                     # 147 tests; offline, no key needed (they use a test-only stand-in model)
python run_queue.py           # the full demo; if no LLM is chosen it ASKS you: 1) openai 2) groq
```

Other commands (all from `app/`):

| Command | What it does |
|---|---|
| `python seed_db.py` | Reset the database to the original data (run before a demo) |
| `python run_queue.py --interactive` | YOU answer the approval cards in the terminal (approve / reject / edit_amount / cancel) |
| `python run_queue.py --llm openai` | Use OpenAI (needs `OPENAI_API_KEY`) |
| `python run_queue.py --llm groq` | Use Groq Cloud with `openai/gpt-oss-20b` (needs `GROQ_API_KEY`) |
| `python run_queue.py` | No flag and no `LLM_PROVIDER`: you are asked which LLM to use |
| `python spike/spike_client.py` / `spike_interrupt.py` | Two tiny proofs: a graph node calls an MCP tool; a graph pauses and resumes |
| `python -m servers.orders_server` | Run one MCP server on its own (also `knowledge_server`, `ops_server`) |

## 1b. Web app: FastAPI backend + React (Vite) UI

The command-line demo above is all the requirements document asks for. The web app is an **optional extra layer**
on top of the same agent (no business logic was duplicated):

```bash
# terminal 1 - backend (from app/, with the venv active and your key in app/.env)
uvicorn api.main:app --port 8000          # API docs: http://localhost:8000/docs

# terminal 2 - frontend (needs Node 20+)
cd frontend
npm install
npm run dev                               # open http://localhost:5173
```

In the UI: choose the LLM (OpenAI or Groq) in the top bar → open a ticket → **Run agent** → when the agent pauses
for a refund, an approval card appears (also listed in the **Approvals** tab). Pick who you are in **Acting as**
(Meera/Dev = lead, Kiran = finance) and Approve / Reject / Edit amount / Cancel. **Incidents** runs the outage
detector. **Audit log** shows who approved what. Frontend checks: `npm test` (17 tests) and `npm run build`.

A screen-by-screen tour with screenshots and a 5-minute demo script is in [`docs/UI_GUIDE.md`](docs/UI_GUIDE.md).

**This demo web app has no login.** Anyone who can open it can act as any approver, and the "Reset demo data" button
(only shown when `OPSDESK_ENABLE_RESET=1`) wipes the database. Run it on localhost only. A real deployment needs
authentication, with the approver identity taken from the login instead of the "Acting as" menu.

## 2. Choosing the LLM (OpenAI or Groq)

`setup.sh` creates `app/.env` (git-ignored). Set one provider there (or pass `--llm`; if neither is set you are asked):

```ini
LLM_PROVIDER=openai    # + OPENAI_API_KEY=...   (optional OPENAI_MODEL, default gpt-4o-mini)
LLM_PROVIDER=groq      # + GROQ_API_KEY=...     (optional GROQ_MODEL, default openai/gpt-oss-20b)
```

The models are defined in ONE place: the `PROVIDERS` table in `app/agent/llm/real.py`.
```

`--llm openai|groq` on `run_queue.py` overrides the file. Both real providers share ONE class
(`app/agent/llm/real.py`) because Groq speaks the OpenAI protocol (only the base URL and key differ).

**The model never makes business decisions.** It only (a) labels the ticket and (b) rephrases a template with safe
facts. Amount limits, approvers and dates are plain Python (`common/rules.py`). Guardrails around the model:
injection detection by code always wins over the model; a reply that mentions fraud, contains a phone number or
loses an id falls back to the plain template; if the model's classification is unusable the run stops with a clear `LLMError` instead of guessing; at most 2 LLM calls
per ticket, with token usage printed at the end.

## 3. Project structure (corporate layering)

```
AI_ONE_DESK_COMPLETE_SOLOUTION/
├── README.md                      <- you are here
├── docs/
│   ├── ARCHITECTURE.md            <- layers, data flow, graphs, security model
│   ├── REQUIREMENTS_TRACEABILITY.md <- every FR / NFR / scenario -> file + test
├── data/                          <- the company's raw material (never edited by code)
│   ├── standard_data.json  metrics.json  logs/  policies/  runbooks/
│   └── internal/fraud-rules.md    <- deliberate TRAP: no server can reach it
└── app/
    ├── common/                    LAYER 1  shared building blocks (no LLM in here)
    │   ├── config.py db.py        settings, SQLite access, frozen clock, audit writer
    │   ├── rules.py               check_refund(): THE refund policy (pure Python)
    │   ├── masking.py responses.py templates.py prompts.py
    │   ├── repositories/          one SQL module per table (customers, orders, refunds, tickets, incidents, ...)
    │   └── stores/                read-only file readers with allow-lists (policies, metrics, logs)
    ├── servers/                   LAYER 2  the 3 MCP servers (thin: tool declarations only)
    │   ├── orders_server.py       11 tools, 1 resource template, 1 prompt   (support operations)
    │   ├── knowledge_server.py    1 tool, 3 resources, 1 template, 1 prompt (policy team)
    │   └── ops_server.py          9 tools, 1 resource, 1 template, 1 prompt (platform team)
    ├── agent/                     LAYER 3  the LangGraph agent (MCP client)
    │   ├── state.py mcp_utils.py runtime.py approvers.py report.py reply_facts.py text_utils.py
    │   ├── llm/                   base.py real.py (OpenAI + Groq, PROVIDERS table) guardrails.py factory.py
    │   ├── nodes/ticket/          ONE FILE PER NODE of Graph A (11 files)
    │   ├── nodes/incident/        ONE FILE PER NODE of Graph B (6 files)
    │   └── graph_ticket.py graph_incident.py   only wiring: which node runs next
    ├── api/                       LAYER 4  FastAPI backend for the web UI (main, state, schemas, routers/)
    ├── run_queue.py               LAYER 4  command-line demo runner (orchestration only)
    ├── tests/                     132 tests: db, rules, servers, scenarios, llm, architecture
    ├── spike/                     tiny working examples of the key techniques
    └── schema.sql seed_db.py setup.sh setup.bat requirements.txt .env.example pytest.ini
└── frontend/                      React + TypeScript + Vite UI (src/api, components, views, hooks, test)
```

Rule of thumb for reviewers: **every Python file starts with a docstring saying WHAT it is, WHY it exists and
WHO uses it, and every import line is commented with the file it comes from and the purpose it serves.**

## 4. How a ticket flows (one paragraph)

`run_queue.py` starts the three MCP servers once. For each ticket, **Graph A** runs: `classify` (label + mark
in_progress) → depending on the kind: privacy/injection → `safe_reply`; policy → `answer_policy`; payment
failure → `incident_reply`; otherwise `resolve_customer` → `fetch_order` → `check_rules` (pure Python) →
automatic `issue_refund`, or `approval_gate` (pauses; a lead, then finance above Rs 25,000, answers) → `draft_reply`
→ `finish` (always writes the final status). **Graph B** reads all `new` tickets, clusters 3+ payment failures
within 30 minutes, correlates the error spike with a deployment 0-10 minutes earlier, links the tickets to the open
incident, **proposes** (never executes) a rollback, and drafts an engineer note and a customer message.
Details and diagrams: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 5. Safety design (ground rules G1-G9)

| Rule | Where it is enforced |
|---|---|
| G1 LLM never decides money/approvers/dates | `common/rules.py`, called by the agent AND re-checked inside `issue_refund` |
| G2 tools return dicts, errors don't raise | `common/responses.py`, all `servers/*` |
| G3 text/logs/tool output are data | prompts in `common/prompts.py`; `search_logs` warning; injection flagged, never obeyed |
| G4 PII masked in the server | `common/masking.py`, used only in `servers/orders_server.py` |
| G5 frozen clock | `common/db.py now()` (never `datetime.now()`) |
| G6 writes are idempotent | refund idempotency key, `INSERT OR IGNORE` links, one proposal per deployment, no-op status updates |
| G7 least privilege | each node declares `ALLOWED_TOOLS`; `ToolBelt` blocks everything else; servers get no API keys |
| G8 rollback only proposed | `propose_rollback` only inserts a row with status `awaiting_approval` |
| G9 no secrets in code | keys only from env / git-ignored `.env`; a test scans the source |

Extra hardening beyond the document: `issue_refund` verifies every approver exists in the `approvers` table with
that exact role, so a forged role cannot unlock a refund.

## 6. Test results

| File | Tests | Covers |
|---|---|---|
| `test_db.py` | 3 | seed data, foreign keys, frozen clock |
| `test_rules.py` | 30 | every rule and boundary (2000/2001, 25000/25001, day 30/31, order of checks) |
| `test_servers.py` | 37 | every tool, resource, template and prompt; PII masking; the fraud-rules trap |
| `test_scenarios.py` | 25 | scenarios S1-S24 end to end (real graphs + real MCP servers over stdio) |
| `test_llm.py` | 28 | provider choice (no default), OpenAI/Groq backends with a stub client, guardrails, 2-calls-per-ticket |
| `test_api.py` | 15 | FastAPI endpoints end to end: choose LLM, run tickets, two-step approval, forged role, incidents, reset guard |
| `test_architecture.py` | 9 | least-privilege allow-lists, no secrets, docstrings + type hints, no raw PII |
| **Python total** | **147** | `pytest -q` → 147 passed (about 15 s) |
| `frontend/` (Vitest) | 17 | approval card logic, API client errors, run panel, app shell (`npm test`) |

## 7. Honest status - read this

* **The document's "GIVEN" files were not supplied, so I created them.** Only the requirements `.docx` was provided;
  the seed data, policies, logs, runbook, schema and tests were written from the document's tables. Facts the document
  states (row counts, order prices, dates, spike 0.4 → 22.8 at 14:10, D-301 at 14:05, INC-500, refund ids) are
  reproduced exactly; filler values (names of other customers, item names, log wording) are mine.
* **The tests are mine, not the course author's 88 hidden tests.** They cover every FR, NFR and scenario in the
  document (see the traceability table), and with the test stand-in model `run_queue.py`'s graphs reproduce the document's section 16.2 and 16.3 tables (verified before the fake LLM was removed).
  My count is 132, not 88, because I split the LLM and architecture checks out and added extra edge cases.
* **The product no longer has an offline LLM, and the full demo has NOT been run with a real model.** Without a key I could
  not run `run_queue.py` end to end after removing the fake. The graphs, rules and servers are unchanged and tested with the
  test-only stand-in (`app/tests/stub_llm.py`), but a real model may classify some tickets differently (a wrong label can
  change an outcome; the rules, approvals and injection check still apply). Please run it once with your key and tell me
  what you see.
* **OpenAI and Groq were NOT exercised against the live APIs** (no keys in this environment). The code path is tested
  with a stub client, including the base URL/model/key selection and every fallback, but a first real run may need
  a model-name tweak in `.env`.
* **Windows (`setup.bat`) is untested**; Linux with Python 3.13 is what was run.
* Not done (stretch goals ST-1, ST-2, ST-4, ST-5): HTTP transport, MCP elicitation, loading templates/prompts
  through the MCP client, and a scoring script. ST-3 (real LLM) is done as described above.
* **The web app was tested end to end in a headless browser, but with the test stand-in model, not a real LLM** (no key
  here). The browser drove: choose LLM → run T1 → T10 lead + finance approvals → outage detection → audit log, with no
  console errors apart from a favicon 404 that I then fixed. The UI is functional, not a finished design; there is no
  login, the production build (`npm run build`) is not served by FastAPI (use `npm run dev`, or host `dist/` yourself).
* `InMemorySaver` means a paused approval is lost if the process exits; for production use a persistent checkpointer.
