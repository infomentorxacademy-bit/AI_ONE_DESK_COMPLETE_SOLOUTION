"""run_queue.py : the demo runner (section 13.5). Run:  python run_queue.py [--llm openai|groq] [--interactive]

STEPS  1 reset the database  2 start the 3 MCP servers  3 run tickets T1..T14 through Graph A (answering
       approval cards)  4 run Graph B (outage detector)  5 print the summary tables and the audit trail of T10.
This file only ORCHESTRATES; the real work is in agent/, servers/ and common/.
"""
from __future__ import annotations

import argparse                               # standard library: command-line options
import asyncio                                # standard library: the graphs are async
import sys                                    # standard library: detect whether a person is at the keyboard
import time                                   # standard library: measure total run time (NFR-12)

import seed_db                                # seed_db.py: main() rebuilds opsdesk.db from the given data
from agent.approvers import InteractiveApprover, ScriptedApprover   # agent/approvers.py: who answers cards
from agent.graph_incident import build_incident_graph               # agent/graph_incident.py: Graph B
from agent.graph_ticket import build_ticket_graph                   # agent/graph_ticket.py: Graph A
from agent.llm import get_llm                                       # agent/llm/factory.py: builds the OpenAI / Groq client
from agent.llm.real import PROVIDERS                                # agent/llm/real.py: the table of supported providers
from common.config import llm_provider                              # common/config.py: reads LLM_PROVIDER
from agent.mcp_utils import open_tools, unwrap                      # agent/mcp_utils.py: start servers, read results
from agent.report import (print_audit, print_final_table, print_first_pass_table,   # agent/report.py: printing
                          print_incident, ticket_line)
from agent.runtime import TicketRun, run_incident, run_ticket       # agent/runtime.py: pause/resume loop

QUEUE = [f"T{n}" for n in range(1, 15)]       # the 14 normal tickets; B01..B12 are handled by Graph B


def choose_provider(cli_value: str | None) -> str:
    """Which LLM to use: --llm flag, else LLM_PROVIDER, else ASK the person. There is no default."""
    chosen = cli_value or llm_provider()
    if chosen:
        return chosen
    if not sys.stdin.isatty():
        raise SystemExit("No LLM chosen. Use --llm openai|groq or set LLM_PROVIDER in app/.env.")
    options = list(PROVIDERS)
    print("Which LLM do you want to use?")
    for number, name in enumerate(options, start=1):
        print(f"  {number}) {name}")
    answer = input("Enter a number or name: ").strip().lower()
    return options[int(answer) - 1] if answer.isdigit() and 1 <= int(answer) <= len(options) else answer


async def main(provider: str | None, interactive: bool) -> None:
    started = time.perf_counter()
    seed_db.main(quiet=True)                                    # 1. clean, identical data every run
    llm = get_llm(choose_provider(provider))     # asks you if no provider was given
    print(f"LLM backend: {llm.name}")
    approver = InteractiveApprover() if interactive else ScriptedApprover()

    async with open_tools() as tools:                           # 2. one connection per server for the whole run
        ticket_graph = build_ticket_graph(tools, llm)
        incident_graph = build_incident_graph(tools, llm)

        print("\nticket| kind     | outcome             | final status")
        runs: list[TicketRun] = []
        for ticket_id in QUEUE:                                 # 3. Graph A for T1..T14
            run = await run_ticket(ticket_graph, ticket_id, approver)
            runs.append(run)
            print(ticket_line(run))

        print("\nIncident flow (Graph B)")                       # 4. outage detector
        print_incident(await run_incident(incident_graph))

        print_first_pass_table(runs)                            # 5. summaries
        print_final_table(runs)
        trail = unwrap(await tools["get_audit_trail"].ainvoke({"ticket_id": "T10"}))["items"]
        print("\nAudit trail for T10 (who approved what)")
        print_audit(trail)

    print(f"\nLLM usage: {llm.usage}")
    print(f"Finished in {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the OpsDesk demo queue.")
    parser.add_argument("--llm", choices=list(PROVIDERS), help="LLM to use (default: LLM_PROVIDER, otherwise you are asked)")
    parser.add_argument("--interactive", action="store_true", help="answer approval cards yourself in the terminal")
    args = parser.parse_args()
    asyncio.run(main(args.llm, args.interactive))
