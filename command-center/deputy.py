#!/usr/bin/env python3
"""Thin, canonical Deputy interaction surface.

This command deliberately delegates execution to ``.claude/skills/engine.py``.
It adds only the durable mission envelope, governed current-source summary and
human-readable rendering needed for an operator to use the existing runtime.
No provider writer, task store or approval mechanism is implemented here.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, pathlib, sys, os
import re

ROOT = pathlib.Path(__file__).resolve().parent
SKILLS = ROOT / ".claude" / "skills"
ARCH = ROOT / ".claude" / "architecture"
INTEGRATIONS = ROOT / ".claude" / "integrations"
RUNTIME = ROOT / ".claude" / "runtime"
for p in (SKILLS, ARCH, INTEGRATIONS, RUNTIME):
    if str(p) not in sys.path: sys.path.insert(0, str(p))
import engine
import company_cockpit
import execution_surface
import proactive
import health_model
import worker as proactive_worker
from ai_provider import status as provider_status, ask as provider_ask, ask_agent as provider_ask_agent
from context_orchestrator import retrieve as retrieve_context, run_tool as run_context_tool


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
    if any(k in text for k in ("company cockpit", "what is happening in the company", "what needs my attention", "what changed", "overdue or blocked", "approvals are waiting", "current kpi data")):
        return "company cockpit"
    if "weekly management review" in text: return "weekly management review"
    if "monthly management review" in text: return "monthly management review"
    if any(k in text for k in ("watch current", "proactive check", "what changed today")): return "proactive cycle"
    return intent


def _is_certification_record(row):
    source = row.get("source") if isinstance(row, dict) else None
    if isinstance(source, dict):
        return source.get("channel") in ("certification", "fixture") or str(source.get("source_id", "")).startswith("CERT-")
    return str(source or "").casefold() in ("certification", "fixture")


def _is_business_ticket(row):
    source = row.get("source") if isinstance(row, dict) else None
    if isinstance(source, dict):
        return bool(source.get("source_id")) and not _is_certification_record(row)
    return str(source or "").startswith("INT-")


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
    # Certification is host/runtime evidence, not a required repository file.
    # Derive source state from the canonical registry/readiness contract so a
    # missing local evidence artifact never makes Deputy itself appear blocked.
    for row in health_model.build(provider=provider_status()).get("business_data", {}).get("sources", []):
        sources.append({"source": row["source_id"], "state": row["state"],
                        "limitation": row.get("limitation"), "freshness": row.get("freshness")})
    st = engine._store()
    loops = st.list("loops", limit=200)
    actions = st.list("actions", limit=200)
    tickets = st.list("tickets", where="status='OPEN'", limit=100)
    open_loops = [x for x in loops if x.get("state") not in ("CLOSED", "VERIFIED") and not _is_certification_record(x)]
    business_tickets = [x for x in tickets if _is_business_ticket(x)]
    worker_state = proactive_worker.status()
    return {"sources": sources, "health": health_model.build(worker=worker_state, provider=provider_status()), "operational_state": {
        "open_loops": len(open_loops),
        "pending_actions": len([x for x in actions if x.get("state") in ("APPROVAL_REQUIRED", "RESULT_UNKNOWN", "EXECUTED_UNVERIFIED")]),
        "open_tickets": len(business_tickets),
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
        labels = {"NO_APPLICABLE_SKILL": "Deputy used general governed analysis; no dedicated workflow was needed."}
        for b in result.get("blocked", [])[:6]:
            code = b.get("code", b.get("reason", "unavailable"))
            lines.append(f"- {labels.get(code, code)}")
    lines += ["", "AUTHORITY", "- Analysis and preparation may proceed; material external changes remain Action Runtime + exact Gev approval.",
              "", "FOLLOW-THROUGH", f"- Resume with: deputy resume {mission_id}"]
    return "\n".join(lines)

def _provider_prompt(intent, context, understood, runtime, routing, graph, language="hy"):
    """Bounded, sanitized context for the reasoning provider; never grants write authority."""
    state_labels = {
        "AVAILABLE": "available",
        "VERIFIED_READ": "available",
        "PARTIAL": "partially connected",
        "NEEDS_SETUP": "needs connection",
        "DEFERRED_BY_GEV": "deferred by Gev",
        "UNAVAILABLE": "unavailable",
        "NOT_CONFIGURED": "not configured",
    }
    source_rows = []
    for row in context.get("sources", []):
        if not isinstance(row, dict):
            continue
        source_rows.append({
            "name": row.get("name") or {"INT-TASKS": "Task register", "INT-OL-MAIL": "Outlook mail", "INT-OL-CAL": "Outlook calendar", "INT-TG": "Telegram", "INT-B24": "Bitrix24 CRM", "INT-MB": "MikroBill"}.get(row.get("source"), "Registered HouseNet source"),
            "state": state_labels.get(row.get("state"), "available" if row.get("state") else "unknown"),
            "freshness": row.get("freshness"),
            "limitation": row.get("limitation"),
        })
    health = context.get("health", {})
    provider_health = dict(health) if isinstance(health, dict) else {}
    business = provider_health.get("business_data")
    if isinstance(business, dict):
        business = dict(business)
        business["state"] = state_labels.get(business.get("state"), business.get("state"))
        business["sources"] = [{
            "name": row.get("name"),
            "state": state_labels.get(row.get("state"), "unknown"),
            "freshness": row.get("freshness"),
            "limitation": row.get("limitation"),
        } for row in business.get("sources", []) if isinstance(row, dict)]
        provider_health["business_data"] = business
    compact = {
        "language": language, "intent": intent, "understanding": understood,
        "sources": source_rows, "health": provider_health, "operational_state": context.get("operational_state", {}),
        "conversation": context.get("conversation", []),
        "tool_trace": context.get("tool_trace", {}),
        "truth_rule": context.get("truth_rule"),
        "runtime": {"status": runtime.get("status"), "blocked": runtime.get("blocked", []),
                    "steps": [{"skill": s.get("skill"), "status": s.get("status"),
                               "summary": s.get("result_summary")} for s in runtime.get("steps", [])]},
        "brains": [b.get("brain_id") for b in routing.get("selected_brains", [])],
        "work_graph": {"validation": (graph or {}).get("validation"), "nodes": len((graph or {}).get("nodes", []))},
        "authority": "Reasoning and preparation only. Never execute or invent external mutations. Material changes require Action Runtime and exact Gev approval.",
    }
    prompt = ("You are Deputy's reasoning layer. Answer the user's question using only the governed context below. "
            "State unavailable or stale data honestly; do not invent facts. Do not expose chain-of-thought, secrets, "
            "raw credentials, or internal implementation noise. Return a concise human answer in the requested language (Armenian when language is 'hy'; English when language is 'en') with priorities, "
            "recommended next actions, limitations, and evidence references. A PARTIAL_SUCCESS runtime result means the operating cycle completed with partial business-source coverage; use the health.product.worker state to judge whether the worker process is actually available. Do not describe the worker as degraded solely because an optional source is unavailable. A dedicated skill is optional; never tell the user that a reasonable analytical question failed because no skill matched. For the normal answer, humanize source names and states: never expose INT-* identifiers, PARTIAL/NEEDS_SETUP/DEFERRED_BY_GEV codes, loop/ticket/runtime jargon, PIDs, raw JSON, or internal implementation names. Say for example that a source is unavailable, needs connection, or is intentionally deferred; keep exact technical values only in evidence/details.\n\n" +
            json.dumps(compact, ensure_ascii=False, default=str, indent=2))
    # Claude Code is invoked through argv; keep governed context below a
    # deterministic ceiling so broad searches cannot fail with E2BIG.
    max_chars = 60000
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars] + "\n[Context truncated by Deputy after bounded evidence projection.]"
    return prompt

def operator_response(payload, language="hy"):
    provider = payload.get("provider") or {}
    runtime = payload.get("runtime") or {}
    answer = provider.get("answer") or payload.get("understanding", {}).get("outcome") or "Deputy prepared the current governed context."
    limitations = []
    if provider.get("status") not in ("OK", "NOT_INVOKED"):
        limitations.append(provider.get("reason") or "The reasoning provider is unavailable.")
    def _limitation(item):
        code = item.get("code", item.get("reason", "unavailable")) if isinstance(item, dict) else str(item)
        labels = {
            "NO_APPLICABLE_SKILL": ("Deputy used general governed analysis." if language != "hy" else "Deputy-ը օգտագործեց ընդհանուր կառավարվող վերլուծություն։"),
            "SOURCE_UNAVAILABLE": "A required source is currently unavailable.",
        }
        return labels.get(code, code)
    limitations.extend(_limitation(x) for x in runtime.get("blocked", [])[:5])
    actions = []
    for step in runtime.get("steps", []):
        if step.get("result_summary") or step.get("skill"):
            actions.append({"skill": step.get("skill"), "status": step.get("status"), "summary": step.get("result_summary")})
    localized_summary = payload.get("understanding", {}).get("outcome")
    if language == "hy":
        localized_summary = "Կօգտագործեմ HouseNet-ի ընթացիկ հավաստված աղբյուրները, կպատրաստեմ հաջորդ քայլերը և արտաքին փոփոխությունները կպահեմ պահանջվող հաստատման սահմաններում։"
    else:
        localized_summary = localized_summary or "I will use current certified HouseNet sources, prepare next actions, and keep material external changes behind the required approval boundary."
    status = payload.get("completion_state", runtime.get("status", "PREPARED"))
    if status == "BLOCKED" and payload.get("context", {}).get("health", {}).get("business_data", {}).get("state") in ("PARTIAL", "UNAVAILABLE"):
        status = "PARTIAL_DATA"
    return {"status": status,
            "answer": answer, "language": language, "mission_id": payload.get("mission_id"),
            "provider": provider.get("provider", "claude-code-max"),
            "provider_state": provider.get("provider_state") or provider.get("state") or provider.get("status"),
            "runtime_state": runtime.get("status"),
            "summary": localized_summary,
            "recommended_actions": actions, "evidence": {"sources": payload.get("context", {}).get("sources", []),
                "work_graph": {"validation": (payload.get("work_graph") or {}).get("validation"), "nodes": len((payload.get("work_graph") or {}).get("nodes", []))}},
            "limitations": limitations, "approval_required": bool(payload.get("execution", {}).get("approval_inbox")) if payload.get("execution") else False,
            "work_graph_summary": {"validation": (payload.get("work_graph") or {}).get("validation"), "node_count": len((payload.get("work_graph") or {}).get("nodes", []))}}


def run(intent, *, inputs=None, as_json=False):
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("intent must be a non-empty string")
    intent = intent.strip(); mission_id = _mission_id(intent)
    canonical_intent = _canonical_intent(intent)
    context = assemble_context()
    context["tool_trace"] = retrieve_context(intent, store=engine._store())
    if isinstance(inputs, dict) and isinstance(inputs.get("conversation"), list):
        context["conversation"] = inputs["conversation"][-12:]
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
    # An analytical question does not need a pre-authored skill trigger. Keep
    # the resolver evidence, but allow the governed reasoning provider to
    # answer it without granting any mutation authority.
    if result.get("status") == "BLOCKED" and any(
        b.get("code") == "NO_APPLICABLE_SKILL" for b in result.get("blocked", [])
    ):
        result["status"] = "PARTIAL"
    cockpit = None
    if canonical_intent in ("company cockpit", "weekly management review", "monthly management review"):
        cockpit = company_cockpit.query(intent)
    execution = None
    if any(k in intent.casefold() for k in ("do everything", "needs my approval", "what needs my approval")):
        execution = {"mode": "PREPARE_ONLY", "approval_inbox": execution_surface.approval_inbox(mission_id),
                     "capability_matrix": execution_surface.capability_matrix(),
                     "policy": "THINK/PREPARE proceeds; COMMIT/CHANGE remains exact Action Runtime approval."}
    proactive_result = proactive.run_cycle() if canonical_intent == "proactive cycle" else None
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
    language = (inputs or {}).get("language", "hy")
    provider = provider_ask_agent(_provider_prompt(intent, context, understood, result, routing, graph, language),
                                  context=context,
                                  tool_executor=lambda request: run_context_tool(request, store=engine._store())) if os.environ.get("DEPUTY_USE_CLAUDE") == "1" else {"status": "NOT_INVOKED", "provider": "claude-code-max", "reason": "Claude Code invocation is opt-in; canonical runtime remains provider-neutral."}
    payload = {"mission_id": mission_id, "request": intent, "understanding": {"raw_intent": intent, "outcome": understood,
        "scope": "current HouseNet operating state", "constraints": ["no external mutation without Action Runtime approval"],
        "completion_criteria": ["facts have provenance", "prepared actions are separated", "verification state is honest"]},
        "context": context, "routing": routing, "runtime": result, "work_graph": graph,
        "cockpit": cockpit,
        "execution": execution,
        "proactive": proactive_result, "provider": provider,
        "completion_state": ("PREPARED" if result.get("status") in ("OK", "PARTIAL")
                              else "PARTIAL_DATA" if context.get("health", {}).get("business_data", {}).get("state") in ("PARTIAL", "UNAVAILABLE")
                              else "BLOCKED"),
        "authority": "ACTION_RUNTIME_ONLY_FOR_MATERIAL_MUTATION"}
    store = engine._store(); store.upsert("commitments", mission_id, payload)
    if as_json: return payload
    if cockpit: return cockpit["human"] + "\n\nFOLLOW-THROUGH\n- Resume with: deputy resume " + mission_id
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
