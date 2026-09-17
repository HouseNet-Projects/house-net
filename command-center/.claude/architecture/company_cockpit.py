"""Derived company cockpit built on Deputy's existing intelligence and Store.

The cockpit is a view, never a second system of record.  It deliberately keeps
source health and provenance beside every derived conclusion and degrades to a
partial result when optional providers are unavailable.
"""
from __future__ import annotations
import datetime as _dt, hashlib, json

import intelligence
import registry
import readiness


def _source_health():
    rows = []
    for iid in registry.ids():
        try:
            r = readiness.row(iid)
            state = r.get("read_state", "UNKNOWN")
            if state == "DEFERRED": freshness = "DEFERRED"
            elif state in ("VERIFIED_READ", "RELIABLE_READ"): freshness = "CURRENT"
            elif state in ("NOT_CONFIGURED", "IMPLEMENTED"): freshness = "UNAVAILABLE"
            else: freshness = "UNKNOWN"
            rows.append({"source_id": iid, "owner": registry.get(iid).get("owner_role"),
                         "authority": registry.get(iid).get("authority", {}).get("name"),
                         "read_state": state, "write_state": "NONE" if not registry.get(iid).get("write_ops") else "GOVERNED",
                         "certification": r.get("read"), "freshness": freshness,
                         "current_limitation": r.get("unblock") or r.get("deferred", {}).get("note")})
        except Exception as exc:
            rows.append({"source_id": iid, "read_state": "ERROR", "freshness": "UNKNOWN", "error": type(exc).__name__})
    return rows


def _task_view(state):
    tasks = state.get("tasks", [])
    return {"open": [t for t in tasks if t.get("open")],
            "overdue": [t for t in tasks if t.get("overdue")],
            "due_soon": [t for t in tasks if t.get("due_soon")],
            "blocked": [t for t in tasks if t.get("blocked")],
            "ownerless": [t for t in tasks if t.get("ownerless")],
            "no_deadline": [t for t in tasks if t.get("no_deadline")],
            "waiting": [t for t in tasks if t.get("waiting_for")],
            "needs_gev": [t for t in tasks if t.get("decision_needed") or t.get("gev_owned")]}


def _domain_signals(state, health):
    open_tasks = state.get("open_tasks", [])
    result = []
    for domain in ("Sales", "Marketing", "Operations", "Customer Care / Retention", "Billing / Revenue", "Tech / NOC", "People / Admin", "Data / Analytics", "Strategy / Transformation / PMO"):
        words = domain.casefold().replace("/", " ").split()
        relevant = [t for t in open_tasks if any(w in (t.get("title", "") + " " + t.get("comment", "")).casefold() for w in words if len(w) > 3)]
        state_name = "AT_RISK" if any(t.get("overdue") or t.get("blocked") for t in relevant) else ("WATCH" if relevant else "INSUFFICIENT_DATA")
        result.append({"domain": domain, "state": state_name, "evidence": [f"task:{t.get('id')}" for t in relevant[:5]], "reason": "derived from current task evidence" if relevant else "no authoritative domain-specific live evidence"})
    return result


def _priority_items(state, task_view):
    items = []
    for t in task_view["overdue"] + task_view["blocked"] + task_view["due_soon"]:
        level = "HIGH" if t.get("critical") or t.get("overdue") else "MEDIUM"
        items.append({"priority": level, "summary": t.get("title"), "owner": t.get("owner") or "UNKNOWN", "deadline": t.get("due"), "why": "overdue" if t.get("overdue") else ("blocked" if t.get("blocked") else "due soon"), "source": "INT-TASKS", "evidence": f"task:{t.get('id')}"})
    return sorted(items, key=lambda x: (0 if x["priority"] == "HIGH" else 1, str(x.get("deadline") or "9999"), x["evidence"]))[:12]


def build_snapshot(*, query="cockpit", persist=True):
    state = intelligence.current_state({})
    exc = intelligence.exceptions(state)
    queue = intelligence.gev_queue(state, exc)
    task_view = _task_view(state)
    health = _source_health()
    signature = intelligence.signature(state, exc, queue)
    sid = "SNAP-" + hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
    previous = intelligence.previous_checkpoint(before_at=state.get("at"))
    delta = intelligence.changes(previous, signature)
    if persist:
        intelligence.record_checkpoint(state, kind="cockpit", exc=exc, queue=queue)
    missing = [r for r in health if r.get("read_state") in ("NOT_CONFIGURED", "DEFERRED", "UNKNOWN")]
    return {"snapshot_id": sid, "generated_at": state.get("at"), "source_as_of": {r["source_id"]: r.get("last_verified") for r in health},
            "query": query, "company_status": "PARTIAL_SUCCESS" if missing else "CURRENT", "tasks": task_view,
            "active_priorities": _priority_items(state, task_view), "open_work": len(task_view["open"]),
            "overdue_work": len(task_view["overdue"]), "blocked_work": len(task_view["blocked"]),
            "waiting_approvals": queue, "unverified_completions": [a for a in state.get("actions", []) if a.get("state") in ("EXECUTED_UNVERIFIED", "RESULT_UNKNOWN")],
            "critical_open_loops": state.get("commitments", []), "domain_signals": _domain_signals(state, health),
            "risks": exc[:12], "anomalies": exc[:12], "missing_data": [{"source_id": r["source_id"], "state": r.get("read_state"), "limitation": r.get("current_limitation")} for r in missing],
            "source_health": health, "delta": delta, "next_actions": _priority_items(state, task_view),
            "evidence": {"truth_mode": state.get("truth_mode"), "task_provenance": state.get("task_provenance"), "visibility": state.get("visibility")},
            "truth_hierarchy": ["CONTROL_PLANE", "COMMAND_CENTER", "KNOWLEDGE", "EXTERNAL_SYSTEM", "MESSAGES_AS_EVIDENCE", "GENERATED_DERIVED", "HISTORY"]}


def render(snapshot):
    lines = ["COMPANY NOW", f"- {snapshot['company_status']} · snapshot {snapshot['snapshot_id']}", "", "TOP PRIORITIES"]
    lines += [f"- [{x.get('priority', x.get('severity', 'INFO'))}] {x.get('summary', x.get('issue', x.get('what', 'attention item')))} ({x.get('why', x.get('category', 'review'))}; owner {x.get('owner', 'UNKNOWN')})" for x in snapshot["active_priorities"][:6]] or ["- No evidence-backed priority in the current window."]
    lines += ["", "CHANGED", f"- {snapshot['delta'].get('meaningful', 0)} meaningful changes" if snapshot["delta"].get("available") else "- No previous production checkpoint; baseline created.", "", "OVERDUE / BLOCKED", f"- {snapshot['overdue_work']} overdue · {snapshot['blocked_work']} blocked", "", "WAITING FOR YOU", f"- {len(snapshot['waiting_approvals'])} approval/decision items", "", "DOMAIN SIGNALS"]
    lines += [f"- {d['domain']}: {d['state']} — {d['reason']}" for d in snapshot["domain_signals"] if d["state"] != "INSUFFICIENT_DATA"][:8] or ["- No domain-specific live evidence."]
    lines += ["", "DATA GAPS"] + [f"- {x['source_id']}: {x['state']}" for x in snapshot["missing_data"]] + ["", "NEXT ACTIONS"]
    lines += [f"- {x['summary']}" for x in snapshot["next_actions"][:6]] or ["- Continue monitoring current open work."]
    return "\n".join(lines)


def query(text):
    t = text.casefold()
    mode = "cockpit"
    if "changed" in t: mode = "delta"
    elif "attention" in t or "approve" in t: mode = "attention"
    elif "overdue" in t or "blocked" in t: mode = "exceptions"
    elif "weekly" in t: mode = "weekly"
    elif "monthly" in t: mode = "monthly"
    snap = build_snapshot(query=mode)
    if mode == "attention": snap["active_priorities"] = snap["waiting_approvals"]
    if mode == "exceptions": snap["active_priorities"] = snap["risks"]
    if "sales" in t: snap["active_priorities"] = [x for x in snap["active_priorities"] if "sales" in str(x).casefold()]
    snap["human"] = render(snap)
    return snap
