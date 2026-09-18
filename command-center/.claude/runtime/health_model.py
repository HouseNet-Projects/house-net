"""Truthful health model for Deputy's operator and self-audit surfaces.

Health is deliberately split into product runtime, registered HouseNet business
sources, and developer/deployment diagnostics.  A source outage can therefore
degrade a feature without making the Deputy product itself appear down.
"""
from __future__ import annotations

import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
INTEGRATIONS = HERE.parent.parent / "integrations"
if str(INTEGRATIONS) not in sys.path:
    sys.path.insert(0, str(INTEGRATIONS))

REGISTERED = ("INT-TASKS", "INT-OL-MAIL", "INT-OL-CAL", "INT-TG", "INT-B24", "INT-MB")


def _business_rows():
    try:
        import readiness
        rows = {row["integration_id"]: row for row in readiness.table()}
    except Exception:
        rows = {}
    out = []
    for source_id in REGISTERED:
        row = rows.get(source_id, {})
        state = row.get("read_state") or row.get("read") or "UNKNOWN"
        if row.get("deferred"):
            state = "DEFERRED_BY_GEV"
        elif state in ("VERIFIED_READ", "RELIABLE_READ"):
            state = "AVAILABLE"
        elif state in ("NOT CERTIFIED", "IMPLEMENTED", "CONFIGURED", "DECLARED"):
            state = "NEEDS_SETUP" if state != "CONFIGURED" else "PARTIAL"
        out.append({
            "source_id": source_id,
            "name": row.get("system") or source_id,
            "state": state,
            "freshness": row.get("live_identity") or "UNKNOWN",
            "limitation": row.get("unblock") or ("Deferred by Gev" if row.get("deferred") else None),
            "registered": True,
        })
    return out


def build(*, store_state="READY", action_runtime_state="READY", worker=None, provider=None, developer=None):
    """Return a serializable, three-domain health snapshot."""
    worker = worker or {}
    provider = provider or {}
    developer = developer or {}
    product = {
        "state": "DOWN" if store_state == "UNAVAILABLE" else ("DEGRADED" if any(
            x not in ("READY", True) for x in (store_state, action_runtime_state)
        ) or provider.get("state") in ("AUTH_REQUIRED", "UNAVAILABLE", "NOT_READY") else "AVAILABLE"),
        "api": "AVAILABLE",
        "store": store_state,
        "worker": "AVAILABLE" if worker.get("running") else "DEGRADED",
        "action_runtime": action_runtime_state,
        "claude_provider": provider.get("state", "UNKNOWN"),
    }
    business = _business_rows()
    available = sum(1 for row in business if row["state"] == "AVAILABLE")
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "product": product,
        "business_data": {"available": available, "total": len(business), "sources": business,
                           "state": "AVAILABLE" if available == len(business) else ("PARTIAL" if available else "UNAVAILABLE")},
        "developer_diagnostics": developer,
    }

