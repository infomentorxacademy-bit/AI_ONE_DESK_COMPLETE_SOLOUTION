"""common/stores/metrics_store.py : read data/metrics.json (error rate per service every 5 minutes).

USED BY servers/ops_server.py (get_metrics, find_spike)
"""
from __future__ import annotations

import json
from typing import Any

from common.config import DATA_DIR   # common/config.py: location of the data folder

# Allow-list of services (NFR-03): any other name is refused before touching a file.
SERVICES = ("payments-api", "orders-api", "search-api")


def _load() -> dict[str, Any]:
    return json.loads((DATA_DIR / "metrics.json").read_text(encoding="utf-8"))


def points(service: str) -> list[dict[str, Any]]:
    """The [{time, value}] series for an allow-listed service."""
    return _load()["services"][service]


def unit() -> str:
    """Unit text, e.g. 'percent_error_rate'."""
    return _load()["unit"]


def metrics_date() -> str:
    """The calendar date the metrics belong to (YYYY-MM-DD)."""
    return _load()["date"]


def find_spike(service: str, threshold: float) -> dict[str, Any]:
    """First point at or above `threshold`; baseline is the FIRST point of the series."""
    series = points(service)
    baseline = series[0]["value"]
    for point in series:
        if point["value"] >= threshold:
            return {"service": service, "date": metrics_date(), "first_time": point["time"],
                    "value": point["value"], "baseline": baseline}
    return {"service": service, "first_time": None}
