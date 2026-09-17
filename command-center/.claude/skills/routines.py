# -*- coding: utf-8 -*-
"""PROACTIVE ROUTINES on existing skills — morning · midday exception check · end-of-day · weekly. Each routine is a fixed composition
of governed skill runs (audited through engine.run_skill); nothing runs in the background by itself. The scheduler is reported
NOT_CONFIGURED until an external trigger (Windows Task Scheduler / cron / service) actually invokes `skill.py routine <name>
--from-scheduler` and thereby writes a heartbeat. No hidden background process exists in this runtime.

    python .claude/skills/skill.py routine morning|midday|eod|weekly [--from-scheduler]"""
import json, datetime, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROUTINES = {
 "morning": [("daily_briefing", {}), ("decision_queue", {}), ("open_loop_memory", {})],
 "midday":  [("exception_review", {}), ("change_review", {}), ("alert_review", {})],
 "eod":     [("end_of_day_control", {}), ("commitment_memory", {}), ("alert_review", {})],
 "weekly":  [("weekly_executive_review", {}), ("commitment_memory", {"query": "ով ա ամենաշատ խոստում ուշացնում"}), ("decision_memory", {"query": "review pending"})],
}

def _hb_path():
    import engine; return pathlib.Path(engine.STATE_DIR) / "scheduler_heartbeat.json"

def scheduler_status():
    p = _hb_path()
    try: d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except ValueError: d = {}
    return {"status": "CONFIGURED" if d.get("last_run") else "NOT_CONFIGURED", "last_run": d.get("last_run"), "routine": d.get("routine"), "note": "routines run only when invoked (skill.py routine <name>) or by an external scheduler that reports a heartbeat; no background delivery"}

def run(name, *, ticket_id=None, from_scheduler=False, inputs=None):
    import engine
    if name not in ROUTINES: return {"status": "BLOCKED", "code": "UNKNOWN_ROUTINE", "reason": f"routine must be one of {sorted(ROUTINES)}"}
    reg = engine.load_registry(); steps = []; base = dict(inputs or {})
    for sid, extra in ROUTINES[name]:
        r = engine.run_skill(reg, sid, {**base, **extra}, intent=f"routine:{name}", selection_reason=f"routine {name}", ticket_id=ticket_id)
        steps.append({"skill": sid, "status": r.get("status"), "summary": r.get("result_summary"), "text": (r.get("result") or {}).get("management_text") if sid == "daily_briefing" else None, "blocked": r.get("blocked")})
    if from_scheduler:
        try: _hb_path().write_text(json.dumps({"last_run": datetime.datetime.now().isoformat(timespec="seconds"), "routine": name}), encoding="utf-8")
        except Exception: pass
    return {"status": "EXECUTED" if all(s["status"] in ("EXECUTED", "ASSISTED", "VERIFIED", "RECORDED", "DUPLICATE") for s in steps) else "PARTIAL", "routine": name, "steps": steps, "scheduler": scheduler_status(), "mutation_performed": False,
            "delivery": "in-session output only — sending a routine result to Telegram/WhatsApp/mail is an Action Runtime approval"}

def render(r):
    L = [f"ROUTINE {r.get('routine')} — {r.get('status')} · SCHEDULER: {r['scheduler']['status']}"]
    for s in r.get("steps", []):
        L.append(f"  {s['skill']}: {s['status']}" + (f" {json.dumps(s['summary'], ensure_ascii=False)[:120]}" if s.get("summary") else ""))
        if s.get("text"): L.append("    " + s["text"].replace("\n", "\n    "))
    return "\n".join(L)
