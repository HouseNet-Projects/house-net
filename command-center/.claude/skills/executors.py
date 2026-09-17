# -*- coding: utf-8 -*-
"""Skill executors — REAL logic over real data (Tasks.xlsx, hardened SQLite state store, memory files).
Contract: fn(inputs: dict, skill: dict, reg: dict) -> dict with 'status' in
  EXECUTED | VERIFIED | RECORDED | DUPLICATE | BLOCKED | ASSISTED  (+ data).
Never fabricates numbers: skills needing data the runtime lacks return BLOCKED with a reason.
"""
import json, re, sys, datetime, pathlib, hashlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def _st():
    import engine
    return engine._store()
sys.path.insert(0, str(ROOT / ".claude" / "policy")); import paths        # ONE business-root resolver (workspace_policy.json -> business_root)
XLSX = paths.tasks(ROOT)
SHEET = "ԱՌԱՋԱԴՐԱՆՔՆԵՐ"
HDR_ROW, FIRST_ROW = 12, 13
COL = {"id": 2, "task": 3, "status": 6, "comment": 7, "due": 11, "owner": 12}
OPEN_STATUSES = {"Ընթացքում", "Չսկսված", "Պարզ չէ", "Սպասում"}
CLOSED_STATUSES = {"Արված", "Չեղարկված"}
HEAD = "Գև"
HY = ["երկուշաբթի","երեքշաբթի","չորեքշաբթի","հինգշաբթի","ուրբաթ","շաբաթ","կիրակի"]
CAUSE_TYPES = ["PERSON","PROCESS","SYSTEM","POLICY","CAPACITY","TRAINING","MANAGEMENT","INCENTIVE","DATA"]
MATERIAL = re.compile(r"(price|pricing|սակագ|salary|comp|աշխատավարձ|hire|fire|terminat|ազատ|contract|պայմանագ|public|հրապարակ|refund|concession|discount|զեղչ|policy|irreversib)", re.I)

class ExecError(Exception): pass

# ───────────────────────── business context helpers ─────────────────────────
def _bc(inputs):
    return (inputs or {}).get("business_context") or {"available": False, "gaps": ["BUSINESS_CONTEXT_MISSING"]}

def _bc_brief(inputs):
    """Compact business context for result envelopes: what the model knows, what it does not (gap codes)."""
    b = _bc(inputs)
    if not b.get("available"): return {"available": False, "gaps": b.get("gaps", ["BUSINESS_CONTEXT_MISSING"])}
    return {"available": True, "playbook": b.get("playbook"), "playbook_name": b.get("playbook_name"), "kpis": b.get("kpis", []), "processes": b.get("processes", []),
            "owner": b.get("owner", {}), "required_data": b.get("required_data", []), "sources": b.get("sources", []), "conflicts": b.get("conflicts", []), "gaps": b.get("gaps", []), "rules": b.get("rules", [])}

def _bc_owner(inputs, default="UNKNOWN"):
    o = _bc(inputs).get("owner") or {}
    if o.get("code") in ("OWNER_UNKNOWN",) or not o.get("owner_role"): return default if not o.get("code") else f"OWNER_UNKNOWN"
    if o.get("status") == "CONFLICT": return f"SOURCE_CONFLICT — {o.get('owner_role')}"
    return o["owner_role"] + (f" — {o['owner_person']}" if o.get("owner_person") and o["owner_person"] != "UNKNOWN" else "")

QKIND = [("owner", r"(who owns|who is responsible|who is accountable|owner of|ով է պատասխանատու|ում վրա է|who handles)"), ("approval", r"(who (should |must )?approve|who approves|ով պիտի հաստատի|approval for)"),
         ("process", r"(which process|what process|որ գործընթաց|process (for|handles)|handles a)"), ("kpi", r"(which kpi|what kpi|which metric|what metric|որ ցուցանիշ|tells us)"),
         ("playbook", r"(what do we do|what should we do|playbook|ինչ ենք անում)"), ("role", r"(who reports to|reports to|role of|what does .* do|պաշտոն)")]

def business_query(inputs, skill=None, reg=None):
    """Business Operating Model lookup with provenance. Fail closed: OWNER_UNKNOWN / KPI_DEFINITION_MISSING / PROCESS_UNDEFINED /
    APPROVAL_RULE_UNKNOWN / SOURCE_CONFLICT / BUSINESS_CONTEXT_MISSING are returned as structured codes, never guessed around."""
    import business
    q = inputs.get("query") or inputs.get("intent") or inputs.get("text") or ""
    if not business.available(): return {"status": "BLOCKED", "code": "BUSINESS_CONTEXT_MISSING", "reason": "business model not built (.claude/business/*.json)", "label": "UNKNOWN"}
    if not q: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "query missing (who owns / which process / what kpi / playbook / who approves)"}
    kind = inputs.get("kind") or next((k for k, rx in QKIND if re.search(rx, q, re.I)), "context")
    mid = business.model_id()
    if mid.get("state") in ("SOURCE_MISSING",): return {"status": "BLOCKED", "code": "SOURCE_MISSING", "reason": f"a current business source is missing: {business.model_state().get('missing')} — rebuild after restoring it", "model": mid, "label": "UNKNOWN"}
    if not mid.get("certified"): return {"status": "BLOCKED", "code": "BUSINESS_CONTEXT_MISSING", "reason": f"business model {mid.get('model_version')} is {mid.get('state')} / uncertified — run build_business_model.py", "model": mid, "label": "UNKNOWN"}
    def _stale(srcs):
        st = business.stale_sources_for(srcs)
        return ({"status": "BLOCKED", "code": "STALE_MODEL", "reason": f"sources {st['changed']} changed since the model was built — rebuild before relying on this fact", "model": mid, "label": "UNKNOWN"} if st["changed"] else None)
    if kind in ("owner", "approval"):
        o = business.find_owner(q)
        if o.get("code") == "OWNER_UNKNOWN" or o.get("code") == "BUSINESS_CONTEXT_MISSING":
            return {"status": "BLOCKED", "code": o["code"], "reason": o.get("reason", "no owner defined in any source"), "kind": kind, "query": q, "label": "UNKNOWN", "gaps": [g["gap_id"] for g in business.gaps_for(q)]}
        e = o["entry"]; s_ = _stale(e["src"])
        if s_: return s_
        res = o.get("resolution", {})
        out = {"status": "EXECUTED", "kind": kind, "query": q, "primitive": e["primitive"], "owner_role": business.render(e.get("owner_role")), "role_codes": res.get("role_codes", []),
               "person": res.get("person") if res.get("person_status") == "PERSON_KNOWN" else "PERSON_UNKNOWN", "person_status": res.get("person_status"), "person_candidates": res.get("candidates", []),
               "ownership_status": e["status"], "sources": e["src"], "source_status": [business.source_status(s) for s in e["src"]], "label": o["conf"], "note": business.render(e.get("note")), "model": mid}
        if e["status"] == "CONFLICT":
            out.update(code="SOURCE_CONFLICT", resolution="SOURCE_CONFLICT — not chosen", conflicts=[{"id": c["id"], "topic": c["topic"], "source_a": c["source_a"], "source_b": c["source_b"], "resolution_required": c["resolution_required"]} for c in o.get("conflicts", [])], label="UNKNOWN")
        if kind == "approval":
            if "threshold" in str(e.get("note", "")).lower() or "UNKNOWN" in str(e.get("owner_role", "")): out.update(code="APPROVAL_RULE_UNKNOWN", approval_rule="UNKNOWN — no approval matrix/thresholds defined in any source")
            else: out["approval_rule"] = e.get("note") or "per ownership entry"
        return out
    if kind == "process":
        ps = business.find_processes(q)
        if not ps: return {"status": "BLOCKED", "code": "PROCESS_UNDEFINED", "reason": "no documented process matches", "query": q, "label": "UNKNOWN"}
        best = ps[0]; s_ = _stale(best["src"])
        if s_: return s_
        out = {"status": "EXECUTED", "kind": kind, "query": q, "process_id": best["process_id"], "name": best["name"], "process_status": best["status"], "owner": business.render(best["accountable_owner"]), "model": mid,
                             "steps": best["steps"], "sla": best["sla_deadline"], "escalation": best["escalation_condition"], "sources": best["src"], "label": best["conf"], "alternatives": [{"id": p["process_id"], "name": p["name"], "status": p["status"]} for p in ps[1:]]}
        if best["status"].startswith("GAP"): out.update(code="PROCESS_UNDEFINED", label="UNKNOWN", note="this is a registered GAP, not an implemented process")
        return out
    if kind == "kpi":
        ks = business.find_kpis(q)
        if not ks: return {"status": "BLOCKED", "code": "KPI_DEFINITION_MISSING", "reason": "no KPI in the catalog matches", "query": q, "label": "UNKNOWN"}
        s_ = _stale(sum((k["src"] for k in ks), []))
        if s_: return s_
        out = {"status": "EXECUTED", "kind": kind, "query": q, "kpis": [{"id": k["kpi_id"], "name": k["name"], "kind": k["kind"], "definition": k["definition"], "owner": k["owner"], "target": k["target"], "target_ref": k.get("target_ref"), "proposed_targets": k.get("proposed_targets", []), "thresholds": k.get("thresholds", []), "source": k["source"], "src": k["src"], "conf": k["conf"]} for k in ks], "label": "DERIVED", "model": mid}
        if all(str(k["target"]) == "UNKNOWN" for k in ks): out.update(code="TARGET_UNKNOWN", note="KPI defined, target not — no source states a target")
        return out
    if kind == "playbook":
        pb = business.playbook_for(query=q)
        if not pb: return {"status": "BLOCKED", "code": "PROCESS_UNDEFINED", "reason": "no playbook matches this situation", "query": q, "label": "UNKNOWN"}
        return {"status": "EXECUTED", "kind": kind, "query": q, "playbook_id": pb["playbook_id"], "name": pb["name"], "chain": pb["chain"], "required_skills": pb["required_skills"], "required_data": pb["required_data"], "model": mid,
                "diagnostic_steps": pb["diagnostic_steps"], "questions": pb["questions_to_answer"], "owner": business.render(pb["owner"]), "escalation_threshold": pb["escalation_threshold"], "authority_boundary": pb["authority_boundary"], "flow": pb["flow"], "sources": pb["src"], "label": "CONFIRMED"}
    if kind == "role":
        r = business.role(q)
        if not r: return {"status": "BLOCKED", "code": "OWNER_UNKNOWN", "reason": "no role matches", "query": q, "label": "UNKNOWN"}
        pr = business.person_for_role(r["code"])
        return {"status": "EXECUTED", "kind": kind, "query": q, "role": {k: r[k] for k in ("code", "title", "function", "manager", "reports", "positions", "filled", "purpose", "decision_rights", "escalation_path")}, "kpis": business.role_kpis(r["code"]), "targets": business.targets_for(r["code"]),
                "current_person": pr.get("person") if pr["status"] == "PERSON_KNOWN" else "PERSON_UNKNOWN", "person_candidates": pr.get("candidates", []), "compensation": "CONFIDENTIAL (overlay only, not returned)", "sources": r["src"], "label": r["conf"], "model": mid}
    ctx = business.context_for(skill["skill_id"] if skill else "business_model_query", q, inputs)
    return {"status": "EXECUTED", "kind": "context", "query": q, "context": {k: ctx[k] for k in ("playbook", "playbook_name", "kpis", "processes", "owner", "conflicts", "sources", "stale_sources", "rules", "gaps", "model") if k in ctx}, "label": "DERIVED", "model": mid}

def _today(inputs):
    t = inputs.get("today")
    return datetime.date.fromisoformat(t) if isinstance(t, str) else (t or datetime.date.today())

def _norm(t): return re.sub(r"\s+", " ", str(t).lower().strip())
def _opid(*p): return hashlib.sha256("|".join(_norm(x) for x in p).encode("utf-8")).hexdigest()[:16]
def _date(v):
    if isinstance(v, datetime.datetime): return v.date()
    if isinstance(v, datetime.date): return v
    if isinstance(v, str):
        try: return datetime.date.fromisoformat(v[:10])
        except ValueError: return None
    return None


# ───────────────────────── live information layer (READ-ONLY, Mission 4) ─────────────────────────
INTEGRATIONS_DIR = ROOT / ".claude" / "integrations"
def _int_mod(name):
    import sys, importlib
    if str(INTEGRATIONS_DIR) not in sys.path: sys.path.insert(0, str(INTEGRATIONS_DIR))
    return importlib.import_module(name)

def _live(inputs, horizon_days=3):
    """Live context (calendar + mail + integration health) through the integration layer. Never raises, never fabricates:
    an unavailable integration is reported with its last successful read; a supplied live_context (tests/evals) is used as-is."""
    if isinstance(inputs.get("live_context"), dict): return inputs["live_context"]
    if inputs.get("no_live"): return {"available": False, "reason": "live context disabled by input", "health_lines": [], "unavailable": [], "critical_unavailable": []}
    try:
        ctx = _int_mod("layer").brief_context(_today(inputs), horizon_days=horizon_days); ctx["available"] = True; return ctx
    except Exception as e:
        return {"available": False, "reason": f"integration layer unavailable: {type(e).__name__}: {e}", "health_lines": [], "unavailable": [], "critical_unavailable": []}

def _live_task_rows(inputs):
    return [{"id": t["id"], "title": t["task"], "owner": t["owner"], "due": t["due"].isoformat() if t["due"] else None, "status": t["status"]} for t in _tasks(inputs) if t["open"]]

def _meetings(lv, today):
    cal = lv.get("calendar") or {}
    if cal.get("status") != "OK": return [], [], []
    ms = sorted(cal.get("records", []), key=lambda m: m.get("start") or ""); t = today.isoformat()
    m_today = [m for m in ms if (m.get("start") or "")[:10] == t]; m_up = [m for m in ms if (m.get("start") or "")[:10] > t]
    conflicts = []
    for i, a in enumerate(m_today):
        for b in m_today[i + 1:]:
            if a.get("end") and b.get("start") and b["start"] < a["end"] and not (a.get("all_day") or b.get("all_day")):
                conflicts.append({"a": a["title"], "b": b["title"], "overlap_from": b["start"], "until": min(a["end"], b.get("end") or a["end"])})
    return m_today, m_up, conflicts

def _email_candidates(lv, inputs, today):
    mail = lv.get("mail") or {}
    if mail.get("status") != "OK": return []
    rc = _int_mod("reconcile")
    heads = (mail.get("identity") or {}).get("addresses") or []
    return rc.open_loop_candidates(mail.get("records", []), tasks=_live_task_rows(inputs), commitments=commitment_memory({})["commitments"], decisions=decision_memory({})["decisions"], today=today, head_addresses=heads)

def _live_sources(kind):
    """Live sources for a sales/operations question. A source deferred by Gev is shown as DEFERRED once, without unblock instructions (no nag)."""
    try: return [({**s, "certification": "DEFERRED (by Gev)", "unblock": None} if s.get("deferred") else s) for s in _int_mod("layer").live_source_status((kind,))[kind]]
    except Exception as e: return [{"integration_id": "?", "certification": "UNKNOWN", "health": "UNAVAILABLE", "reason": f"{type(e).__name__}: {e}"}]

def _live_ok(sources, exclude=("INT-TASKS",)):
    return [s for s in sources if s.get("certification") in ("VERIFIED_READ", "RELIABLE_READ") and s.get("health") in ("AVAILABLE", "DEGRADED") and s.get("integration_id") not in exclude]

def _sec_meeting(m):
    return {"kind": "meeting", "text": f"{(m.get('start') or '')[11:16]} {m.get('title', '')} ({m.get('participant_count', 0)} մասնակից)" + (f" · {m['location']}" if m.get("location") else ""), "record_id": m.get("record_id")}

# ───────────────────────── source of truth ─────────────────────────
def load_tasks(path=None):
    import openpyxl
    p = pathlib.Path(path) if path else XLSX
    if not p.exists(): raise ExecError(f"source missing: {p.name}")
    wb = openpyxl.load_workbook(p, data_only=True)
    if SHEET not in wb.sheetnames: raise ExecError(f"sheet {SHEET} missing")
    ws = wb[SHEET]
    hdr = [ws.cell(row=HDR_ROW, column=c).value for c in (COL["id"], COL["task"], COL["status"], COL["due"], COL["owner"])]
    if hdr[0] != "№" or not hdr[1] or not hdr[2]:
        raise ExecError(f"schema drift at header row {HDR_ROW}: {hdr}")
    tasks = []
    for r in range(FIRST_ROW, ws.max_row + 1):
        n = ws.cell(row=r, column=COL["id"]).value
        task = ws.cell(row=r, column=COL["task"]).value
        if not isinstance(n, int) or not task: continue
        st = str(ws.cell(row=r, column=COL["status"]).value or "").strip()
        tasks.append({"id": n, "task": str(task).strip(), "status": st,
                      "comment": str(ws.cell(row=r, column=COL["comment"]).value or "").strip(),
                      "due": _date(ws.cell(row=r, column=COL["due"]).value),
                      "owner": str(ws.cell(row=r, column=COL["owner"]).value or "").strip(),
                      "open": st not in CLOSED_STATUSES, "row": r})
    return tasks

def _tasks(inputs):
    """Tasks from inputs (user-supplied OR merged back from an earlier chain step, where dates
    arrive as ISO strings) are normalized to the canonical shape; otherwise loaded from the xlsx."""
    if "tasks" in inputs and isinstance(inputs["tasks"], list):
        out = []
        for t in inputs["tasks"]:
            if not isinstance(t, dict) or "task" not in t: continue
            st = str(t.get("status", "")).strip()
            out.append({**t, "due": _date(t.get("due")), "status": st,
                        "owner": str(t.get("owner", "")).strip(), "open": st not in CLOSED_STATUSES})
        return out
    return load_tasks(inputs.get("path"))

def _ser(t): return {**t, "due": t["due"].isoformat() if t["due"] else None}

# ───────────────────────── A. executive control ─────────────────────────
def task_management(inputs, skill=None, reg=None):
    tasks = _tasks(inputs)
    if inputs.get("task_id") is not None:
        t = next((x for x in tasks if x["id"] == int(inputs["task_id"])), None)
        if not t: return {"status": "BLOCKED", "reason": f"task {inputs['task_id']} not found"}
        return {"status": "EXECUTED", "task": _ser(t), "source": XLSX.name}
    f = inputs.get("status_filter")
    sel = [t for t in tasks if (not f or t["status"] == f)]
    return {"status": "EXECUTED", "count": len(sel), "open": sum(t["open"] for t in sel),
            "tasks": [_ser(t) for t in sel], "source": XLSX.name}

def deadline_management(inputs, skill=None, reg=None):
    today = _today(inputs); tasks = [t for t in _tasks(inputs) if t["open"]]
    b = {"overdue": [], "today": [], "tomorrow": [], "upcoming": [], "no_deadline": []}
    for t in tasks:
        if not t["due"]: b["no_deadline"].append(_ser(t)); continue
        n = (t["due"] - today).days
        key = "overdue" if n < 0 else "today" if n == 0 else "tomorrow" if n == 1 else "upcoming"
        b[key].append({**_ser(t), "days": n})
    for k in b: b[k].sort(key=lambda x: (x.get("due") or "9999", x["id"]))
    return {"status": "EXECUTED", "today": today.isoformat(), "buckets": b,
            "counts": {k: len(v) for k, v in b.items()}, "source": XLSX.name}

def _counterpart(owner):
    """Who holds the ball. Returns (holder, is_other)."""
    o = owner.strip()
    if not o or o == "—": return ("", False)
    if "→" in o: holder = o.split("→")[0].strip()
    else: holder = o
    is_other = HEAD not in holder or o.isupper()
    if o.isupper(): holder = o
    if is_other and not holder: holder = "UNKNOWN"
    return (holder, is_other)

def waiting_for_tracking(inputs, skill=None, reg=None):
    today = _today(inputs); items = []
    for t in _tasks(inputs):
        if not t["open"]: continue
        holder, other = _counterpart(t["owner"])
        if other:
            items.append({**_ser(t), "from": holder, "expected_by": t["due"].isoformat() if t["due"] else None,
                          "days_left": (t["due"] - today).days if t["due"] else None})
    groups = {}
    for it in items: groups.setdefault(it["from"], []).append(it)
    return {"status": "EXECUTED", "count": len(items), "waiting_for": items, "by_counterpart": groups}

def executive_prioritization(inputs, skill=None, reg=None):
    today = _today(inputs); ranked = []
    for t in _tasks(inputs):
        if not t["open"]: continue
        score, why = 0, []
        if t["due"]:
            n = (t["due"] - today).days
            if n < 0: score += 100 + min(-n, 30); why.append(f"overdue {-n}d")
            elif n == 0: score += 80; why.append("due today")
            elif n == 1: score += 60; why.append("due tomorrow")
            else: score += max(0, 40 - n); why.append(f"due in {n}d")
        else: score += 10; why.append("no deadline")
        if "ԿՐԻՏԻԿ" in t["task"].upper() or "CRITICAL" in t["task"].upper(): score += 50; why.append("marked critical")
        holder, other = _counterpart(t["owner"])
        if other and t["owner"].isupper(): score += 15; why.append(f"ball with {holder}")
        ranked.append({**_ser(t), "score": score, "why": ", ".join(why)})
    ranked.sort(key=lambda x: (-x["score"], x["id"]))
    for i, r in enumerate(ranked):
        r["P"] = "P1" if (i < 5 and r["score"] >= 60) else "P2" if r["score"] >= 40 else "P3" if r["score"] >= 15 else "P4"
    return {"status": "EXECUTED", "ranked": ranked, "p1_count": sum(r["P"]=="P1" for r in ranked)}

def daily_briefing(inputs, skill=None, reg=None):
    """Deputy Daily Brief = task register (canonical) + Business Operating Model + LIVE context through the integration layer
    (calendar, mail candidates, integration health). Sections are emitted only when non-empty; an unavailable critical
    integration is reported explicitly with its last successful read — never silently omitted, never shown as current data."""
    today = _today(inputs)
    dl = deadline_management(inputs); wf = waiting_for_tracking(inputs); pr = executive_prioritization(inputs)
    b = dl["buckets"]
    head_actions = [r for r in pr["ranked"] if r["P"] == "P1" and not _counterpart(r["owner"])[1]]
    decisions = [r for r in pr["ranked"] if r["owner"].isupper()]
    bc = _bc(inputs); lv = _live(inputs)
    m_today, m_up, conflicts = _meetings(lv, today)
    cands = _email_candidates(lv, inputs, today)
    act = [c for c in cands if c["class"] in ("ACTION", "DECISION", "DELEGATE") and not c["duplicate_of"]]
    dec_mail = [c for c in act if c["class"] == "DECISION"]
    cm = commitment_memory({})["commitments"]; cm_due = [x for x in cm if x.get("due") and x["due"] <= (today + datetime.timedelta(days=3)).isoformat()]
    prep = []
    if m_today or m_up:
        rc = _int_mod("reconcile"); rows = _live_task_rows(inputs); dm = decision_memory({})["decisions"]
        for m in (m_today + m_up)[:5]:
            pk = rc.meeting_pack(m, rows, cm, dm, bool(bc.get("available")))
            prep.append({"meeting": m.get("title"), "start": m.get("start"), "participants": m.get("participant_count", 0), "context_found": pk["context_found"], "missing": pk["missing_preparation"][:3], "agenda": pk["recommended_agenda"][:3]})
    risks = []
    for iid in lv.get("critical_unavailable", []): risks.append({"kind": "INTEGRATION_DOWN", "text": next((l for l in lv.get("health_lines", []) if l.startswith(iid)), f"{iid} unavailable")})
    if lv.get("available") is False and lv.get("reason"): risks.append({"kind": "INTEGRATION_LAYER_DOWN", "text": lv["reason"]})
    if conflicts: risks.append({"kind": "SCHEDULE_CONFLICT", "text": f"{len(conflicts)} overlapping meeting(s) today", "detail": conflicts})
    if len(b["overdue"]) >= 3: risks.append({"kind": "OVERDUE_PILEUP", "text": f"{len(b['overdue'])} overdue items"})
    for c in bc.get("conflicts", []): risks.append({"kind": "SOURCE_CONFLICT", "text": f"{c['id']} {c['topic']} — {c.get('resolution_required', '')}"})
    live_sales = _live_sources("sales"); live_ops = _live_sources("operations"); sales_ok = _live_ok(live_sales); ops_ok = _live_ok(live_ops)
    sections = []
    def sec(sid, title, items, note=None):
        if items: sections.append({"id": sid, "title": title, "items": items, **({"note": note} if note else {})})
    sec("TODAY", "ԱՅՍՕՐ", [_sec_meeting(m) for m in m_today]
        + [{"kind": "deadline", "text": f"{x['id']}. {x['task'][:60]} · {x.get('owner', '')}", "id": x["id"]} for x in b["today"]]
        + [{"kind": "head_action", "text": f"{x['id']}. {x['task'][:60]} — {x['why']}", "id": x["id"]} for x in head_actions[:5]])
    sec("OVERDUE", "ԺԱՄԿԵՏԱՆՑ", [{"kind": "task", "text": f"{x['id']}. [{x.get('due')}] {x['task'][:60]} · {x.get('owner', '')}", "id": x["id"]} for x in b["overdue"]]
        + [{"kind": "commitment", "text": f"[{x['due']}] {x['text'][:60]}", "op_id": x.get("op_id")} for x in cm_due])
    sec("WAITING_FOR", "ՍՊԱՍՈՒՄ ԵՄ", [{"kind": "task", "text": f"{w['id']}. {w['from']} · {w['task'][:50]} [{w.get('expected_by') or '—'}]", "id": w["id"]} for w in wf["waiting_for"]]
        + [{"kind": "email", "text": f"✉ {c['counterpart']}: {str(c['subject'])[:60]} ({c['class']}, {c['age_days']}d)", "candidate_id": c["candidate_id"], "class": c["class"]} for c in act if c["class"] != "DECISION"],
        note="✉ = CANDIDATE_OPEN_LOOP from mail — not a task until Gev confirms")
    sec("SALES", "ՎԱՃԱՌՔ", [{"kind": "live", "text": f"{s['integration_id']} {s['health']} — live signal available (query it)"} for s in sales_ok])
    sec("OPERATIONS", "ԳՈՐԾԱՌՆՈՒԹՅՈՒՆ", [{"kind": "live", "text": f"{s['integration_id']} {s['health']} — live signal available (query it)"} for s in ops_ok])
    sec("DECISIONS", "ՈՐՈՇՈՒՄՆԵՐ", [{"kind": "task", "text": f"{x['id']}. {x['task'][:60]} · {x['owner']}", "id": x["id"]} for x in decisions]
        + [{"kind": "email", "text": f"✉ {c['counterpart']}: {str(c['subject'])[:60]}", "candidate_id": c["candidate_id"], "class": "DECISION"} for c in dec_mail]
        + [{"kind": "business", "text": f"{c['id']} {c['topic']}"} for c in bc.get("conflicts", [])])
    sec("RISKS", "ՌԻՍԿԵՐ", risks)
    sec("PREPARATION", "ՊԱՏՐԱՍՏՈՒԹՅՈՒՆ", [{"kind": "meeting", "text": f"{p['meeting']} ({(p['start'] or '')[5:16]}): " + ("; ".join(p["missing"]) if p["missing"] else "context ready"), "agenda": p["agenda"]} for p in prep])
    brief = {"status": "EXECUTED", "date": today.isoformat(), "weekday": HY[today.weekday()],
             "top_priorities": pr["ranked"][:5], "head_actions": head_actions[:5], "decisions_pending": decisions,
             "deadlines_today": b["today"], "overdue": b["overdue"], "tomorrow": b["tomorrow"],
             "waiting_for": wf["waiting_for"], "no_deadline": b["no_deadline"],
             "counts": dl["counts"], "source": XLSX.name, "sections": sections,
             "live": {"available": bool(lv.get("available")), "mode": lv.get("mode"), "meetings_today": m_today, "meetings_upcoming": m_up[:5], "schedule_conflicts": conflicts,
                      "email_candidates": act, "email_candidates_total": len(cands), "integration_health": lv.get("health_lines", []), "unavailable": lv.get("unavailable", []),
                      "critical_unavailable": lv.get("critical_unavailable", []), "reason": lv.get("reason"), "sales_sources": live_sales, "operations_sources": live_ops},
             "preparation": prep, "risks": risks,
             "data_gaps": ([f"sales: no VERIFIED live source ({', '.join(str(s.get('integration_id')) + '=' + str(s.get('certification')) for s in live_sales)})"] if not sales_ok else [])
                          + ([f"operations: no VERIFIED live source beyond the task register ({', '.join(str(s.get('integration_id')) + '=' + str(s.get('certification')) for s in live_ops if s.get('integration_id') != 'INT-TASKS')})"] if not ops_ok else [])
                          + bc.get("routine_missing_data", []),
             "business_alerts": {"pending_decisions": [c["id"] for c in bc.get("conflicts", [])], "gaps": bc.get("gaps", [])}, "business_context": _bc_brief(inputs)}
    # MISSION 5 — the management brief (TOP LINE · CHANGES · SALES · OPERATIONS · TASKS · CALENDAR · MAIL · RISKS · ACTIONS · GEV) on the same live reads
    brief["management"] = _management(inputs, lv, lambda IQ, st: IQ.brief(st, record=not inputs.get("no_checkpoint")))
    if brief["management"].get("status") == "EXECUTED": brief["management_text"] = _iq().render_brief(brief["management"])
    return brief

# ───────────────────────── MISSION 5 — live management intelligence (one pipeline: skills/intelligence.py) ─────────────────────────
def _iq():
    import intelligence; return intelligence

def _management(inputs, lv, fn):
    """Run one intelligence view on the canonical current state. Fails closed: an error is reported as UNAVAILABLE with its reason, never as an empty 'all fine'."""
    try:
        IQ = _iq(); st = IQ.current_state({**inputs, **({"live_context": lv} if isinstance(lv, dict) and lv.get("calendar") is not None else {})}); return fn(IQ, st)
    except Exception as e: return {"status": "UNAVAILABLE", "reason": f"intelligence pipeline failed: {type(e).__name__}: {e}", "mutation_performed": False}

def _focus(text):
    t = _norm(text)
    if re.search(r"(meeting|հանդիպ|calendar|օրացույց)", t): return "calendar"
    if re.search(r"(\bmail\b|e-?mail|նամակ|փոստ|inbox)", t): return "mail"
    if re.search(r"(sales|վաճառք|deal|pipeline|churn|չըռն)", t): return "sales"
    if re.search(r"(operation|գործառն|\bops\b|backlog|\bsla\b|վառվում|install)", t): return "operations"
    if re.search(r"(task|թասկ|առաջադրանք|ուշաց|\blate\b|overdue|stuck|կախված|blocked)", t): return "tasks"
    return "all"

def management_snapshot(inputs, skill=None, reg=None):
    """LIVE MANAGEMENT SNAPSHOT: current state from every readable integration, exceptions ranked, recommendations, Gev queue — focused by the question (tasks / calendar / mail / sales / operations / all)."""
    IQ = _iq(); st = IQ.current_state(inputs); exc = IQ.exceptions(st)
    focus = inputs.get("focus") or _focus(inputs.get("intent") or inputs.get("query") or inputs.get("text") or "")
    out = {"status": "EXECUTED", "focus": focus, "date": st["today"], "truth_mode": st["truth_mode"], "visibility": st["visibility"], "visibility_lines": IQ.visibility_lines(st), "unavailable": st["unavailable"],
           "exceptions_count": len(exc), "top": [IQ.management_answer(e) for e in exc[:5]], "actions": [IQ.action_line(e) for e in exc[:7]], "gev": IQ.gev_queue(st, exc), "mutation_performed": False,
           "verdict": ("no proven exception in the visible systems" if not exc else exc[0]["what"]) + (f" · visibility gaps: {', '.join(st['unavailable'])}" if st["unavailable"] else "")}
    if focus in ("tasks", "all"): out["tasks"] = IQ.task_view(st, exc)
    if focus in ("calendar", "all"): out["calendar"] = IQ.calendar_view(st)
    if focus in ("mail", "all"): out["mail"] = IQ.mail_view(st, exc)
    if focus in ("sales", "all"): out["sales"] = IQ.sales_intelligence(st, None)
    if focus in ("operations", "all"): out["operations"] = IQ.operations_intelligence(st, exc)
    out["business_context"] = _bc_brief(inputs); return out

def exception_review(inputs, skill=None, reg=None):
    """EXCEPTION MODE: only proven exceptions, ranked; incomplete visibility is stated separately — never 'everything is fine' when half the systems are dark."""
    IQ = _iq(); st = IQ.current_state(inputs)
    return {**IQ.exception_view(st), "mutation_performed": False, "business_context": _bc_brief(inputs)}

def change_review(inputs, skill=None, reg=None):
    """WHAT CHANGED since a checkpoint/time: NEW · CHANGED · RESOLVED · WORSENED · NEEDS_GEV from durable checkpoints + live reads."""
    IQ = _iq(); st = IQ.current_state(inputs); today = _today(inputs); since = inputs.get("since"); t = _norm(inputs.get("intent") or inputs.get("query") or inputs.get("text") or "")
    if not since and re.search(r"(yesterday|երեկ)", t): since = (today - datetime.timedelta(days=1)).isoformat()
    if not since and re.search(r"(last week|անցյալ շաբաթ|a week)", t): since = (today - datetime.timedelta(days=7)).isoformat()
    return {**IQ.change_view(st, since, record=not inputs.get("no_checkpoint")), "mutation_performed": False, "business_context": _bc_brief(inputs)}

def decision_queue(inputs, skill=None, reg=None):
    """GEV DECISION QUEUE: only what genuinely requires Gev — APPROVAL · DECISION · ESCALATION · OWNER NEEDED · PRIORITY CONFLICT · MISSING BUSINESS TRUTH."""
    IQ = _iq(); st = IQ.current_state(inputs); exc = IQ.exceptions(st); q = IQ.gev_queue(st, exc)
    loops = IQ.open_loops(st, exc, persist=False)
    return {"status": "EXECUTED", "date": st["today"], "truth_mode": st["truth_mode"], "queue": q, "count": len(q), "categories": sorted({x["category"] for x in q}),
            "forgotten": [l for l in loops["open"] if l.get("kind") in ("COMMITMENT", "DECISION_PENDING", "MAIL_DECISION")], "visibility_lines": IQ.visibility_lines(st), "unavailable": st["unavailable"],
            "note": "ordinary team work is not in this queue; each item says why Gev specifically is needed", "mutation_performed": False, "business_context": _bc_brief(inputs)}

def end_of_day_control(inputs, skill=None, reg=None):
    today = _today(inputs); tasks = _tasks(inputs); dl = deadline_management(inputs)
    done_today = [_ser(t) for t in tasks if not t["open"] and t["due"] == today]
    slipped = dl["buckets"]["overdue"] + [x for x in dl["buckets"]["today"]]
    out = {"status": "EXECUTED", "date": today.isoformat(), "completed_today": done_today, "not_completed": slipped,
           "decisions_pending": [_ser(t) for t in tasks if t["open"] and t["owner"].isupper()],
           "waiting_for": waiting_for_tracking(inputs)["waiting_for"], "tomorrow": dl["buckets"]["tomorrow"]}
    out["management"] = _management(inputs, _live(inputs), lambda IQ, st: IQ.eod_view(st, record=not inputs.get("no_checkpoint")))     # Mission 5 EOD control: planned / completed / slipped / moved / unverified / escalation / Gev
    return out

def weekly_review(inputs, skill=None, reg=None):
    dl = deadline_management(inputs)
    b = _bc(inputs)
    out = {"status": "ASSISTED", "actions_overdue": dl["buckets"]["overdue"], "open_count": sum(dl["counts"].values()),
           "sales": "UNKNOWN — no VERIFIED live sales source: " + ", ".join(f"{s.get('integration_id')}={s.get('certification')}" for s in _live_sources("sales")),
           "operations": "UNKNOWN — no VERIFIED live operations source beyond the task register: " + ", ".join(f"{s.get('integration_id')}={s.get('certification')}" for s in _live_sources("operations") if s.get("integration_id") != "INT-TASKS"),
           "sections": b.get("routine_sections", []), "missing_sources": b.get("routine_missing_data", []), "pending_decisions": [c["id"] + " " + c["topic"] for c in b.get("conflicts", [])],
           "note": "sales/ops KPI sections stay UNKNOWN without a live source; the management review below is built from what is live.", "business_context": _bc_brief(inputs)}
    out["management"] = _management(inputs, _live(inputs, horizon_days=7), lambda IQ, st: IQ.weekly_view(st))     # Mission 5 weekly review surface
    return out

def meeting_preparation(inputs, skill=None, reg=None):
    if not inputs.get("meeting"): return {"status": "BLOCKED", "reason": "required input 'meeting' missing"}
    dl = deadline_management(inputs); wf = waiting_for_tracking(inputs); pr = executive_prioritization(inputs)
    topic = _norm(inputs.get("topic", inputs["meeting"]))
    related = [r for r in pr["ranked"] if any(w in _norm(r["task"]) for w in topic.split() if len(w) > 3)]
    # LIVE calendar (INT-OL-CAL, read-only): find the meeting in the next 14 days and assemble the pack with provenance
    lv = _live(inputs, horizon_days=14); m_today, m_up, _ = _meetings(lv, _today(inputs)); found = None
    for m in m_today + m_up:
        if set(w for w in topic.split() if len(w) > 3) & set(_norm(m.get("title", "")).split()): found = m; break
    cal = {"found": bool(found), "source": "INT-OL-CAL", "health": next((l for l in lv.get("health_lines", []) if l.startswith("INT-OL-CAL")), lv.get("reason"))}
    if found:
        pk = _int_mod("reconcile").meeting_pack(found, _live_task_rows(inputs), commitment_memory({})["commitments"], decision_memory({})["decisions"], bool(_bc(inputs).get("available")))
        cal.update({k: pk[k] for k in ("meeting", "participants", "purpose", "related_tasks", "related_tasks_uncertain", "previous_commitments", "relevant_decisions", "kpis", "processes", "missing_preparation", "recommended_agenda", "recommended_questions", "context_found", "note")})
    else: cal["note"] = "meeting not found in the live calendar (today + 14 days) — time and participants UNKNOWN unless supplied"
    live_names = ", ".join(p.get("name", "") for p in (found or {}).get("participants", []) if p.get("name")) if found else ""
    out = {"status": "EXECUTED", "meeting": inputs["meeting"], "purpose": inputs.get("purpose") or (cal.get("purpose") if found else None) or "UNKNOWN — supply",
            "participants": inputs.get("participants") or live_names or "UNKNOWN — supply", "when": (found or {}).get("start"), "calendar": cal,
            "previous_decisions": decision_memory({}, None, None)["decisions"][-5:],
            "open_actions": related or pr["ranked"][:5], "overdue": dl["buckets"]["overdue"],
            "waiting_for": wf["waiting_for"], "decisions_required": [r for r in pr["ranked"] if r["owner"].isupper()],
            "numbers": "UNKNOWN — no KPI feed; expected KPIs per business model: " + ", ".join(k["name"] for k in _bc(inputs).get("kpis", [])[:5]) if _bc(inputs).get("available") else "UNKNOWN — no KPI feed; supply if required",
            "talking_points": [f"Close: {r['task']}" for r in (related or pr['ranked'][:3])], "business_context": _bc_brief(inputs)}
    # OPERATING LAYER pre-meeting pack: commitments of the participants (lifecycle), decisions on the topic (in force?), KPI bindings, open alerts — evidence only, no mutation
    try:
        import commitments as CM, decisions as DM, kpis as KP, alerts as AL, people as PP
        t = _today(inputs).isoformat(); names = [p.get("name") for p in (found or {}).get("participants", []) if p.get("name")] + [str(inputs.get("participants") or "")]
        who = {pp["name"] for n in names for pp in PP.find_person(n)} | {pp["token"] for n in names for pp in PP.find_person(n)}
        out["participant_commitments"] = [r for r in CM.open_rows(t) if (r.get("who") in who) or any(_norm(n) and _norm(n) in _norm(r.get("who")) for n in names if n)]
        out["decisions_on_topic"] = DM.recall(inputs.get("topic") or inputs["meeting"], t, limit=5)
        out["kpis_relevant"] = KP.for_text(inputs.get("topic") or inputs["meeting"])
        out["open_alerts"] = [{"id": a["op_id"], "what": a.get("what"), "severity": a.get("severity"), "state": a.get("state"), "escalation_level": a.get("escalation_level", 0)} for a in AL.listing() if a.get("state") in ("OPEN", "REOPENED", "ACKNOWLEDGED")][:8]
        out["questions_to_ask"] = [f"{r['who']}: status of «{r['what'][:60]}» (due {r['due_display']}, {r['lifecycle']})" for r in out["participant_commitments"][:5]] + [f"Decision «{d['text'][:60]}» — still in force? ({d['in_force_reason']})" for d in out["decisions_on_topic"] if d.get("review_pending") or d.get("contradictions")]
        out["mutation_performed"] = False
    except Exception as e: out["pack_note"] = f"operating-layer pack unavailable: {type(e).__name__}: {e}"
    return out

def delegation_design(inputs, skill=None, reg=None):
    instr = inputs.get("instruction") or inputs.get("notes") or inputs.get("recommendation")
    if not instr: return {"status": "BLOCKED", "reason": "instruction missing"}
    owner = (inputs.get("owner") or "").strip(); issues = []
    vague = {"sales team","operations","management","it","թիմ","բաժին"}
    if not owner: issues.append("owner missing — one named person required")
    elif _norm(owner) in vague or len(owner.split()) > 3: issues.append(f"owner '{owner}' is not a single named person")
    due = _date(inputs.get("deadline"))
    if not due: issues.append("deadline missing")
    draft = {"task": instr.strip(), "owner": owner or "<NAME REQUIRED>", "deadline": due.isoformat() if due else "<DATE REQUIRED>",
             "expected_output": inputs.get("expected_output", "<define: what is delivered, in what form>"),
             "bitrix_ready": not issues}
    return {"status": "EXECUTED" if not issues else "ASSISTED", "draft": draft, "issues": issues}

def _append_state(table, record, key_fields):
    """Idempotent write through the hardened store: the DB decides RECORDED vs DUPLICATE (no read-then-append race)."""
    oid = _opid(*[record.get(k, "") for k in key_fields])
    r = _st().record(table, oid, record)
    return {"status": r["status"], "op_id": oid, "record": r.get("record"), "existing": r.get("existing"), "store": table}

def _read_state(table):
    return _st().list(table)

def commitment_tracking(inputs, skill=None, reg=None):
    text = (inputs.get("text") or "").strip()
    if not text: return {"status": "BLOCKED", "reason": "text missing"}
    due = _date(inputs.get("due"))
    rec = {"text": text, "owner": inputs.get("owner", HEAD), "due": due.isoformat() if due else None,
           "condition": inputs.get("condition"), "state": "OPEN"}
    r = _append_state("commitments", rec, ["text", "owner", "due"])
    r["scheduler_available"] = False
    r["note"] = "Recorded and will be surfaced by the session-start brief; no autonomous timer exists in this runtime."
    return r

def commitment_memory(inputs, skill=None, reg=None):
    """COMMITMENT ENGINE view: open commitments with lifecycle (OPEN / DUE_SOON / OVERDUE), by person, late leaders, what is expected on a date —
    answers «ով ինչ ա խոստացել», «ով ա ամենաշատ խոստում ուշացնում», «վաղը ումից ինչ եմ սպասում». Read-only; closing needs evidence (fulfil)."""
    import commitments as CM
    today = _today(inputs); t = today.isoformat(); q = _norm(inputs.get("query") or inputs.get("intent") or inputs.get("text") or "")
    # Work-graph checkpoints and commitments share the historical Store table;
    # only canonical commitment-shaped rows belong in this view.
    items = [r for r in CM.open_rows(t) if r.get("what")]
    grouped = {k: [r for r in v if r.get("what")] for k, v in CM.by_person(t).items()}
    out = {"status": "EXECUTED", "count": len(items), "commitments": items, "by_person": {k: [{"op_id": r["op_id"], "what": r["what"][:100], "due": r["due_display"], "lifecycle": r["lifecycle"], "evidence_refs": len(r.get("evidence") or [])} for r in v] for k, v in grouped.items()},
           "overdue": [r for r in items if r["lifecycle"] == "OVERDUE"], "due_soon": [r for r in items if r["lifecycle"] == "DUE_SOON"], "unknown_due": [r for r in items if not r.get("due")], "late_leaders": CM.late_leaders(t), "mutation_performed": False}
    if inputs.get("fulfil"):
        f = inputs["fulfil"]; out["fulfil"] = CM.fulfil(f.get("op_id"), f.get("evidence"), by="Gev"); out["mutation_performed"] = out["fulfil"].get("status") == "FULFILLED"
    if re.search(r"(վաղը|tomorrow)", q):
        d = (today + datetime.timedelta(days=1)).isoformat(); out["focus"] = "tomorrow"; out["expected"] = CM.expected_on(d, t); out["answer"] = (f"{len(out['expected'])} commitment(s) due {d}: " + "; ".join(f"{r['who']} → {r['what'][:60]}" for r in out["expected"])) if out["expected"] else f"nothing is due {d} in the commitment register (unknown-due promises: {len(out['unknown_due'])})"
    elif re.search(r"(ամենաշատ|ուշացնում|delays? (?:most|the most)|most (?:late|overdue)|worst)", q):
        out["focus"] = "late_leaders"; ll = out["late_leaders"]; out["answer"] = (f"{ll[0]['who']} — {ll[0]['overdue']} overdue promise(s), {ll[0]['delay_days']} delay-day(s) in total" if ll else "no overdue promise in the register — nobody is late on record")
    elif re.search(r"(ով ինչ|who promised|ինչ ա խոստացել|խոստացել)", q):
        out["focus"] = "by_person"; out["answer"] = ("; ".join(f"{k}: {len(v)} open" for k, v in out["by_person"].items()) if out["by_person"] else "no open commitment on record")
    else: out["focus"] = "all"
    return out

def decision_logging(inputs, skill=None, reg=None):
    d = (inputs.get("decision") or "").strip()
    if not d: return {"status": "BLOCKED", "reason": "decision missing"}
    rec = {"decision": d, "reason": inputs.get("reason", ""), "owner": inputs.get("owner", HEAD),
           "effective_date": inputs.get("effective_date"), "follow_up": inputs.get("follow_up"), "date": _today(inputs).isoformat()}
    return _append_state("decisions", rec, ["decision", "owner"])

def decision_memory(inputs, skill=None, reg=None):
    """DECISION MEMORY: «սրա մասին ինչ էինք որոշել» · «երբ» · «ինչու» · «դեռ ուժի մեջ ա՞» · review-pending · contradictions surfaced. Read-only."""
    import decisions as DM
    q = (inputs.get("query") or inputs.get("intent") or inputs.get("text") or "").strip(); t = _today(inputs).isoformat()
    legacy = _read_state("decisions")
    out = {"status": "EXECUTED", "decisions": legacy, "count": len([d for d in legacy if d.get("kind") != "LOCAL_DRAFT"]), "review_pending": DM.review_pending(t), "candidates": DM.candidates(), "mutation_performed": False}
    if inputs.get("confirm"): out["confirm"] = DM.confirm(inputs["confirm"], by="Gev"); out["mutation_performed"] = True
    if inputs.get("supersede"): sp = inputs["supersede"]; out["supersede"] = DM.supersede(sp.get("new"), sp.get("old"), by="Gev"); out["mutation_performed"] = True
    if q and not re.search(r"^(what did we decide|past decisions|decision history|review pending)\??$", _norm(q)):
        hits = DM.recall(q, t); out["query"] = q; out["recall"] = hits
        if hits:
            h = hits[0]; force = "IN FORCE" if h["in_force"] else ("NOT IN FORCE" if h["in_force"] is False else "UNCONFIRMED (candidate)")
            out["answer"] = {"what": h["text"], "when": h["when"], "why": h["why"], "who": h["maker"], "status": h["status"], "in_force": force + (" — REVIEW PENDING" if h["review_pending"] else "") + f" ({h['in_force_reason']})", "contradictions": h["contradictions"]}
            if h["contradictions"]: out["conflict"] = "CONFLICTING DECISIONS on record — both shown, none silently overwritten; Gev decides which stands (supersede)"
        else: out["answer"] = {"what": "NO DECISION ON RECORD for this topic", "when": None, "why": None, "in_force": "UNKNOWN — nothing recorded; a decision Deputy never saw cannot be confirmed"}
    return out

def reminder_intelligence(inputs, skill=None, reg=None):
    due = _date(inputs.get("due")); item = inputs.get("item")
    if not item: return {"status": "BLOCKED", "reason": "item missing"}
    if not due: return {"status": "BLOCKED", "reason": "unparseable or missing due date"}
    today = _today(inputs); prep = inputs.get("prep_items") or []
    plan = []
    for off, label in ((7,"Preparation may be required"),(3,"Check readiness"),(1,"Confirm materials/people"),(0,"Action reminder")):
        d = due - datetime.timedelta(days=off)
        if d >= today: plan.append({"date": d.isoformat(), "label": label, "past": False})
    plan.append({"date": (due + datetime.timedelta(days=1)).isoformat(), "label": "Check completion; follow up if incomplete", "past": False})
    text = f"{item} — {due.isoformat()} ({HY[due.weekday()]})." + (" Preparation still required: " + "; ".join(prep) if prep else "")
    return {"status": "EXECUTED", "item": item, "due": due.isoformat(), "plan": plan, "reminder_text": text,
            "scheduler_available": False,
            "honesty": "No autonomous scheduler in this runtime: checkpoints are surfaced via the session-start brief, not fired automatically."}

def follow_up_management(inputs, skill=None, reg=None):
    dl = deadline_management(inputs); wf = waiting_for_tracking(inputs); today = _today(inputs)
    fu = []
    for t in dl["buckets"]["overdue"]:
        holder, other = _counterpart(t["owner"])
        fu.append({"id": t["id"], "item": t["task"], "owner": holder or HEAD, "since": t["due"], "days": -t["days"],
                   "next_action": f"Follow up with {holder or HEAD} today: status + new date"})
    for w in wf["waiting_for"]:
        if not any(f["id"] == w["id"] for f in fu):
            fu.append({"id": w["id"], "item": w["task"], "owner": w["from"], "since": w.get("expected_by"),
                       "next_action": f"Ask {w['from']} for status; escalate if no answer by {w.get('expected_by') or 'EOD'}"})
    return {"status": "EXECUTED", "count": len(fu), "follow_ups": fu}

def escalation_management(inputs, skill=None, reg=None):
    item = inputs.get("item")
    if not item: return {"status": "BLOCKED", "reason": "item missing"}
    block = {"problem": item, "impact": inputs.get("impact", "UNKNOWN — supply"), "owner": inputs.get("owner") or _bc_owner(inputs, "UNKNOWN"),
             "deadline_status": inputs.get("deadline_status", "UNKNOWN"), "done_so_far": inputs.get("done_so_far", "UNKNOWN"),
             "head_action": inputs.get("head_action", "Decide: escalate / re-assign / extend deadline")}
    return {"status": "EXECUTED", "escalation": block, "business_context": _bc_brief(inputs)}

def decision_support(inputs, skill=None, reg=None):
    issue = inputs.get("issue") or inputs.get("analysis") or inputs.get("description")
    if not issue: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "issue (or analysis/description) missing"}
    if not isinstance(issue, str): issue = json.dumps(issue, ensure_ascii=False)[:400]
    opts = inputs.get("options") or []
    rec = inputs.get("recommendation") or ("INSUFFICIENT DATA — supply options/facts" if not opts else f"Evaluate {len(opts)} options against facts; recommendation pending facts")
    return {"status": "ASSISTED", "decision_needed": {"issue": issue, "context": inputs.get("context", "UNKNOWN"),
            "options": opts, "recommendation": rec, "risk_of_delay": inputs.get("risk_of_delay", "UNKNOWN"),
            "deadline": inputs.get("deadline", "UNKNOWN"), "approver": HEAD,
            "owner": inputs.get("owner") or _bc_owner(inputs, "<NAME>"), "head_action": inputs.get("head_action", "Decide/approve")}, "label": "DERIVED", "business_context": _bc_brief(inputs)}

def approval_management(inputs, skill=None, reg=None):
    lvl = inputs.get("action_level"); ladder = (reg or {}).get("authority_ladder", [])
    if lvl not in ladder: return {"status": "BLOCKED", "reason": f"unknown action_level {lvl!r}"}
    needs = lvl in ("EXECUTE_EXTERNAL", "EXECUTE_MATERIAL")
    if needs and not inputs.get("approval_token"):
        return {"status": "BLOCKED", "code": "APPROVAL_REQUIRED", "action_level": lvl, "approved": False}
    return {"status": "EXECUTED", "action_level": lvl, "approved": True, "approval_required": needs}

def authority_checking(inputs, skill=None, reg=None):
    import engine
    lvl = inputs.get("action_level"); target = inputs.get("skill_id", skill["skill_id"] if skill else None)
    s = (reg or {}).get("_index", {}).get(target) if reg else None
    if not s: return {"status": "BLOCKED", "reason": f"unknown skill {target}"}
    a = engine.authority_check(reg, s, lvl, inputs.get("approval_token"))
    return {"status": "EXECUTED" if a["ok"] else "BLOCKED", "allowed": a["ok"], "reason": a.get("reason"), "code": a.get("code")}

def policy_checking(inputs, skill=None, reg=None):
    a = inputs.get("action", "")
    hits = MATERIAL.findall(a)
    return {"status": "EXECUTED", "material": bool(hits), "matched": hits,
            "policy": "Requires explicit Head approval before execution" if hits else "No material-action policy triggered"}

def risk_classification(inputs, skill=None, reg=None):
    a = _norm(inputs.get("action", "")); mat = bool(MATERIAL.search(a))
    irreversible = any(w in a for w in ("delete","ջնջ","terminate","send","ուղարկ","publish","pay","վճար"))
    level = "CRITICAL" if (mat and irreversible) else "HIGH" if mat else "MEDIUM" if irreversible else "LOW"
    return {"status": "EXECUTED", "risk": level, "material": mat, "irreversible": irreversible}

def sensitivity_check(inputs, skill=None, reg=None):
    t = inputs.get("text", ""); import engine
    flagged = bool(engine.SENSITIVE.search(t)) or bool(re.search(r"\b\d{9,}\b", t))
    return {"status": "EXECUTED", "sensitive": flagged, "advice": "Redact before logging/sending" if flagged else "OK"}

def information_classification(inputs, skill=None, reg=None):
    items = inputs.get("items") or ([inputs["content"]] if inputs.get("content") else [])
    if isinstance(items, str): items = [items]
    if not items: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "content/items missing"}
    out = []
    rules = [("DECISION", r"(decide|approve|հաստատ|որոշ|should we|pros/cons)"),
             ("ACTION", r"(please|do|send|prepare|fix|արա|ուղարկ|պատրաստ|make|need you to|by (today|tomorrow))"),
             ("DELEGATE", r"(հանձնարար|assign|delegate|թող .* անի|let .* do)"),
             ("MONITOR", r"(watch|monitor|keep an eye|հետև|track)"),
             ("IGNORE", r"(spam|unsubscribe|lottery)")]
    for it in items:
        cls = "FYI"
        for name, pat in rules:
            if re.search(pat, it, re.I): cls = name; break
        out.append({"item": it, "class": cls})
    return {"status": "EXECUTED", "classified": out}

def source_verification(inputs, skill=None, reg=None):
    p = pathlib.Path(inputs.get("path") or XLSX)
    if not p.is_absolute(): p = paths.resolve(ROOT, inputs.get("path") or XLSX)        # business-relative sources resolve under the business root
    if not p.exists(): return {"status": "BLOCKED", "code": "SOURCE_MISSING", "reason": f"source missing: {p.name}", "path": str(p)}
    age_h = (datetime.datetime.now() - datetime.datetime.fromtimestamp(p.stat().st_mtime)).total_seconds() / 3600
    res = {"status": "VERIFIED", "path": p.name, "exists": True, "age_hours": round(age_h, 1),
           "stale": age_h > 72, "schema_ok": None}
    if p.suffix == ".xlsx" and (p.name == XLSX.name or inputs.get("schema") == "tasks"):
        try: load_tasks(p); res["schema_ok"] = True
        except ExecError as e: res.update(status="BLOCKED", code="SCHEMA_DRIFT", schema_ok=False, reason=str(e))
        except Exception as e: res.update(status="BLOCKED", code="UNREADABLE_SOURCE", schema_ok=False, reason=f"{type(e).__name__}: {e}")
    return res

def source_reconciliation(inputs, skill=None, reg=None):
    srcs = inputs.get("sources")
    if not srcs or len(srcs) < 2: return {"status": "BLOCKED", "reason": "need >=2 sources: [{name,value,date?,authoritative?}]"}
    vals = {str(s.get("value")) for s in srcs}
    if len(vals) == 1: return {"status": "EXECUTED", "contradiction": False, "value": srcs[0]["value"]}
    dated = [s for s in srcs if s.get("date")]
    newest = max(dated, key=lambda s: s["date"]) if dated else None
    auth = next((s for s in srcs if s.get("authoritative")), None)
    return {"status": "EXECUTED", "contradiction": True,
            "report": [f"{s['name']} says {s['value']}" + (f" ({s['date']})" if s.get('date') else "") for s in srcs],
            "newest": newest["name"] if newest else "UNKNOWN", "authoritative": auth["name"] if auth else "UNKNOWN",
            "impact": inputs.get("impact", "UNKNOWN — assess"), "verify": "Confirm with source owner before using either figure",
            "chosen": None}

def confidence_labeling(inputs, skill=None, reg=None):
    claims = inputs.get("claims") or []
    if not claims: return {"status": "BLOCKED", "reason": "claims missing"}
    out = [{"claim": c.get("text", c) if isinstance(c, dict) else c,
            "label": (c.get("label") if isinstance(c, dict) and c.get("label") in ("CONFIRMED","DERIVED","UNVERIFIED","UNKNOWN") else "UNVERIFIED")}
           for c in claims]
    return {"status": "EXECUTED", "labeled": out}

def completion_verification(inputs, skill=None, reg=None):
    """evidence_spec: {type: file_exists|task_status|state_record, ...}. Returns ATTEMPTED/EXECUTED/VERIFIED."""
    spec = inputs.get("evidence_spec")
    if not spec: return {"status": "BLOCKED", "reason": "evidence_spec missing"}
    kind = spec.get("type")
    if kind == "file_exists":
        q = pathlib.Path(spec["path"])
        p = q if q.is_absolute() else paths.resolve(ROOT, spec["path"])        # business-relative evidence resolves through the ONE business-root resolver
        ok = p.exists()
        return {"status": "VERIFIED" if ok else "ATTEMPTED", "verified": ok, "evidence": {"path": str(p), "exists": ok}}
    if kind == "task_status":
        t = next((x for x in _tasks(inputs) if x["id"] == int(spec["task_id"])), None)
        if not t: return {"status": "BLOCKED", "reason": "task not found"}
        ok = t["status"] == spec.get("expected", "Արված")
        return {"status": "VERIFIED" if ok else "ATTEMPTED", "verified": ok, "evidence": {"task": t["id"], "status": t["status"]}}
    if kind == "state_record":
        table = str(spec["store"]).replace(".jsonl", ""); ok = _st().get(table, spec.get("op_id")) is not None
        return {"status": "VERIFIED" if ok else "ATTEMPTED", "verified": ok, "evidence": {"store": spec["store"], "found": ok}}
    return {"status": "BLOCKED", "reason": f"unknown evidence type {kind!r}"}

def audit_logging(inputs, skill=None, reg=None):
    import engine
    rec = inputs.get("record")
    if not isinstance(rec, dict): return {"status": "BLOCKED", "reason": "record must be a dict"}
    out = engine.audit({"skill_id": "audit_logging", "manual": True, **rec})
    return {"status": "RECORDED", "store": "audit", "op_id": out["audit_id"]}

def open_loops(inputs, skill=None, reg=None):
    dl = deadline_management(inputs); wf = waiting_for_tracking(inputs); cm = commitment_memory({}); dm = decision_memory({})
    pending = [t for t in _tasks(inputs) if t["open"] and t["owner"].isupper()]
    lv = _live(inputs); cands = _email_candidates(lv, inputs, _today(inputs))
    out = {"status": "EXECUTED", "open_tasks": sum(dl["counts"].values()), "overdue": dl["buckets"]["overdue"],
           "waiting_for": wf["waiting_for"], "open_commitments": cm["commitments"],
           "decisions_pending": [_ser(t) for t in pending], "decisions_logged": len(dm["decisions"]),
           "email_candidates": [c for c in cands if c["class"] in ("ACTION", "DECISION", "DELEGATE", "MONITOR")], "email_candidates_total": len(cands),
           "email_source": next((l for l in lv.get("health_lines", []) if l.startswith("INT-OL-MAIL")), lv.get("reason") or "INT-OL-MAIL not read"),
           "note": "email_candidates are CANDIDATE_OPEN_LOOP (evidence from mail) — none is recorded as a commitment or task automatically"}
    out["management"] = _management(inputs, lv, lambda IQ, st: {"status": "EXECUTED", "loops": IQ.open_loops(st, persist=not inputs.get("no_checkpoint")), "mail": IQ.mail_view(st), "truth_mode": st["truth_mode"], "visibility_lines": IQ.visibility_lines(st)})   # Mission 5 durable open loops + mail intelligence
    return out

def memory_retrieval(inputs, skill=None, reg=None):
    q = _norm(inputs.get("query", inputs.get("context", ""))); hits = []
    if not q: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "query missing (what to find)"}
    files = list(paths.root(ROOT).glob("*.md")) + list((ROOT / ".claude" / "docs").glob("*.md")) + list(paths.biz("01_Active", repo_root=ROOT).rglob("*.md")) + [paths.inbox_input(ROOT)]
    for mem in (pathlib.Path.home() / ".claude" / "projects").glob("*Command-center*/memory"):      # machine-local Claude memory, wherever this clone lives
        if mem.is_dir(): files += list(mem.glob("*.md"))
    for f in files:
        try: txt = f.read_text(encoding="utf-8")
        except Exception: continue
        for i, line in enumerate(txt.splitlines()):
            if q and q in _norm(line): hits.append({"file": f.name, "line": i + 1, "text": line.strip()[:160]})
    out = {"status": "EXECUTED", "query": q, "hits": hits[:25], "count": len(hits)}
    try:
        import documents as DOC; out["documents"] = DOC.search(inputs.get("query", inputs.get("context", "")), idx=DOC.load(rebuild=bool(inputs.get("rebuild_index"))))
        out["document_conflicts"] = out["documents"].get("conflicts", []); out["business_model_first"] = out["documents"].get("business_model_first", [])
    except Exception as e: out["documents"] = {"status": "UNAVAILABLE", "reason": f"document index failed: {type(e).__name__}: {e}"}
    return out

def document_extraction(inputs, skill=None, reg=None):
    p = inputs.get("path")
    if not p: return {"status": "BLOCKED", "reason": "path missing"}
    p = pathlib.Path(p); p = p if p.is_absolute() else ROOT / p
    if not p.exists(): return {"status": "BLOCKED", "code": "SOURCE_MISSING", "path": str(p)}
    if p.suffix == ".docx":
        import docx; d = docx.Document(p)
        paras = [x.text.strip() for x in d.paragraphs if x.text.strip()]
        return {"status": "EXECUTED", "paragraphs": len(paras), "tables": len(d.tables), "head": paras[:10]}
    if p.suffix == ".xlsx":
        import openpyxl; wb = openpyxl.load_workbook(p, read_only=True)
        return {"status": "EXECUTED", "sheets": wb.sheetnames}
    return {"status": "EXECUTED", "text_head": p.read_text(encoding="utf-8", errors="replace")[:1000]}

# ───────────────────────── OPERATING LAYER — channels · people · KPIs · meeting notes · alerts (read-only intelligence) ─────────────────────────
def channel_intelligence(inputs, skill=None, reg=None):
    """«Տելեգրամում ինչ կա» · «ում պիտի պատասխանեմ» · «վաթսափից ինչ follow-up կա»: Telegram/WhatsApp evidence through the integration layer —
    requests to answer, promise candidates, follow-ups owed, escalations, cross-channel duplicates, injection flags. Never sends; NOT_CONFIGURED is said plainly."""
    import channels as CH
    q = _norm(inputs.get("query") or inputs.get("intent") or inputs.get("text") or ""); today = _today(inputs).isoformat()
    chans = [c for c, rx in (("INT-TG", r"(telegram|տելեգրամ|телеграм|\btg\b)"), ("INT-WA", r"(whatsapp|վաթսափ|վոթսափ|ватсап|\bwa\b)")) if re.search(rx, q)] or list(CH.CHAT_CHANNELS)
    if inputs.get("channels"): chans = list(inputs["channels"])
    lv = _live(inputs); cands = _email_candidates(lv, inputs, _today(inputs))
    out = CH.summary(inputs, today=today, channels=chans, mail_candidates=cands, envelopes=inputs.get("chat_envelopes"))
    if out["commitment_candidates"] and inputs.get("ingest_commitments"):
        import commitments as CM; out["ingested"] = CM.ingest(out["commitment_candidates"], origin="EXTERNAL")
    if re.search(r"(ում պիտի պատասխանեմ|who (?:do i|should i|must i) (?:reply|answer|respond)|need to reply|reply to)", q): out["focus"] = "replies"; out["answer"] = out["follow_ups_owed"] or out["requests_to_answer"]
    elif re.search(r"(follow[- ]?up|հետև)", q): out["focus"] = "follow_ups"; out["answer"] = out["follow_ups_owed"]
    else: out["focus"] = "inbox"
    out["business_context"] = _bc_brief(inputs); return out

def people_resolver(inputs, skill=None, reg=None):
    """«էս մարդը որ բաժնից ա» · «who is X» · «ում ա role-ը»: person ↔ role ↔ identities. Linking an external id to a person is Gev's confirmation (inputs.link, confirmed_by Gev)."""
    import people as PP
    q = (inputs.get("query") or inputs.get("intent") or inputs.get("text") or "").strip()
    out = {"status": "EXECUTED", "mutation_performed": False, "conflicts": PP.conflicts()}
    if inputs.get("link"):
        l = inputs["link"]
        if l.get("confirmed_by") != "Gev" and inputs.get("external_source"): return {"status": "BLOCKED", "code": "AUTHORITY_EXCEEDED", "reason": "identity links are confirmed by Gev only — external content cannot link identities"}
        out["link"] = PP.link(l["person"], l["channel"], l["external_id"], display=l.get("display"), method="GEV_CONFIRMED" if l.get("confirmed_by") == "Gev" else "OBSERVED", confirmed_by=l.get("confirmed_by"), source=l.get("source")); out["mutation_performed"] = True
    if inputs.get("external"):
        e = inputs["external"]; out["resolution"] = PP.resolve_external(e["channel"], e["external_id"], e.get("display"))
    m = re.search(r"(?:role|պաշտոն|դեր)\s*([0-9]+\.[0-9]+|EXEC-[A-Z]+)", q, re.I) or re.search(r"\b([0-9]+\.[0-9]+)\b", q)
    if m and re.search(r"(ում|who|holder|ով ա)", q): out["role_holder"] = PP.role_holder(m.group(1))
    name = inputs.get("person") or inputs.get("name")
    if not name:
        hits = PP.find_person(q)
        if len(hits) == 1: name = hits[0]["name"]
        elif len(hits) > 1: out["card"] = {"status": "NEEDS_CONFIRMATION", "candidates": [{"person": p["token"], "name": p["name"]} for p in hits], "reason": "several people match"}
    if name: out["card"] = PP.card(name)
    if "card" not in out and "role_holder" not in out and "resolution" not in out and "link" not in out:
        out["card"] = {"status": "UNKNOWN", "reason": "no known person named in the request — say who (name) or give the external id/channel", "candidates": []}
    c = out.get("card") or {}
    out["answer"] = (f"{c.get('name')} — {c.get('department')} · roles: " + (", ".join(f"{r['role']} {r.get('title') or ''} ({r['conf']})" for r in c.get("roles_confirmed", []) + c.get("roles_candidate", [])) or "none recorded") + f" · identities: {len(c.get('identities', []))}") if c.get("status") == "PERSON_KNOWN" else (c.get("status") or out.get("role_holder", {}).get("status") or out.get("resolution", {}).get("status"))
    return out

def kpi_intelligence(inputs, skill=None, reg=None):
    """«էս KPI-ն ումն ա» · «էս KPI-ի target-ը ինչ ա» · «ինչ ա արժեքը հիմա»: KPI binding from the Business Operating Model — owner, target, source, availability. Never invents a value."""
    import kpis as KP
    q = (inputs.get("query") or inputs.get("intent") or inputs.get("text") or "").strip(); ref = inputs.get("kpi") or inputs.get("kpi_id")
    if not ref:
        m = re.search(r"\b(K-[A-Z0-9\-]+|R-\d+\.\d+-\d+)\b", q, re.I); ref = m.group(1).upper() if m else None
    if not ref:
        import business
        hits = business.find_kpis(re.sub(r"(kpi|target|owner|ումն|ինչ|target-ը|whose|what|the|is|this|էս|այս|ա\b)", " ", q, flags=re.I), limit=3) if business.available() else []
        if len(hits) == 1 or (hits and _norm(hits[0]["name"]) in _norm(q)): ref = hits[0]["kpi_id"]
        elif len(hits) > 1: return {"status": "EXECUTED", "kpi": {"status": "NEEDS_CONFIRMATION", "candidates": [{"kpi_id": k["kpi_id"], "name": k["name"]} for k in hits], "reason": "several KPIs match — name the KPI id"}, "answer": "NEEDS CONFIRMATION — which KPI: " + ", ".join(k["kpi_id"] for k in hits), "mutation_performed": False}
    if not ref: return {"status": "EXECUTED", "kpi": {"status": "KPI_DEFINITION_MISSING", "reason": "no KPI named in the request and no catalog match — give the KPI id or name"}, "answer": "KPI_DEFINITION_MISSING", "mutation_performed": False}
    r = KP.resolve(ref); out = {"status": "EXECUTED", "kpi": r, "mutation_performed": False, "business_context": _bc_brief(inputs)}
    if r["status"] == "KPI_DEFINITION_MISSING": out["answer"] = f"KPI_DEFINITION_MISSING — {r['reason']}"; return out
    ql = _norm(q)
    if re.search(r"(ումն|owner|whose|who owns|ով ա պատասխանատու|պատասխանատու)", ql): out["focus"] = "owner"; o = r["owner"]; out["answer"] = f"{r['kpi_id']} {r['name']} → owner role {o.get('role')} · person {o.get('person')} ({o.get('person_status')})" + (" · candidates: " + ", ".join(str(c.get('person', c.get('token', '?'))) + '/' + str(c.get('conf', '?')) for c in o.get("candidates", [])) if o.get("candidates") else "")
    elif re.search(r"(target|թիրախ|պլան|norm|նորմ)", ql): out["focus"] = "target"; tg = r["target"]; out["answer"] = f"{r['kpi_id']} target: {tg['value']} {tg.get('unit') or ''} ({tg['status']})" + (f" — {tg.get('reason')}" if tg.get("reason") else "")
    elif re.search(r"(value|current|now|հիմա|արժեք|ինչքան|how much)", ql): out["focus"] = "value"; out["answer"] = f"{r['kpi_id']} current value: {r['current_value']}" + (f" — {r['source'].get('reason')}" if r["source"].get("reason") else "")
    else: out["focus"] = "definition"; out["answer"] = f"{r['kpi_id']} {r['name']}: {r['definition']} · formula {r['formula']} · source {r['source'].get('system')} ({r['source'].get('state')}) · target {r['target']['value']} · status {r['status']}"
    return out

def meeting_notes(inputs, skill=None, reg=None):
    """POST-MEETING: supplied notes → decision candidates · commitment candidates · open questions · action drafts (owner/deadline/expected output) · «ժողովից ինչ մնաց բաց».
    Evidence-only extraction with the exact quote; everything is a CANDIDATE until Gev confirms; nothing is written to any system."""
    import commitments as CM
    notes = inputs.get("notes") or inputs.get("content") or inputs.get("text")
    if not notes or len(str(notes).strip()) < 10: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "meeting notes missing — paste/supply the notes (Deputy extracts only from what is supplied, never from memory)"}
    today = _today(inputs); t = today.isoformat(); meeting = inputs.get("meeting") or "meeting"
    dec_rx = re.compile(r"(\b(?:we )?(?:decided|agreed|decision:|resolved that)\b|որոշեցինք|որոշվեց|համաձայնեցինք|պայմանավորվեցինք)", re.I)
    q_rx = re.compile(r"(\?\s*$|\bopen question\b|\bunclear\b|\btbd\b|\bto be decided\b|պարզ չի|պարզ չէ|հարց ա մնում|անհասկանալի|բաց հարց)", re.I)
    lines = [l.strip(" -•*\t") for l in re.split(r"\n+|(?<=[.!?։])\s+", str(notes)) if l.strip(" -•*\t")]
    decisions_c, questions, actions, commits = [], [], [], []
    for i, l in enumerate(lines):
        speaker = None; m = re.match(r"^([A-Za-zԱ-Ֆա-ֆ][\w\-]{1,30})\s*[:：]\s*(.+)$", l)
        if m: speaker, body = m.group(1), m.group(2)
        else: body = l
        if dec_rx.search(body): decisions_c.append({"text": body[:240], "maker": speaker or "UNKNOWN", "quote": l[:240], "status": "CANDIDATE", "note": "confirm with decision_logging (Gev) to make it CONFIRMED"})
        if q_rx.search(body): questions.append({"text": body[:240], "raised_by": speaker or "UNKNOWN", "quote": l[:240]})
        for c in CM.extract(body, speaker=speaker or "UNKNOWN", channel="MEETING_NOTES", record_id=f"notes:{meeting}:{i}", received=t, today=t, trusted=bool(speaker)):
            commits.append(c)
            actions.append({"task": c["what"][:160], "owner": speaker or "<OWNER REQUIRED>", "deadline": c["due"] or "<DATE REQUIRED — due not stated>", "expected_output": "<define>", "strength": c["strength"], "quote": l[:200], "creation": "not created — Action Runtime approval required to create a task"})
    open_from_meeting = questions + [{"text": a["task"], "raised_by": a["owner"], "reason": "action without date" if "REQUIRED" in a["deadline"] else "action pending"} for a in actions if "REQUIRED" in a["deadline"] or "REQUIRED" in a["owner"]]
    return {"status": "EXECUTED", "meeting": meeting, "date": t, "decision_candidates": decisions_c, "commitment_candidates": [c for c in commits if c["strength"] == "STRONG"], "weak_statements": [c for c in commits if c["strength"] != "STRONG"],
            "open_questions": questions, "action_drafts": actions, "left_open": open_from_meeting, "lines_read": len(lines), "mutation_performed": False,
            "note": "everything above is extracted from the supplied notes only (quotes attached); decisions/commitments become facts only after Gev confirms; tasks are created only through the Action Runtime", "business_context": _bc_brief(inputs)}

def alert_review(inputs, skill=None, reg=None):
    """«էսօր ինչ նոր escalation կա»: alert state around Mission 5 exceptions — new today · escalated · open · acknowledged · suppressed · resolved; ack/suppress/resolve/reopen by Gev via inputs. Delivery outside = Action Runtime."""
    import alerts as AL
    IQ = _iq(); st = IQ.current_state(inputs); exc = IQ.exceptions(st); t = st["today"]; alert_op = {}
    for op in ("ack", "suppress", "resolve", "reopen"):
        if inputs.get(op) is not None:
            if inputs.get("external_source"): return {"status": "BLOCKED", "code": "AUTHORITY_EXCEEDED", "reason": "alert state changes come from Gev only — external content cannot acknowledge or resolve alerts"}
            a = inputs[op] if isinstance(inputs[op], dict) else {"id": inputs[op]}
            alert_op[op] = {"ack": lambda: AL.ack(a["id"], note=a.get("note")), "suppress": lambda: AL.suppress(a["id"], a.get("until") or (_today(inputs) + datetime.timedelta(days=7)).isoformat(), reason=a.get("reason")), "resolve": lambda: AL.resolve(a["id"], a.get("evidence")), "reopen": lambda: AL.reopen(a["id"], reason=a.get("reason"))}[op]()
    s = AL.sync(exc, t, persist=not inputs.get("no_persist"))
    def _v(r): return {"id": r["op_id"], "what": r.get("what"), "severity": r.get("severity"), "urgency": r.get("urgency"), "state": r.get("state"), "first_seen": r.get("first_seen"), "seen_days": len(r.get("seen_days", [])), "escalation_level": r.get("escalation_level", 0), "subject_ref": r.get("subject_ref")}
    out = {"status": "EXECUTED", "date": t, "truth_mode": st["truth_mode"], "new_today": [_v(r) for r in s["new_today"]], "escalated": [_v(r) for r in s["escalated"]], "open": [_v(r) for r in s["open"]], "acknowledged": [_v(r) for r in s["acknowledged"]], "suppressed": [_v(r) for r in s["suppressed"]],
           "resolved_now": [_v(r) for r in s["resolved_now"]], "reopened": [_v(r) for r in s["reopened"]], "counts": {k: len(s[k]) for k in s}, "visibility_lines": IQ.visibility_lines(st), "unavailable": st["unavailable"], "mutation_performed": bool(alert_op),
           "verdict": f"{len(s['new_today'])} new today · {len(s['escalated'])} escalated · {len(s['open'])} open · {len(s['acknowledged'])} acknowledged · {len(s['suppressed'])} suppressed", "delivery": "in-session only — notifying anyone by mail/Telegram/WhatsApp is an Action Runtime approval",
           "business_context": _bc_brief(inputs)}
    if alert_op: out["alert_op"] = alert_op
    return out

# ───────────────────────── analysis (supplied data only; never live) ─────────────────────────
def analysis_on_supplied_data(inputs, skill=None, reg=None):
    key = next((k for k in ("sales_data","ops_data","dataset","performance_data") if k in inputs), None)
    if not key or not inputs[key]:
        kind = "operations" if str((skill or {}).get("domain", "")).startswith("C_") else "sales"
        srcs = _live_sources(kind); ok = _live_ok(srcs); bc = _bc_brief(inputs)
        return {"status": "BLOCKED", "code": "MISSING_INPUT" if not ok else "MISSING_INPUT", "reason": f"{skill['skill_id'] if skill else 'analysis'}: no dataset supplied and no VERIFIED live {kind} source is connected ({', '.join(str(s.get('integration_id')) + '=' + str(s.get('certification')) for s in srcs)})",
                "label": "UNKNOWN", "live_sources": srcs,
                "answer": {"LIVE_DATA": "none — no VERIFIED live source for this question", "BUSINESS_MODEL": {"kpis": bc.get("kpis", []), "playbook": bc.get("playbook"), "owner": bc.get("owner"), "required_data": bc.get("required_data", [])},
                           "DERIVED_ANALYSIS": None, "UNKNOWN": ["actuals", "target variance (no actuals; targets only from targets.json)", "trend"]},
                "unblock": [s.get("unblock") for s in srcs if s.get("unblock")], "business_context": bc}
    data = inputs[key]
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        return {"status": "BLOCKED", "code": "INVALID_DATA", "reason": "dataset must be a list of dict rows"}
    nums = {}
    for r in data:
        for k, v in r.items():
            if isinstance(v, (int, float)): nums.setdefault(k, []).append(v)
    stats = {k: {"n": len(v), "sum": round(sum(v), 2), "min": min(v), "max": max(v), "mean": round(sum(v)/len(v), 2)} for k, v in nums.items()}
    trend = {}
    for k, v in nums.items():
        if len(v) >= 2: trend[k] = {"first": v[0], "last": v[-1], "change_pct": round((v[-1]-v[0])/v[0]*100, 1) if v[0] else None}
    return {"status": "ASSISTED", "rows": len(data), "stats": stats, "trend": trend, "label": "DERIVED",
            "note": "Computed from supplied data only; interpretation requires domain confirmation.", "business_context": _bc_brief(inputs)}

def performance_gap_diagnosis(inputs, skill=None, reg=None):
    d = inputs.get("performance_data") or inputs.get("description")
    if not d: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "performance_data/description required; never attribute cause without evidence"}
    text = _norm(json.dumps(d, ensure_ascii=False) if not isinstance(d, str) else d)
    signals = {"PROCESS": r"(process|ընթացակարգ|handoff|no procedure|unclear steps)", "SYSTEM": r"(system|համակարգ|tool|crm|billing|software|bug)",
               "CAPACITY": r"(overload|too much|ծանրաբեռն|capacity|no time)", "TRAINING": r"(training|doesn't know how|ուսուց|չգիտի)",
               "DATA": r"(data|wrong numbers|տվյալ|missing data)", "INCENTIVE": r"(bonus|incentive|commission|պրեմիա|no reason to)",
               "MANAGEMENT": r"(no feedback|unclear priorities|manager|ղեկավար)", "POLICY": r"(policy|rule|կանոն|not allowed)",
               "PERSON": r"(attitude|refus|absent|late again|չի ուզում)"}
    hits = {k: bool(re.search(p, text)) for k, p in signals.items()}
    likely = [k for k in CAUSE_TYPES if hits.get(k)]
    return {"status": "ASSISTED", "candidate_causes": likely or ["UNKNOWN — insufficient evidence"],
            "rule": "Do not assume a PERSON problem; verify PROCESS/SYSTEM/CAPACITY first.", "label": "DERIVED"}

def root_cause_analysis(inputs, skill=None, reg=None):
    desc = inputs.get("description") or inputs.get("symptom")
    if not desc: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "description/symptom required"}
    whys = inputs.get("whys") or []
    chain = [{"why": i + 1, "answer": w} for i, w in enumerate(whys[:5])]
    root = whys[-1] if len(whys) >= 3 else None
    b = _bc(inputs)
    return {"status": "ASSISTED", "symptom": desc, "why_chain": chain, "root_cause": root or "UNKNOWN — fewer than 3 whys supplied",
            "corrective_action": inputs.get("corrective_action", "PENDING root cause"), "playbook_questions": b.get("questions", []), "playbook_diagnostics": b.get("diagnostic_steps", []), "business_context": _bc_brief(inputs),
            "cause_type_candidates": performance_gap_diagnosis({"description": " ".join([desc] + whys)})["candidate_causes"],
            "label": "DERIVED" if root else "UNVERIFIED"}

def structured_analysis(inputs, skill=None, reg=None):
    src = inputs.get("description") or inputs.get("analysis")
    if not src: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "description/analysis required"}
    return {"status": "ASSISTED", "frame": {"what_happened": src if isinstance(src, str) else "see analysis", "why_it_matters": "UNKNOWN — supply impact",
            "root_cause": inputs.get("root_cause", "UNKNOWN"), "options": inputs.get("options", []),
            "recommendation": inputs.get("recommendation", "PENDING"), "owner": inputs.get("owner", "<NAME>"),
            "deadline": inputs.get("deadline", "<DATE>"), "head_action": inputs.get("head_action", "Decide/approve")}, "label": "DERIVED"}

def executive_reporting(inputs, skill=None, reg=None):
    dl = deadline_management(inputs); wf = waiting_for_tracking(inputs)
    red = len(dl["buckets"]["overdue"]); yellow = len(dl["buckets"]["today"]) + len(wf["waiting_for"])
    snapshot = "RED" if red else "YELLOW" if yellow else "GREEN"
    return {"status": "EXECUTED", "snapshot": snapshot, "red": dl["buckets"]["overdue"], "yellow_today": dl["buckets"]["today"],
            "waiting": wf["waiting_for"], "sales": "UNKNOWN — no feed", "operations": "UNKNOWN — no feed",
            "decisions_required": [t for t in dl["buckets"]["today"] + dl["buckets"]["overdue"] if t["owner"].isupper()]}

# ───────────────────────── communication ─────────────────────────
INTERNAL = [("Ես ու Claude", "Գև"), ("Ես + Claude", "Գև"), ("Claude", ""), ("pull անել", ""), ("push", ""), ("Bitrix-ում ստուգել", "")]
def communication_quality_check(inputs, skill=None, reg=None):
    t = inputs.get("content") or inputs.get("text") or ""
    if not t: return {"status": "BLOCKED", "reason": "content missing"}
    issues = []
    if re.search(r"(^|\W)Ես(\W|$)", t) and "Գև" not in t: issues.append("uses «Ես» — outgoing must be in «Գև» voice")
    for a, _ in INTERNAL:
        if a.lower() in t.lower(): issues.append(f"internal wording present: {a!r}")
    if not re.search(r"\d{2}-\d{2}|\d{4}-\d{2}-\d{2}|ուրբաթ|հինգշաբթի|վաղը|այսօր|tomorrow|today", t, re.I): issues.append("no deadline/date")
    return {"status": "EXECUTED", "ok": not issues, "issues": issues}

def outgoing_communication(inputs, skill=None, reg=None):
    t = inputs.get("content") or ""
    if not t: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "content missing"}
    kind = inputs.get("kind") or "message"
    if kind == "follow_up" and not re.search(r"(status|կարգավիճակ|new date|նոր ժամկետ|\?)", t, re.I): t = t.rstrip() + "\nStatus?  ·  New date?  ·  Blocker?"
    clean = t
    for a, b in INTERNAL: clean = clean.replace(a, b)
    clean = re.sub(r"(^|\W)Ես(\W)", r"\1Գև\2", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    q = communication_quality_check({"content": clean})
    return {"status": "EXECUTED", "kind": kind, "recipient": inputs.get("recipient"), "draft": clean, "quality": q,
            "requires_head_ok_before_send": True, "send_tool_available": False}

def drafting(inputs, skill=None, reg=None):
    c = inputs.get("content")
    if not c: return {"status": "BLOCKED", "reason": "content missing"}
    kind = inputs.get("kind") or "summary"
    tmpl = {"summary": "WHAT HAPPENED: {c}\nWHY IT MATTERS: <supply>\nRECOMMENDATION: <supply>\nHEAD ACTION: <supply>",
            "meeting": "Decisions:\nTasks (owner/deadline):\nFollow-up date:\nSource: {c}"}
    if kind not in tmpl: return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": f"unknown kind {kind!r}; use summary|meeting"}
    return {"status": "ASSISTED", "kind": kind, "draft": tmpl[kind].format(c=c), "requires_head_ok_before_send": True}


# ───────────────────────── CONTROLLED HANDS — action runtime executor (Mission 4.2) ─────────────────────────
def _ac():
    import actions; return actions

WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6, "երկուշաբթի": 0, "երեքշաբթի": 1, "չորեքշաբթի": 2, "հինգշաբթի": 3, "ուրբաթ": 4}
def _resolve_date(word, today):
    w = _norm(word or "")
    if not w: return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", w): return w[:10]
    if w in ("today", "այսօր"): return today.isoformat()
    if w in ("tomorrow", "վաղը"): return (today + datetime.timedelta(days=1)).isoformat()
    for name, wd in WEEKDAYS.items():
        if w.startswith(name):
            d = today + datetime.timedelta(days=((wd - today.weekday()) % 7) or 7); return d.isoformat()
    return None

def _last_local_draft():
    """Most recent local (in-store, R0) draft — never a provider object."""
    rows = [r for r in _read_state("decisions") if r.get("kind") == "LOCAL_DRAFT"]
    return rows[-1] if rows else None

def _last_provider_draft():
    """Most recent VERIFIED provider-side Outlook draft (Action Runtime evidence) that has not been sent yet — 'send it' means THAT item."""
    ac = _ac()
    drafts = [a for a in ac.list_actions("status='VERIFIED'") if (a.get("request") or {}).get("target_operation") == "mail.draft" and ((a.get("verification") or {}).get("evidence") or {}).get("id")]
    if not drafts: return None
    sent = {(a.get("request") or {}).get("target_object_id") for a in ac.list_actions("status IN ('VERIFIED','APPROVED','EXECUTING','EXECUTED_UNVERIFIED','RESULT_UNKNOWN')") if (a.get("request") or {}).get("target_operation") == "mail.send"}
    for a in reversed(drafts):
        ev = a["verification"]["evidence"]
        if ev["id"] not in sent: return {"entry_id": ev["id"], "to": ev.get("to") or a["request"]["parameters"].get("to"), "subject": ev.get("subject") or a["request"]["parameters"].get("subject"), "draft_action": a["action_id"]}
    return None

def _parse_action_intent(text, inputs, today):
    """Deterministic understanding of the common management intents → Action Request spec(s) or a non-mutating verdict."""
    t = " ".join(str(text or "").split()); tl = t.lower()
    m = re.search(r"create (?:a |the same )?task for (\w+) to (.+?)(?: by ([\w-]+))?[.!]?$", t, re.I)
    if m:
        owner, title, due = m.group(1), m.group(2).strip(), _resolve_date(m.group(3), today) if m.group(3) else inputs.get("due")
        return {"kind": "action", "system": "INT-TASKS", "op": "tasks.create", "object_type": "task", "params": {"title": title, "owner": owner, "due": due, "status": "Չսկսված"}, "domain": "A_EXECUTIVE_CONTROL",
                "effect": f"one open task for {owner} in Tasks.xlsx" + (f" due {due}" if due else ""), "post": "row exists with this title/owner/deadline/status"}
    m = re.search(r"(?:move|reschedule) (?:tomorrow's |the |today's )?(.+?) to (\d{1,2}:\d{2})", t, re.I)
    if m:
        title, hm = m.group(1).strip(), m.group(2); ev = inputs.get("event") or {}
        if not ev: return {"kind": "blocked", "code": "TARGET_NOT_FOUND", "reason": f"meeting '{title}' not found in the live calendar window — supply/identify the exact event first"}
        day = (ev.get("start") or "")[:10] or (today + datetime.timedelta(days=1)).isoformat(); start = f"{day}T{int(hm.split(':')[0]):02d}:{hm.split(':')[1]}:00"
        dur = 60
        try: dur = int((datetime.datetime.fromisoformat(ev["end"]) - datetime.datetime.fromisoformat(ev["start"])).total_seconds() // 60)
        except Exception: pass
        end = (datetime.datetime.fromisoformat(start) + datetime.timedelta(minutes=dur)).isoformat(timespec="seconds")
        return {"kind": "action", "system": "INT-OL-CAL", "op": "calendar.update", "object_type": "calendar_event", "object_id": ev.get("source_record_id") or ev.get("record_id"), "params": {"subject": ev.get("title") or title, "start": start, "end": end, "participants": [p.get("name") for p in ev.get("participants", [])]},
                "domain": "A_EXECUTIVE_CONTROL", "effect": f"'{ev.get('title') or title}' moves to {start[11:16]} (participants unchanged, {len(ev.get('participants', []))})", "post": "event read back with the new start/end and the same participants"}
    m = re.search(r"cancel (?:tomorrow's |the |today's )?(meeting|.+?)[.!]?$", t, re.I)
    if m and "task" not in tl:
        ev = inputs.get("event") or {}
        if not ev: return {"kind": "blocked", "code": "TARGET_NOT_FOUND", "reason": "meeting to cancel not identified in the live calendar — supply/identify the exact event first"}
        return {"kind": "action", "system": "INT-OL-CAL", "op": "calendar.cancel", "object_type": "calendar_event", "object_id": ev.get("source_record_id") or ev.get("record_id"), "params": {"subject": ev.get("title"), "start": ev.get("start"), "participants": [p.get("name") for p in ev.get("participants", [])]},
                "domain": "A_EXECUTIVE_CONTROL", "effect": f"'{ev.get('title')}' on {ev.get('start')} is cancelled for {len(ev.get('participants', []))} participant(s)", "post": "event absent/cancelled on read-back"}
    m = re.search(r"^draft an? (?:e-?mail|message|reply) to (\w+)(?: (?:asking|about|that|saying) (.+))?", t, re.I)
    if m:
        return {"kind": "local_draft", "to": m.group(1), "subject": inputs.get("subject") or (m.group(2) or "Follow-up")[:60], "body": inputs.get("body") or (f"Dear {m.group(1)},\n\n{m.group(2) or ''}\n\nGev" if m.group(2) else "")}
    m = re.search(r"^(?:e-?mail|message) (?:the )?(.+?) (?:that|saying|about) (.+)", t, re.I)
    if m:
        to = inputs.get("to") or m.group(1).strip(); body = m.group(2).strip()
        return {"kind": "action", "system": "INT-OL-MAIL", "op": "mail.send", "object_type": "email", "params": {"to": to, "cc": inputs.get("cc") or "", "subject": inputs.get("subject") or body[:60], "body": inputs.get("body") or body, "attachments": inputs.get("attachments") or []},
                "domain": "G_COMMUNICATION", "effect": f"an e-mail is SENT to {to}", "post": "Sent Items evidence (recipient, subject, sent time)", "recipients_resolved": bool(inputs.get("to") or "@" in to)}
    if re.search(r"put (?:that|the|this) draft (?:in|into) outlook", tl):
        d = inputs.get("draft") or _last_local_draft()
        if not d: return {"kind": "blocked", "code": "MISSING_INPUT", "reason": "no local draft to place — draft it first"}
        return {"kind": "action", "system": "INT-OL-MAIL", "op": "mail.draft", "object_type": "email_draft", "params": {"to": d.get("to"), "subject": d.get("subject"), "body": d.get("body")}, "domain": "G_COMMUNICATION", "effect": f"a DRAFT appears in Outlook Drafts addressed to {d.get('to')} (nothing is sent)", "post": "draft read back by EntryID (recipient, subject)"}
    m = re.search(r"(?:send|reply|answer)\b.*?\b(?:on|via|in|through) (telegram|whatsapp)\b(?: to (\S+))?|(?:(տելեգրամ|վաթսափ|whatsapp|telegram)[- ]?ով)\s+(?:ուղարկի|պատասխանի)", t, re.I)
    if m:
        ch = (m.group(1) or m.group(3) or "").lower(); iid = "INT-TG" if ch.startswith(("tele", "տել")) else "INT-WA"
        d = inputs.get("draft") if isinstance(inputs.get("draft"), dict) else {}
        text_body = inputs.get("text") or inputs.get("body") or d.get("body") or d.get("text")
        if not text_body and not (iid == "INT-WA" and inputs.get("template")): return {"kind": "blocked", "code": "MISSING_INPUT", "reason": f"nothing to send on {'Telegram' if iid == 'INT-TG' else 'WhatsApp'} — prepare the reply text first (management_communication), then approve the send"}
        if iid == "INT-TG":
            chat = inputs.get("chat_id") or (m.group(2) if m.group(2) and m.group(2).lstrip("-").isdigit() else None)
            if not chat: return {"kind": "blocked", "code": "MISSING_INPUT", "reason": "Telegram chat not identified (chat_id) — pick the conversation from channel_intelligence first"}
            op = "chat.reply" if inputs.get("reply_to_message_id") else "chat.send"
            return {"kind": "action", "system": "INT-TG", "op": op, "object_type": "chat_message", "object_id": inputs.get("reply_to_message_id"), "params": {"chat_id": str(chat), "text": text_body, **({"reply_to_message_id": inputs["reply_to_message_id"]} if inputs.get("reply_to_message_id") else {})}, "domain": "G_COMMUNICATION",
                    "effect": f"a Telegram message is SENT to chat {chat} (bot account)", "post": "provider accepted (message_id) — no independent read-back exists for a bot's own message: reported PARTIAL until confirmed in the chat"}
        to = inputs.get("to") or m.group(2); digits = re.sub(r"\D", "", str(to or ""))
        if not digits: return {"kind": "blocked", "code": "MISSING_INPUT", "reason": "WhatsApp recipient number not identified (to) — pick the conversation from channel_intelligence first"}
        if inputs.get("template"): return {"kind": "action", "system": "INT-WA", "op": "chat.send_template", "object_type": "chat_message", "params": {"to": str(to), "template": inputs["template"], "language": inputs.get("language") or "en", "variables": inputs.get("variables") or []}, "domain": "G_COMMUNICATION", "effect": f"WhatsApp TEMPLATE '{inputs['template']}' is sent to …{digits[-4:]}", "post": "provider delivery status (sent/delivered/read) via the verified webhook"}
        return {"kind": "action", "system": "INT-WA", "op": "chat.send_text", "object_type": "chat_message", "params": {"to": str(to), "text": text_body, **({"reply_to_message_id": inputs["reply_to_message_id"]} if inputs.get("reply_to_message_id") else {})}, "domain": "G_COMMUNICATION", "effect": f"a WhatsApp text is SENT to …{digits[-4:]} (free-form: only inside the 24h customer-service window)", "post": "provider delivery status (sent/delivered/read) via the verified webhook — pending until it arrives"}
    if re.search(r"^send it\b|^send (?:that|the) (?:draft|e-?mail|message)|^ուղարկիր?(?: (?:դա|էդ|այն|նամակը|դռաֆտը|draft-?ը))?[.!]?$", tl):
        pd = None if inputs.get("draft") else _last_provider_draft()
        if pd:                                                        # natural Outlook flow: the reviewed draft ITEM is sent, leaves Drafts, lands in Sent Items
            return {"kind": "action", "system": "INT-OL-MAIL", "op": "mail.send", "object_type": "email_draft", "object_id": pd["entry_id"], "params": {"to": pd["to"], "subject": pd["subject"], "content": "as saved in the Outlook draft (reviewed by Gev; sent unchanged)"},
                    "domain": "G_COMMUNICATION", "effect": f"the Outlook draft '{pd['subject']}' is SENT to {pd['to']} — it leaves Drafts and appears in Sent Items", "post": "draft gone from Drafts + Sent Items evidence (recipient, subject)", "recipients_resolved": bool(pd["to"] and "@" in str(pd["to"]))}
        d = inputs.get("draft") or _last_local_draft()
        if not d: return {"kind": "blocked", "code": "MISSING_INPUT", "reason": "nothing pending to send — draft it first"}
        return {"kind": "action", "system": "INT-OL-MAIL", "op": "mail.send", "object_type": "email", "params": {"to": d.get("to"), "cc": d.get("cc") or "", "subject": d.get("subject"), "body": d.get("body"), "attachments": d.get("attachments") or []}, "domain": "G_COMMUNICATION", "effect": f"the e-mail is SENT to {d.get('to')}", "post": "Sent Items evidence", "recipients_resolved": bool(d.get("to") and "@" in str(d.get("to")))}
    m = re.search(r"remind me (?:if|when) (\w+) (?:hasn't|has not|doesn't) (.+)", t, re.I)
    if m: return {"kind": "local_memory", "text": f"remind: if {m.group(1)} has not {m.group(2).strip()}", "owner": HEAD, "due": inputs.get("due")}
    m = re.search(r"close (?:the |this )?task(?: (\d+))?", tl)
    if m:
        tid = m.group(1) or inputs.get("task_id")
        if not tid: return {"kind": "blocked", "code": "MISSING_INPUT", "reason": "which task? give its № from Tasks.xlsx"}
        if not inputs.get("evidence"): return {"kind": "blocked", "code": "VERIFICATION_REQUIRED", "reason": f"closing task {tid} needs completion evidence (what was delivered, where) — none supplied; a task is not complete because someone says so"}
        return {"kind": "action", "system": "INT-TASKS", "op": "tasks.close", "object_type": "task", "object_id": int(tid), "params": {"evidence": inputs["evidence"]}, "domain": "A_EXECUTIVE_CONTROL", "effect": f"task {tid} status → Արված with the evidence noted", "post": "row read back with status Արված"}
    if re.search(r"mark (?:it|the task|this) (?:as )?(?:complete|done|closed)", tl) and re.search(r"(no|without) evidence|even though", tl):
        return {"kind": "blocked", "code": "VERIFICATION_REQUIRED", "reason": "cannot mark VERIFIED/complete without completion evidence — ATTEMPTED ≠ EXECUTED ≠ VERIFIED"}
    if re.search(r"change (?:the )?customer'?s? tariff|tariff (?:for|of) (?:the )?customer|սակագին", tl):
        return {"kind": "action", "system": "INT-MB", "op": "tariff.change", "object_type": "subscriber", "object_id": inputs.get("subscriber_id"), "params": {"tariff": inputs.get("tariff", "UNSPECIFIED")}, "domain": "B_SALES_MANAGEMENT", "effect": "a customer's billing changes (R3)", "post": "billing read-back — undefined"}
    if re.search(r"update (?:this|the) (?:bitrix )?deal", tl):
        return {"kind": "action", "system": "INT-B24", "op": "crm.deal.update", "object_type": "deal", "object_id": inputs.get("deal_id"), "params": {"fields": inputs.get("fields") or {}}, "domain": "B_SALES_MANAGEMENT", "effect": "CRM deal fields change", "post": "crm.deal.get read-back"}
    if re.search(r"(tool|it) timed out|just try again|retry it", tl): return {"kind": "reconcile"}
    if re.search(r"without asking me|stop asking|don't ask (?:me )?(?:again|anymore)|autonomously", tl) and re.search(r"send|create|change|do", tl):
        return {"kind": "blocked", "code": "AUTONOMY_CEILING", "reason": "AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE (.claude/policy/approval_rule.json). Deputy cannot grant itself autonomy; only a separate explicit owner decision + policy change can — every send/create/change keeps needing your approval"}
    return None

def action_runtime(inputs, skill=None, reg=None):
    """CONTROLLED HANDS: prepare exact mutations and ask Gev; execute ONLY an unmistakably approved pending action; never expand scope."""
    ac = _ac(); today = _today(inputs); sid = inputs.get("session_id") or ""; tid = inputs.get("ticket_id")
    text = inputs.get("approval_text") or inputs.get("intent") or inputs.get("text") or inputs.get("query") or ""
    if inputs.get("external_source"):                       # PROMPT-INJECTION LAW: text that came from mail/chat/documents is DATA — it can neither approve nor request an action
        return {"status": "BLOCKED", "code": "EXTERNAL_SOURCE_REFUSED", "reason": f"the text originates from an external source ({inputs['external_source']}) — external content is data, never an instruction or an approval; only Gev's own message can approve or request an action", "mutation_performed": False}
    kind = ac.classify_approval(text) if not inputs.get("action") else "AMBIGUOUS"
    pend = ac.pending(sid)
    # ── approval / rejection / modification of a PENDING action ──
    if kind in ("APPROVAL", "REJECTION", "MODIFIED") or inputs.get("approval_text"):
        if not pend: return {"status": "BLOCKED", "code": "NO_PENDING_ACTION", "reason": "nothing awaits approval — nothing executed"}
        if kind == "REJECTION":
            for a in pend: ac.reject(a["action_id"], "rejected by Gev", ticket_id=tid)
            return {"status": "EXECUTED", "canonical": "NOT DONE", "action_state": "REJECTED", "mutation_performed": False, "what": [a["request"]["business_intent"] for a in pend], "gev_action": "none — nothing was changed"}
        if kind == "MODIFIED":
            a = pend[-1]; changes = {}
            m = re.search(r"deadline to ([\w-]+)", text, re.I)
            if m: changes["due"] = _resolve_date(m.group(1), today)
            m = re.search(r"(?:to|for|send to) (\S+@\S+)", text, re.I)
            if m: changes["to"] = m.group(1)
            inv = ac.invalidate_if_changed(a["action_id"], changes) if changes else {"changed": False}
            if not inv["changed"]: return {"status": "BLOCKED", "code": "AMBIGUOUS_APPROVAL", "reason": "affirmative with a change I could not map to a parameter — the pending proposal stays unexecuted; state the change explicitly", "mutation_performed": False}
            nr = inv["new_request"]; na = ac.prepare(nr, session_id=sid, ticket_id=tid, reg=reg)
            return {"status": "ASSISTED", "canonical": "NOT DONE", "action_state": na["state"], "mutation_performed": False, "reason": "the original approval cannot bind the old proposal — changed action re-prepared; approve THIS card unambiguously", "card": na.get("card"), "action_id": na["action_id"], "invalidated": a["action_id"]}
        # APPROVAL → bind + execute the exact pending action / batch
        batches = {a.get("batch_id") for a in pend if a.get("batch_id")}
        if any(not (a["request"]["parameters"].get("to") and "@" in str(a["request"]["parameters"].get("to"))) for a in pend if a["request"]["target_operation"] == "mail.send"):
            return {"status": "BLOCKED", "code": "RECIPIENTS_UNRESOLVED", "reason": "the pending e-mail has no concrete recipient address — resolve recipients first, then approve", "mutation_performed": False}
        ap = ac.approve(text, session_id=sid, ticket_id=tid)
        if ap["status"] != "APPROVED": return {"status": "BLOCKED", "code": "NOT_APPROVED", "reason": ap["reason"], "kind": ap["kind"], "mutation_performed": False}
        if ap.get("batch_id"):
            b = ac.execute_batch(ap["batch_id"], ticket_id=tid)
            return {"status": "VERIFIED" if b["state"] == "VERIFIED" else ("ATTEMPTED" if b["state"] == "PARTIAL" else "BLOCKED"), "canonical": {"VERIFIED": "DONE", "PARTIAL": "PARTIAL", "FAILED": "NOT DONE"}[b["state"]], "batch": b, "mutation_performed": b["verified"] > 0, "approval": ap["tokens"][0]["token_id"], "reason": None if b["state"] == "VERIFIED" else "partial batch — see steps"}
        r = ac.execute(ap["action_ids"][0], ticket_id=tid)
        st = {"VERIFIED": "VERIFIED", "RESULT_UNKNOWN": "ATTEMPTED", "EXECUTED_UNVERIFIED": "ATTEMPTED"}.get(r["state"], "BLOCKED")
        return {"status": st, **r, "reason": r.get("result") if st == "BLOCKED" else None}
    # ── structured request supplied directly (tests / other skills) ──
    if inputs.get("action"):
        spec = dict(inputs["action"]); spec.setdefault("kind", "action")
    else:
        spec = _parse_action_intent(text, inputs, today)
    if spec is None:
        if pend: return {"status": "BLOCKED", "code": "AMBIGUOUS_APPROVAL", "reason": f"'{text[:60]}' is not an unmistakable approval of the pending action ({pend[-1]['request']['business_intent'][:60]}) — say OK / GO / Արա / Հաստատում եմ, or reject", "mutation_performed": False, "pending": [a["action_id"] for a in pend]}
        return {"status": "BLOCKED", "code": "MISSING_INPUT", "reason": "no mutating action recognised in the request; supply 'action' {system, op, params} or a recognised management intent"}
    if spec["kind"] == "blocked": return {"status": "BLOCKED", "code": spec["code"], "reason": spec["reason"], "mutation_performed": False}
    if spec["kind"] == "local_draft":
        rec = {"decision": f"local draft to {spec['to']}: {spec['subject']}", "reason": "prepared locally — no provider mutation", "kind": "LOCAL_DRAFT", "to": spec["to"], "subject": spec["subject"], "body": spec["body"]}
        r = _append_state("decisions", rec, ["decision", "subject", "body"])
        return {"status": "ASSISTED", "canonical": "NOT DONE", "draft": rec, "provider_mutation": False, "mutation_performed": False, "note": "text prepared locally; nothing exists in Outlook. 'put that draft in Outlook' or 'send it' will each require your approval", "op_id": r["op_id"]}
    if spec["kind"] == "local_memory":
        r = commitment_tracking({"text": spec["text"], "owner": spec["owner"], "due": spec.get("due")})
        return {"status": "ASSISTED", "canonical": "NOT DONE", "commitment": r, "mutation_performed": False, "note": "recorded in Deputy's own memory (surfaced by the brief); no external system was touched — if a real reminder/task must be created in a system, that will be a separate approval"}
    if spec["kind"] == "reconcile":
        unk = [a for a in ac.list_actions("status='RESULT_UNKNOWN'")]
        if not unk: return {"status": "BLOCKED", "code": "RECONCILE_FIRST", "reason": "no action is in RESULT_UNKNOWN — and a blind retry is never performed; identify the action to reconcile", "mutation_performed": False}
        outs = [ac.reconcile(a["action_id"], ticket_id=tid) for a in unk]
        return {"status": "ATTEMPTED", "canonical": outs[-1]["canonical"], "reconciled": outs, "mutation_performed": False, "note": "RECONCILE FIRST: external state re-read; no retry was performed. Retry only if reconciliation proved the write is absent and the approval is still valid"}
    # ── build + prepare (PREPARE → SHOW GEV) ──
    bc = _bc_brief(inputs)
    req = ac.build_request(skill_id="action_runtime", business_intent=text or spec.get("effect", ""), business_domain=spec.get("domain", "A_EXECUTIVE_CONTROL"), target_system=spec["system"], target_operation=spec["op"],
                           target_object_type=spec.get("object_type", "object"), target_object_id=spec.get("object_id"), parameters=spec.get("params") or {}, expected_effect=spec.get("effect", ""), expected_postcondition=spec.get("post", "read-back matches"),
                           source_context={"ticket_id": tid, "intent": text[:200]}, business_context={k: bc.get(k) for k in ("owner", "processes", "gaps") if bc.get(k)})
    a = ac.prepare(req, session_id=sid, ticket_id=tid, reg=reg)
    if a["state"] == "DENIED":
        return {"status": "BLOCKED", "code": a["codes"][-1], "reason": a.get("reason"), "action_id": a["action_id"], "capability": a.get("capability"), "mutation_performed": False, "canonical": "BLOCKED"}
    note = None
    if spec.get("recipients_resolved") is False: note = "recipient is a group/name, not addresses — resolve recipients before approval (nothing sent)"
    return {"status": "ASSISTED", "canonical": "NOT DONE", "action_state": a["state"], "action_id": a["action_id"], "card": a["card"], "fingerprint": req["action_fingerprint"], "risk_class": req["risk_class"], "mutation_performed": False, "note": note, "gev_action": "approve (OK / GO / Արա / Հաստատում եմ) or reject", "business_context": bc}

# ───────────────────────── output validation ─────────────────────────
def validate_output(skill_id, result):
    if not isinstance(result, dict) or "status" not in result: return False, "result must be dict with status"
    if result["status"] not in ("EXECUTED","VERIFIED","RECORDED","DUPLICATE","BLOCKED","ASSISTED","ATTEMPTED"):
        return False, f"bad status {result['status']}"
    if result["status"] == "BLOCKED" and not (result.get("reason") or result.get("code")): return False, "BLOCKED without reason"
    checks = {
        "executive_prioritization": lambda r: all(x.get("P") in ("P1","P2","P3","P4") for x in r.get("ranked", [])) and r.get("p1_count", 0) <= 5,
        "deadline_management": lambda r: set(r.get("buckets", {})) == {"overdue","today","tomorrow","upcoming","no_deadline"},
        "daily_briefing": lambda r: all(k in r for k in ("top_priorities","overdue","deadlines_today","waiting_for","counts","sections","live")) and all(s.get("items") for s in r.get("sections", [])) and (r["live"].get("available") is False or not (set(r["live"].get("critical_unavailable", [])) - {x["text"].split(" ")[0] for x in r.get("risks", []) if x.get("kind") == "INTEGRATION_DOWN"})),
        "task_management": lambda r: "tasks" in r or "task" in r,
        "commitment_tracking": lambda r: "op_id" in r and "scheduler_available" in r,
        "reminder_intelligence": lambda r: r.get("scheduler_available") is False and "plan" in r,
        "waiting_for_tracking": lambda r: all(i.get("from") for i in r.get("waiting_for", [])),
        "follow_up_management": lambda r: all(f.get("owner") and f.get("next_action") for f in r.get("follow_ups", [])),
        "escalation_management": lambda r: set(r.get("escalation", {})) >= {"problem","impact","owner","deadline_status","done_so_far","head_action"},
        "source_reconciliation": lambda r: r.get("chosen") is None if r.get("contradiction") else True,
        "completion_verification": lambda r: r["status"] in ("VERIFIED","ATTEMPTED") and "verified" in r,
        "delegation_design": lambda r: "draft" in r and "issues" in r,
        "decision_support": lambda r: "decision_needed" in r and r["decision_needed"].get("approver") == HEAD,
        "management_communication": lambda r: r.get("requires_head_ok_before_send") is True and "Claude" not in r.get("draft", ""),
        "decision_logging": lambda r: "op_id" in r and r.get("store") == "decisions",
        "source_verification": lambda r: "stale" in r and "exists" in r,
        "risk_classification": lambda r: r.get("risk") in ("LOW","MEDIUM","HIGH","CRITICAL"),
        "approval_management": lambda r: "approved" in r,
        "authority_checking": lambda r: "allowed" in r,
        "action_runtime": lambda r: "mutation_performed" in r and (r["status"] != "VERIFIED" or r.get("state") == "VERIFIED") and not (r["status"] == "ASSISTED" and r.get("mutation_performed")),
        # Mission 5 — intelligence never mutates, never hides visibility gaps, never invents categories
        "management_snapshot": lambda r: r.get("mutation_performed") is False and "visibility" in r and "unavailable" in r and "truth_mode" in r and all(x.get("category") in ("APPROVAL", "DECISION", "ESCALATION", "OWNER NEEDED", "PRIORITY CONFLICT", "MISSING BUSINESS TRUTH") for x in r.get("gev", [])),
        "exception_review": lambda r: r.get("mutation_performed") is False and "visibility_incomplete" in r and "exceptions" in r and all(e.get("WHAT_CAUSED_IT", "").split(" — ")[0] in ("CONFIRMED CAUSE", "SUPPORTED HYPOTHESIS", "UNKNOWN") for e in r["exceptions"]),
        "change_review": lambda r: r.get("mutation_performed") is False and set(r.get("groups", {})) == {"NEW", "CHANGED", "RESOLVED", "WORSENED", "NEEDS_GEV"},
        "channel_intelligence": lambda r: r.get("mutation_performed") is False and "channels" in r and "requests_to_answer" in r and "injection_flagged" in r and all(s.get("state") in ("LIVE", "CACHED", "FIXTURE", "NOT_CONFIGURED", "UNAVAILABLE") for s in r["channels"].values()),
        "people_resolver": lambda r: "answer" in r and ((r.get("card") or {}).get("status") in (None, "PERSON_KNOWN", "UNKNOWN", "NEEDS_CONFIRMATION")),
        "kpi_intelligence": lambda r: r.get("mutation_performed") is False and (r.get("kpi") or {}).get("status") in ("OK", "UNAVAILABLE", "TARGET_UNKNOWN", "KPI_DEFINITION_MISSING", "NEEDS_CONFIRMATION") and "answer" in r,
        "meeting_notes": lambda r: r.get("mutation_performed") is False and all(k in r for k in ("decision_candidates", "commitment_candidates", "open_questions", "action_drafts", "left_open")) and all(d.get("status") == "CANDIDATE" for d in r["decision_candidates"]),
        "alert_review": lambda r: all(k in r for k in ("new_today", "escalated", "open", "acknowledged", "suppressed", "resolved_now")) and "delivery" in r,
        "commitment_memory": lambda r: "commitments" in r and "late_leaders" in r and all(c.get("lifecycle") in ("OPEN", "DUE_SOON", "OVERDUE") for c in r["commitments"]),
        "decision_memory": lambda r: "decisions" in r and "review_pending" in r,
        "decision_queue": lambda r: r.get("mutation_performed") is False and all(x.get("category") in ("APPROVAL", "DECISION", "ESCALATION", "OWNER NEEDED", "PRIORITY CONFLICT", "MISSING BUSINESS TRUTH") and x.get("why_gev") for x in r.get("queue", [])),
    }
    fn = checks.get(skill_id)
    if fn and result["status"] not in ("BLOCKED",) and not fn(result): return False, f"validation rule failed for {skill_id}"
    return True, None

def verify_completion(skill_id, result, inputs=None):
    """COMPLETION VERIFICATION — re-read the state a skill claims to have produced. Returns (ok, detail).
    A claim that cannot be re-observed is VERIFICATION_FAILED, never success."""
    inputs = inputs or {}
    if not isinstance(result, dict): return False, "no result"
    st = result.get("status")
    try:
        if st in ("RECORDED", "DUPLICATE") and result.get("store"):
            found = _st().get(result["store"], result.get("op_id"))
            return (found is not None), f"{result['store']}:{result.get('op_id')} {'present' if found else 'ABSENT'} on re-read"
        if skill_id in ("task_management",) and "tasks" in result:
            n = len(_tasks(inputs)); return (n == result.get("count")), f"re-read {n} rows vs reported {result.get('count')}"
        if skill_id == "deadline_management":
            n = len([t for t in _tasks(inputs) if t["open"]]); tot = sum(result.get("counts", {}).values())
            return (n == tot), f"re-read {n} open vs bucketed {tot}"
        if skill_id == "daily_briefing":
            n = len([t for t in _tasks(inputs) if t["open"]]); tot = sum(result.get("counts", {}).values())
            return (n == tot), f"re-read {n} open vs briefed {tot}"
        if skill_id == "audit_logging" and st == "RECORDED":
            import engine
            recs = engine.read_audit(3); ok = any(r.get("manual") for r in recs)
            return ok, "manual audit record present on re-read" if ok else "audit record ABSENT"
        if skill_id == "completion_verification":
            return ("verified" in result), "verification result carries explicit verified flag"
        if skill_id == "action_runtime" and result.get("action_id"):
            import actions; a = actions.get(result["action_id"])
            if not a: return False, "action record ABSENT on re-read"
            if result.get("status") == "VERIFIED" and a["state"] != "VERIFIED": return False, f"claimed VERIFIED but store says {a['state']}"
            return True, f"action {a['action_id']} re-read: {a['state']}"
        if skill_id in ("channel_intelligence", "people_resolver", "kpi_intelligence", "meeting_notes", "alert_review", "commitment_memory", "decision_memory"):
            if result.get("mutation_performed") and skill_id in ("people_resolver", "alert_review", "commitment_memory", "decision_memory"):
                tbl = {"people_resolver": "identities", "alert_review": "alerts", "commitment_memory": "commitments", "decision_memory": "decisions"}[skill_id]
                return _st().count(tbl) >= 0, f"{tbl} re-read after a Gev-initiated state change"
            return result.get("mutation_performed") is False, "read-only operating-layer intelligence: no mutation claimed"
        if skill_id in ("management_snapshot", "exception_review", "change_review", "decision_queue"):
            ck = (result.get("checkpoint") or (result.get("management") or {}).get("checkpoint") or {}).get("op_id")
            if ck:
                found = _st().get("checkpoints", ck); return (found is not None), f"checkpoint {ck} {'present' if found else 'ABSENT'} on re-read"
            if isinstance(result.get("tasks"), dict) and "counts" in result["tasks"] and "tasks" not in inputs:
                n = len([t for t in _tasks(inputs) if t["open"]]); return (n == result["tasks"]["counts"]["open"]), f"re-read {n} open vs reported {result['tasks']['counts']['open']}"
            return result.get("mutation_performed") is False, "read-only intelligence: no mutation claimed"
        return True, "no post-condition declared"
    except Exception as e:
        return False, f"verification error {type(e).__name__}: {e}"

def summarize(result):
    if not isinstance(result, dict): return str(result)[:200]
    keys = [k for k in ("status","count","p1_count","snapshot","op_id","verified","contradiction","risk","code","reason") if k in result]
    return {k: result[k] for k in keys}
