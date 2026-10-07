# OpsDesk Standard - AI Customer-Support Platform for TechNova Retail

An AI agent that reads support tickets, answers or resolves the safe ones with company tools and policy,
sends risky ones to the right human with a clear recommendation, keeps every ticket's status in a database,
and notices when many tickets point to one outage.

Built from `OpsDesk_Standard_Project_Requirements.docx`: **3 MCP servers (21 tools, 7 resources, 3 prompts)**,
**1 pure-Python rule module**, **1 LangGraph agent = 2 graphs (11 + 6 nodes)**, SQLite (10 tables), human approval
with `interrupt()` / resume, and a switchable LLM: **offline FakeLLM (default), OpenAI, or Groq**.

> **Groq vs Grok.** The Groq option uses **Groq Cloud (groq.com)** through its OpenAI-compatible API.
> It is *not* xAI's "Grok".

---------------------------------------------------------------------------------------------------

## 1. Quick start (about 2 minutes, no API key needed)

```bash
cd app
bash setup.sh                 # creates .venv, installs pinned libraries, builds opsdesk.db, creates .env
source .venv/bin/activate
pytest -q                     # 129 tests, all offline
python run_queue.py           # the full demo: 14 tickets + outage detector (~4 seconds)
```

Other commands (all from `app/`):

| Command | What it does |
|---|---|
| `python seed_db.py` | Reset the database to the original data (run before a demo) |
| `python run_queue.py --interactive` | YOU answer the approval cards in the terminal (approve / reject / edit_amount / cancel) |
| `python run_queue.py --llm openai` | Use OpenAI (needs `OPENAI_API_KEY`) |
| `python run_queue.py --llm groq` | Use Groq Cloud (needs `GROQ_API_KEY`) |
| `python spike/spike_client.py` / `spike_interrupt.py` | Two tiny proofs: a graph node calls an MCP tool; a graph pauses and resumes |
| `python -m servers.orders_server` | Run one MCP server on its own (also `knowledge_server`, `ops_server`) |

A real captured run is in [`docs/sample_run_output.txt`](docs/sample_run_output.txt).

## 2. Choosing the LLM (OpenAI, Groq, or none)

Copy `app/.env.example` to `app/.env` (git-ignored) and set one provider:

```ini
LLM_PROVIDER=fake      # default: offline, free, deterministic
LLM_PROVIDER=openai    # + OPENAI_API_KEY=...   (optional OPENAI_MODEL, default gpt-4o-mini)
LLM_PROVIDER=groq      # + GROQ_API_KEY=...     (optional GROQ_MODEL, default llama-3.3-70b-versatile)
```

`--llm fake|openai|groq` on `run_queue.py` overrides the file. Both real providers share ONE class
(`app/agent/llm/real.py`) because Groq speaks the OpenAI protocol (only the base URL and key differ).

**The model never makes business decisions.** It only (a) labels the ticket and (b) rephrases a template with safe
facts. Amount limits, approvers and dates are plain Python (`common/rules.py`). Guardrails around the model:
injection detection by code always wins over the model; a reply that mentions fraud, contains a phone number or
loses an id falls back to the plain template; any API error falls back to the offline FakeLLM; at most 2 LLM calls
per ticket, with token usage printed at the end.

## 3. Project structure (corporate layering)

```
AI_ONE_DESK_COMPLETE_SOLOUTION/
├── README.md                      <- you are here
├── docs/
│   ├── ARCHITECTURE.md            <- layers, data flow, graphs, security model
│   ├── REQUIREMENTS_TRACEABILITY.md <- every FR / NFR / scenario -> file + test
│   └── sample_run_output.txt      <- a real run of run_queue.py
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
    │   ├── llm/                   base.py fake.py real.py (OpenAI + Groq) factory.py
    │   ├── nodes/ticket/          ONE FILE PER NODE of Graph A (11 files)
    │   ├── nodes/incident/        ONE FILE PER NODE of Graph B (6 files)
    │   └── graph_ticket.py graph_incident.py   only wiring: which node runs next
    ├── run_queue.py               LAYER 4  demo runner (orchestration only)
    ├── tests/                     129 tests: db, rules, servers, scenarios, llm, architecture
    ├── spike/                     tiny working examples of the key techniques
    └── schema.sql seed_db.py setup.sh setup.bat requirements.txt .env.example pytest.ini
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
| `test_llm.py` | 26 | FakeLLM, OpenAI/Groq backends with a stub client, guardrails, fallbacks, 2-calls-per-ticket |
| `test_architecture.py` | 8 | least-privilege allow-lists, no secrets, docstrings + type hints, no raw PII |
| **Total** | **129** | `pytest -q` → 129 passed (about 9 s) |

## 7. Honest status - read this

* **The document's "GIVEN" files were not supplied, so I created them.** Only the requirements `.docx` was provided;
  the seed data, policies, logs, runbook, schema and tests were written from the document's tables. Facts the document
  states (row counts, order prices, dates, spike 0.4 → 22.8 at 14:10, D-301 at 14:05, INC-500, refund ids) are
  reproduced exactly; filler values (names of other customers, item names, log wording) are mine.
* **The tests are mine, not the course author's 88 hidden tests.** They cover every FR, NFR and scenario in the
  document (see the traceability table), and `run_queue.py` reproduces the document's section 16.2 and 16.3 tables.
  My count is 129, not 88, because I split the LLM and architecture checks out and added extra edge cases.
* **OpenAI and Groq were NOT exercised against the live APIs** (no keys in this environment). The code path is tested
  with a stub client, including the base URL/model/key selection and every fallback, but a first real run may need
  a model-name tweak in `.env`.
* **Windows (`setup.bat`) is untested**; Linux with Python 3.13 is what was run.
* Not done (stretch goals ST-1, ST-2, ST-4, ST-5): HTTP transport, MCP elicitation, loading templates/prompts
  through the MCP client, and a scoring script. ST-3 (real LLM) is done as described above.
* `InMemorySaver` means a paused approval is lost if the process exits; for production use a persistent checkpointer.
