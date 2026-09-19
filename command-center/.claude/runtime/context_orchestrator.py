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
            # Generated Deputy/provider output is historical context, never
            # current source truth. Keep the context projection focused on
            # durable work metadata so stale answers cannot be repeated as
            # present facts (for example, an old worker-health claim).
            if str(key).lower() in {"parameters", "payload", "source_context", "business_context", "history", "provider", "answer", "raw_answer", "result", "runtime"}:
                continue
            out[str(key)] = _compact_value(item, depth=depth + 1, max_chars=max_chars)
        return out
    if isinstance(value, list):
        return [_compact_value(item, depth=depth + 1, max_chars=max_chars) for item in value[:12]]
    text = str(value)
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


def _compact_rows(rows):
    projected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Mission records contain the full historical Deputy answer/context.
        # They are useful for audit, but are not current business evidence and
        # can reintroduce stale health claims into a new reasoning request.
        if row.get("mission_id") and row.get("authority") == "ACTION_RUNTIME_ONLY_FOR_MATERIAL_MUTATION":
            continue
        # Preserve user conversation turns, never recycle an old assistant
        # answer as if it were a current source observation.
        if row.get("kind") == "CONVERSATION_MESSAGE" and row.get("role") == "assistant":
            continue
        projected.append(_compact_value(row))
    return projected


def _evidence_keys(row):
    """Exact identifiers only; no fuzzy person/name merging."""
    keys = []
    for field in ("conversation_id", "source_record_id", "record_id", "person", "person_token", "deal_id", "meeting_id"):
        value = row.get(field) if isinstance(row, dict) else None
        if value not in (None, ""):
            keys.append((field, str(value).casefold().strip()))
    source = row.get("source") if isinstance(row, dict) else None
    if isinstance(source, dict):
        for field in ("record_id", "source_record_id", "external_id", "conversation_id"):
            value = source.get(field)
            if value not in (None, ""):
                keys.append((field, str(value).casefold().strip()))
    return keys


def correlate(selected):
    """Return conservative exact-evidence groups across retrieved records."""
    buckets = {}
    for tool, rows in (selected or {}).items():
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            ref = row.get("op_id") or row.get("record_id") or row.get("id") or row.get("event_id")
            for field, value in _evidence_keys(row):
                if len(value) < 3:
                    continue
                buckets.setdefault((field, value), []).append({"tool": tool, "ref": str(ref)})
    out = []
    for (field, value), refs in buckets.items():
        unique = {(r["tool"], r["ref"]) for r in refs}
        if len(unique) >= 2:
            out.append({"basis": field, "value": value, "records": sorted(unique),
                        "confidence": "OBSERVED_EXACT", "authority": "EVIDENCE_LINK_ONLY"})
    return out[:32]


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
    return {"query": intent, "tools": tools, "records": selected, "correlations": correlate(selected),
            "authority": "READ_ONLY_EVIDENCE", "result_limit": limit}


def run_tool(request, *, store=None):
    """Execute one registered read-only Deputy tool for the agent loop."""
    request = request if isinstance(request, dict) else {}
    name = request.get("tool")
    if name not in {"search_work", "search_open_loops", "search_observations", "search_approvals", "search_context"}:
        raise ValueError("unregistered Deputy read tool")
    query = str(request.get("query") or "").strip()
    if not query:
        raise ValueError("tool query is required")
    limit = max(1, min(int(request.get("limit", 8)), 12))
    result = retrieve(query, store=store, limit=limit)
    if name == "search_context":
        records = result.get("records", {})
    else:
        records = result.get("records", {}).get(name, [])
    return {"tool": name, "query": query, "records": records, "correlations": result.get("correlations", []),
            "authority": "READ_ONLY_EVIDENCE", "result_limit": limit}
