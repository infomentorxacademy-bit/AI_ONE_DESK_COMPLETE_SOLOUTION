"""agent/report.py : pretty-print the demo output (tables and notes) for run_queue.py.

WHY    Presentation is kept apart from logic, so run_queue.py stays a short, readable script.
USED BY run_queue.py
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from agent.runtime import TicketRun   # agent/runtime.py: the per-ticket result record


def ticket_line(run: TicketRun) -> str:
    """One line: ticket | kind | outcome | final status (section 13.5)."""
    final = run.final
    outcome = final.get("outcome", "pending_approval" if run.cards else "?")
    return f"{run.ticket_id:<4}| {final.get('kind', '?'):<9}| {outcome:<20}| {final.get('final_status', 'pending_approval')}"


def print_first_pass_table(runs: list[TicketRun]) -> None:
    """The table of section 16.2: outcomes BEFORE any human answered a card."""
    counts = Counter(r.first_label for r in runs)
    order = ["answered", "refund_issued", "paused", "refund_duplicate", "refund_declined",
             "ignored_injection", "needs_clarification", "refused_privacy"]
    print("\nOutcomes before any human answers a card (section 16.2)")
    print(f"  {'outcome':<22}{'tickets':<26}count")
    for name in order:
        ids = [r.ticket_id for r in runs if r.first_label == name]
        print(f"  {name:<22}{', '.join(ids):<26}{counts.get(name, 0)}")
    print(f"  {'TOTAL':<48}{len(runs)}")


def print_final_table(runs: list[TicketRun]) -> None:
    """The table of section 16.3: final ticket statuses after all cards were answered."""
    print("\nFinal ticket statuses (section 16.3)")
    for run in runs:
        print(f"  {run.ticket_id:<4}{run.final.get('outcome', '?'):<22}{run.final.get('final_status', '?')}")


def print_incident(result: dict[str, Any]) -> None:
    """Graph B result: cluster size, spike, deployment, incident, proposal and both notes."""
    if not result.get("cluster_ids"):
        print("  No outage cluster found.")
        return
    spike, dep, proposal = result["spike"], result.get("correlated") or {}, result.get("proposal") or {}
    print(f"  cluster size     : {len(result['cluster_ids'])} tickets ({result['cluster_ids'][0]}..{result['cluster_ids'][-1]})")
    print(f"  spike            : {spike['baseline']}% -> {spike['value']}% at {spike['first_time']}")
    print(f"  deployment       : {dep.get('id')} {dep.get('version')} at {dep.get('at')}")
    print(f"  incident         : {result.get('incident_id')}   flags: {result.get('flags')}")
    print(f"  rollback proposal: {proposal.get('id')} ({proposal.get('status')}) - NOT executed")
    print("\n  --- engineer note ---")
    print("  " + result["engineer_note"].replace("\n", "\n  "))
    print("\n  --- customer message ---")
    print("  " + result["customer_message"])


def print_audit(items: list[dict[str, Any]]) -> None:
    """An audit trail, oldest first, so a reader can follow the story top to bottom."""
    for row in reversed(items):
        print(f"  {row['ts']}  {row['actor']:<8}{row['action']:<16}{row['detail']}")
