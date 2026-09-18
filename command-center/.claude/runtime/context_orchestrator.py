"""Read-only Deputy context tools.

The orchestrator selects bounded, relevant canonical records before Claude is
invoked. Tool results are evidence, never authority, and this module has no
provider write capability.
"""
from __future__ import annotations
import json, re
from store import Store


def _terms(text):
    return {x for x in re.findall(r"[\w\u0530-\u058F]{3,}", str(text).casefold()) if x not in {"what", "where", "which", "this", "that", "this"}}


def _matches(row, terms):
    blob = json.dumps(row, ensure_ascii=False, default=str).casefold()
    return not terms or any(t in blob for t in terms)


def _compact_value(value, *, depth=0, max_chars=900):
    """Project evidence for a provider prompt without copying raw Store rows."""
    if depth >= 3:
        text = json.dumps(value, ensure_ascii=False, default=str)
        return text[:max_chars] + ("…" if len(text) > max_chars else "")
    if isinstance(value, dict):
        out = {}
        for key, item in list(value.items())[:32]:
            if str(key).lower() in {"parameters", "payload", "source_context", "business_context", "history"}:
                continue
            out[str(key)] = _compact_value(item, depth=depth + 1, max_chars=max_chars)
        return out
    if isinstance(value, list):
        return [_compact_value(item, depth=depth + 1, max_chars=max_chars) for item in value[:12]]
    text = str(value)
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


def _compact_rows(rows):
    return [_compact_value(row) for row in rows]


def retrieve(intent, *, store=None, limit=8):
    """Run bounded read-only tools against the canonical Store."""
    store = store or Store()
    terms = _terms(intent)
    tools = []
    selected = {}
    for name, table in (("search_work", "commitments"), ("search_open_loops", "loops"), ("search_observations", "channel_events"), ("search_approvals", "actions")):
        try:
            rows = [r for r in store.list(table, limit=200) if _matches(r, terms)]
            rows = rows[-limit:]
            selected[name] = _compact_rows(rows)
            tools.append({"tool": name, "status": "OK", "count": len(rows), "source": table})
        except Exception as exc:
            selected[name] = []
            tools.append({"tool": name, "status": "UNAVAILABLE", "reason": type(exc).__name__})
    return {"query": intent, "tools": tools, "records": selected,
            "authority": "READ_ONLY_EVIDENCE", "result_limit": limit}
