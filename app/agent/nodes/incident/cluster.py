"""Node 2 of Graph B: cluster. Do 3+ similar tickets arrive close together? (FR-42)

TOOLS  none
LLM    llm.classify() on each new ticket (keep the ones labelled incident_report)
RULE   sort by created_at, keep tickets within 30 minutes of the FIRST one. Fewer than 3 => not an outage (graph ends).
"""
from __future__ import annotations

import asyncio                                   # standard library: run LLM calls off the event loop
from datetime import datetime, timedelta         # standard library: time-window arithmetic
from typing import Any, Awaitable, Callable

from agent.state import IncidentState            # agent/state.py: state shape

ALLOWED_TOOLS: tuple[str, ...] = ()
MIN_CLUSTER = 3                                  # fewer similar tickets than this is just noise
WINDOW = timedelta(minutes=30)                   # all tickets must arrive within 30 minutes of the first
_FORMAT = "%Y-%m-%d %H:%M:%S"                    # how created_at is stored in the database


def make_cluster(llm: Any) -> Callable[[IncidentState], Awaitable[dict[str, Any]]]:
    """Build the cluster node."""

    async def cluster(state: IncidentState) -> dict[str, Any]:
        reports: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for ticket in state["tickets"]:
            verdict = await asyncio.to_thread(llm.classify, ticket)
            if verdict["kind"] == "incident_report":
                reports.append((ticket, verdict))
        reports.sort(key=lambda pair: pair[0]["created_at"])
        if not reports:
            return {"cluster": [], "cluster_ids": []}
        first_time = datetime.strptime(reports[0][0]["created_at"], _FORMAT)
        group = [t for t, _ in reports if datetime.strptime(t["created_at"], _FORMAT) - first_time <= WINDOW]
        if len(group) < MIN_CLUSTER:
            return {"cluster": [], "cluster_ids": []}
        service = reports[0][1].get("service", "payments-api")
        return {"cluster": group, "cluster_ids": [t["id"] for t in group], "service": service}

    return cluster
