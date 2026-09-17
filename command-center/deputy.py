#!/usr/bin/env python3
"""Thin, canonical Deputy interaction surface.

This command deliberately delegates execution to ``.claude/skills/engine.py``.
It adds only the durable mission envelope, governed current-source summary and
human-readable rendering needed for an operator to use the existing runtime.
No provider writer, task store or approval mechanism is implemented here.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, pathlib, sys
import re

ROOT = pathlib.Path(__file__).resolve().parent
SKILLS = ROOT / ".claude" / "skills"
ARCH = ROOT / ".claude" / "architecture"
INTEGRATIONS = ROOT / ".claude" / "integrations"
for p in (SKILLS, ARCH, INTEGRATIONS):
    if str(p) not in sys.path: sys.path.insert(0, str(p))
import engine


def _mission_id(intent):
    day = datetime.date.today().isoformat()
    return "MIS-" + hashlib.sha256((day + "|" + intent.strip()).encode()).hexdigest()[:16]


def _canonical_intent(intent):
    """Map the two first-class operator phrases to existing registered chains."""
    text = intent.casefold()
    if re.search(r"\b(today|daily)\b", text) and re.search(r"\b(operating|operations?)?\s*brief\b", text):
        return "daily brief"
    if re.search(r"sales", text) and re.search(r"operations?", text) and re.search(r"(plan|execution|week)", text):
        return "weekly sales & operations review"
    return intent


def assemble_context():
    """Read currently governed local sources; unavailable sources stay explicit."""
    sources = []
    try:
        import adapter_tasks
        task_data = adapter_tasks.read("tasks.list", {})
        records = task_data.get("records", [])
        sources.append({"source": "INT-TASKS", "state": "VERIFIED_READ", "records": len(records),
                        "open": sum(1 for r in records if r.get("open")),
                        "updated_at": task_data.get("source_updated_at"), "provenance": task_data.get("identity")})
    except Exception as exc:
        sources.append({"source": "INT-TASKS", "state": "UNAVAILABLE", "reason": type(exc).__name__})
    cert_path = ROOT / ".claude" / "integrations" / "certification.json"
    try:
        cert = json.loads(cert_path.read_text(encoding="utf-8")).get("integrations", {})
        for sid in ("INT-TG", "INT-OL-CAL", "INT-OL-MAIL", "INT-B24", "INT-MB"):
            row = cert.get(sid, {})
            sources.append({"source": sid, "state": row.get("state", "UNKNOWN"),
                            "read_ops": row.get("read_ops", []), "retrieved_at": row.get("certified_at")})
    except (OSError, ValueError):
        sources.append({"source": "integration-certification", "state": "UNAVAILABLE"})
    st = engine._store()
    loops = st.list("loops", limit=200)
    actions = st.list("actions", limit=200)
    tickets = st.list("tickets", where="status='OPEN'", limit=100)
    return {"sources": sources, "operational_state": {
        "open_loops": len([x for x in loops if x.get("state") not in ("CLOSED", "VERIFIED")]),
        "pending_actions": len([x for x in actions if x.get("state") in ("APPROVAL_REQUIRED", "RESULT_UNKNOWN", "EXECUTED_UNVERIFIED")]),
        "open_tickets": len(tickets),
    }, "truth_rule": "current certified source evidence only; messages and generated output are not authority"}


def _human(result, understood, context, mission_id):
    lines = ["UNDERSTOOD", understood,
             "", "CURRENT STATE"]
    for row in context["sources"]:
        detail = f"{row['records']} records ({row['open']} open)" if "records" in row else row.get("state", "UNKNOWN")
        lines.append(f"- {row['source']}: {detail}")
    op = context["operational_state"]
    lines += [f"- Open loops: {op['open_loops']} · pending approvals/actions: {op['pending_actions']} · open tickets: {op['open_tickets']}",
              "", "RESULT"]
    lines.append(f"- Status: {result.get('status', 'UNKNOWN')} · mission: {mission_id}")
    if result.get("brains"):
        lines.append("- Brains: " + ", ".join(x["brain_id"] for x in result["brains"].get("selected_brains", [])))
    for step in result.get("steps", []):
        if step.get("status") in ("EXECUTED", "VERIFIED", "ASSISTED", "RECORDED"):
            summary = step.get("result_summary") or step.get("result", {}).get("management_text")
            if summary: lines.append(f"- {step.get('skill')}: {str(summary)[:320]}")
    if result.get("status") in ("BLOCKED", "PARTIAL"):
        lines += ["", "BLOCKED / NEEDS REVIEW"]
        for b in result.get("blocked", [])[:6]: lines.append(f"- {b.get('code', b.get('reason', 'unavailable'))}")
    lines += ["", "AUTHORITY", "- Analysis and preparation may proceed; material external changes remain Action Runtime + exact Gev approval.",
              "", "FOLLOW-THROUGH", f"- Resume with: deputy resume {mission_id}"]
    return "\n".join(lines)


def run(intent, *, inputs=None, as_json=False):
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("intent must be a non-empty string")
    intent = intent.strip(); mission_id = _mission_id(intent)
    canonical_intent = _canonical_intent(intent)
    context = assemble_context()
    reg = engine.load_registry()
    routing = __import__("brain_router").route(canonical_intent)
    understood = (f"I will {intent[0].lower() + intent[1:]}. I will use current certified HouseNet sources, "
                  "prepare next actions, and keep material external changes behind the required approval boundary.")
    runtime_inputs = {"_operating_context": context}
    if canonical_intent == "weekly sales & operations review":
        task = next((x for x in context["sources"] if x["source"] == "INT-TASKS"), {})
        runtime_inputs["content"] = (f"Current evidence: INT-TASKS has {task.get('records', 'UNKNOWN')} records, "
                                      f"{task.get('open', 'UNKNOWN')} open. Sales and Operations live KPI sources are "
                                      "reported by the runtime as UNKNOWN when not certified; no figures are inferred.")
    result = engine.run_deputy_request(reg, canonical_intent, runtime_inputs, action_level="ANALYZE",
                                       session_id=mission_id, source="DeputyCLI")
    graph = None
    try:
        # Mission graphs are checkpoints in the existing Store. The
        # commitments table remains reserved for commitment records consumed
        # by the canonical commitment engine.
        from work_orchestrator import create_node, validate_graph
        nodes=[]; parent=None
        for kind in ("GOAL", "STRATEGY", "ACTION_PLAN", "TASK", "CHECKPOINT", "EVIDENCE", "VERIFIED_COMPLETION"):
            n=create_node(kind, intent if kind == "GOAL" else f"{kind}: {intent}", owner="GEV",
                          status="PLANNED" if kind == "ACTION_PLAN" else "PROPOSED", parent_id=parent,
                          source="mission:" + mission_id, brains=[x["brain_id"] for x in routing.get("selected_brains", [])],
                          approval="PENDING" if kind == "TASK" else "NOT_REQUIRED")
            nodes.append(n); parent=n["id"]
        errors=validate_graph(nodes)
        if errors: raise ValueError(";".join(errors))
        graph={"nodes":nodes,"validation":"GREEN","records":[engine._store().record("checkpoints", mission_id + ":graph", {"kind":"MISSION_WORK_GRAPH","mission_id":mission_id,"nodes":nodes})]}
    except Exception as exc:
        graph = {"status": "BLOCKED", "reason": type(exc).__name__}
    payload = {"mission_id": mission_id, "request": intent, "understanding": {"raw_intent": intent, "outcome": understood,
        "scope": "current HouseNet operating state", "constraints": ["no external mutation without Action Runtime approval"],
        "completion_criteria": ["facts have provenance", "prepared actions are separated", "verification state is honest"]},
        "context": context, "routing": routing, "runtime": result, "work_graph": graph,
        "completion_state": "PREPARED" if result.get("status") in ("OK", "PARTIAL") else "BLOCKED",
        "authority": "ACTION_RUNTIME_ONLY_FOR_MATERIAL_MUTATION"}
    store = engine._store(); store.upsert("commitments", mission_id, payload)
    if as_json: return payload
    return _human(result, understood, context, mission_id)


def resume(mission_id, as_json=False):
    row = engine._store().get("commitments", mission_id)
    if not row: raise ValueError("mission not found")
    return json.dumps(row, ensure_ascii=False, indent=2, default=str) if as_json else _human(row.get("runtime", {}), row.get("understanding", {}).get("outcome", ""), row.get("context", {}), mission_id)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="deputy", description="HouseNet Deputy operating loop")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run"); run_p.add_argument("intent"); run_p.add_argument("--json", action="store_true")
    res_p = sub.add_parser("resume"); res_p.add_argument("mission_id"); res_p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        out = run(args.intent, as_json=True) if args.command == "run" else resume(args.mission_id, as_json=args.json)
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str) if args.command == "run" and args.json else out)
        return 0
    except (ValueError, engine.SkillError) as exc:
        print(json.dumps({"status": "BLOCKED", "code": type(exc).__name__, "reason": str(exc)}, ensure_ascii=False))
        return 2

if __name__ == "__main__": raise SystemExit(main())
