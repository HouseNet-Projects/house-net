# -*- coding: utf-8 -*-
"""MISSION 5 — LIVE SALES & OPERATIONS INTELLIGENCE: the ONE canonical current-state intelligence pipeline.

    LIVE READS → NORMALIZE → PROVENANCE/FRESHNESS → CURRENT STATE → CHANGE DETECTION → EXCEPTIONS → CORRELATION → CAUSE DISCIPLINE
    → IMPACT → PRIORITY → RECOMMENDATION → OWNER → DEADLINE → GEV ACTION → MANAGEMENT OUTPUT

Rules this module enforces mechanically (tests assert them):
  · every live observation keeps source system · record id · retrieved_at · freshness · authority · state (LIVE / CACHED / STALE / UNAVAILABLE /
    NOT_CONFIGURED / FIXTURE / SUPPLIED); NO ISSUE and NO DATA never collapse (visibility is reported separately from exceptions)
  · a fixture / supplied dataset is never production truth (truth_mode = NON_PRODUCTION) · stale is never presented as live
  · causes are CONFIRMED CAUSE / SUPPORTED HYPOTHESIS (with the evidence signal) / UNKNOWN — correlation is never a cause
  · owner / deadline / cause / numbers are never invented: UNKNOWN stays UNKNOWN, missing sources are named with the capability that is missing
  · recommendations are ACTION → OWNER → DEADLINE → VERIFY and never mutate anything; execution goes through the Mission 4.2 Action Runtime only
  · Gev's queue carries only what genuinely needs Gev (APPROVAL · DECISION · ESCALATION · OWNER NEEDED · PRIORITY CONFLICT · MISSING BUSINESS TRUTH)
  · durable continuity = minimal checkpoints (signatures, no payloads) + open loops (refs, no shadow copies); live systems stay authoritative
The Business Operating Model says what things MEAN (owners, KPIs, processes, playbooks); live integrations say what is HAPPENING now."""
import json, re, datetime, hashlib, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(HERE.parent / "integrations") not in sys.path: sys.path.insert(0, str(HERE.parent / "integrations"))

SEVERITY = ("HIGH", "MEDIUM", "LOW"); URGENCY = ("NOW", "TODAY", "THIS_WEEK", "LATER")
CAUSE_KINDS = ("CONFIRMED CAUSE", "SUPPORTED HYPOTHESIS", "UNKNOWN")
GEV_CATEGORIES = ("APPROVAL", "DECISION", "ESCALATION", "OWNER NEEDED", "PRIORITY CONFLICT", "MISSING BUSINESS TRUTH")
IMPACT_CATEGORIES = ("revenue", "customer", "deadline", "workload/capacity", "operational continuity", "dependency/blocker", "management attention", "compliance/governance")
BLOCKED_STATUSES = {"Սպասում"}; UNCLEAR_STATUSES = {"Պարզ չէ"}; NOT_STARTED = {"Չսկսված"}
CRITICAL_RX = re.compile(r"(ԿՐԻՏԻԿ|CRITICAL|URGENT|ՇՏԱՊ)", re.I)
DECISION_MEETING_RX = re.compile(r"(decision|approve|approval|sign-?off|որոշ|հաստատ|review|budget|strategy|ռազմավար|ժողով)", re.I)
FOLLOWUP_MEETING_RX = re.compile(r"(follow[- ]?up|status|sync|check-?in|հետև|կարգավիճակ)", re.I)
DEADLINE_MEETING_RX = re.compile(r"(deadline|due|submit|ժամկետ|վերջնաժամկետ|delivery|հանձն)", re.I)
UNKNOWN = "UNKNOWN"

def _x():
    import executors; return executors
def _st():
    import engine; return engine._store()
def _now(): return datetime.datetime.now().isoformat(timespec="seconds")
def _hid(*p): return hashlib.sha256("|".join(str(x) for x in p).encode("utf-8")).hexdigest()[:12]
def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())

# ═══════════════════════════════ 1. LIVE READS + PROVENANCE ═══════════════════════════════
def _vis_of(iid, env, spec=None, cap=None):
    """One honest visibility row per integration: what state its data is in RIGHT NOW (never 'no issue' when there is no data)."""
    spec = spec or {}; env = env or {}
    row = {"integration_id": iid, "system": spec.get("system") or env.get("source_system"), "critical": bool(spec.get("critical")), "mode": env.get("mode", "REAL"),
           "retrieved_at": env.get("retrieved_at"), "count": env.get("count", 0), "authority": (spec.get("authority") or {}).get("name") or (env.get("authority") or {}).get("name"),
           "certification": (cap or {}).get("certification"), "health": env.get("health") or (cap or {}).get("health"), "last_success": env.get("last_success") or (cap or {}).get("last_success"),
           "code": env.get("code"), "reason": env.get("reason"), "unblock": (cap or {}).get("unblock"), "production_truth": env.get("mode", "REAL") == "REAL" and env.get("status") == "OK"}
    if env.get("status") == "OK":
        row["state"] = "FIXTURE" if env.get("mode") == "FIXTURE" else ("SUPPLIED" if env.get("mode") == "SUPPLIED" else env.get("freshness", "LIVE"))
        row["cache_age_seconds"] = env.get("cache_age_seconds")
    else:
        row["state"] = "DEFERRED" if env.get("code") == "DEFERRED" or (spec or {}).get("deferred") else ("NOT_CONFIGURED" if env.get("code") == "NOT_CONFIGURED" or (cap or {}).get("health") == "NOT_CONFIGURED" else "UNAVAILABLE")
        if row["state"] == "DEFERRED": row["unblock"] = None; row["deferred"] = (spec or {}).get("deferred")          # deferred by Gev: shown once, never nagged with unblock instructions
    row["usable"] = row["state"] in ("LIVE", "CACHED", "FIXTURE", "SUPPLIED")             # STALE data is visible but never used as current truth
    return row

def _supplied_tasks_env(inputs, today):
    import normalize
    x = _x(); rows = x._tasks(inputs); upd = _now()
    recs = [normalize.task("INT-TASKS", t, upd) for t in rows]
    return {"status": "OK", "integration_id": "INT-TASKS", "source_system": "Tasks.xlsx (supplied rows)", "op": "tasks.list", "kind": "task", "count": len(recs), "records": recs, "retrieved_at": upd,
            "freshness": "LIVE", "mode": "SUPPLIED", "authority": {"name": "ACTIVE_REGISTER", "business_source": "S09"}, "notes": ["rows supplied by the caller — not a production read"]}

def read_sources(inputs, today, *, horizon_days=3, mail_days=3):
    """Every integration genuinely available at runtime is read through the integration layer (read-only, audited). Returns (envelopes, visibility)."""
    import layer, registry, health
    inputs = inputs or {}; env = {}; use_cache = not inputs.get("no_cache")
    # task register (canonical live register S09 / INT-TASKS)
    if isinstance(inputs.get("tasks"), list): env["INT-TASKS"] = _supplied_tasks_env(inputs, today)
    else: env["INT-TASKS"] = layer.query("INT-TASKS", "tasks.list", {"path": inputs["path"]} if inputs.get("path") else {}, use_cache=use_cache)
    # Outlook calendar + mail (memory-only cache with visible freshness)
    lv = inputs.get("live_context") if isinstance(inputs.get("live_context"), dict) else None
    if lv is None and not inputs.get("no_live"):
        try: lv = layer.brief_context(today, horizon_days=horizon_days, mail_days=mail_days, use_cache=use_cache)
        except Exception as e: lv = {"error": f"{type(e).__name__}: {e}"}
    for iid, key in (("INT-OL-CAL", "calendar"), ("INT-OL-MAIL", "mail")):
        e = (lv or {}).get(key)
        if isinstance(e, dict) and e.get("status"): env[iid] = e
        else:
            import contracts as C
            env[iid] = C.failure(iid, (registry.get(iid) or {}).get("system", iid), key, "UNAVAILABLE", (lv or {}).get("error") or (lv or {}).get("reason") or "live layer disabled/unavailable for this run", last_success=(health.get(iid) or {}).get("last_success"))
    # Bitrix24 / MikroBILL: read only when the capability truth says a read can succeed; otherwise an honest failure envelope with the missing capability
    st = {s["integration_id"]: s for s in layer.status()}
    for iid, op in (("INT-B24", "crm.deals"), ("INT-MB", None)):
        s = st.get(iid) or {}; spec = registry.get(iid) or {}
        import contracts as C
        if spec.get("deferred"): env[iid] = C.failure(iid, spec.get("system", iid), op or "read", "DEFERRED", f"{iid} deferred by {spec['deferred'].get('by')} since {spec['deferred'].get('since')} — no read attempted, no activation requested", last_success=s.get("last_success")); continue
        if op and s.get("configured") and s.get("certification") in ("VERIFIED_READ", "RELIABLE_READ", "CONNECTED"):
            env[iid] = layer.query(iid, op, {"limit": 200}, use_cache=use_cache)
        elif not spec.get("read_ops"): env[iid] = C.failure(iid, spec.get("system", iid), op or "read", "NOT_CONFIGURED", f"{iid}: no read interface inventoried — {spec.get('unblock') or 'interface unknown'}", last_success=s.get("last_success"))
        else: env[iid] = C.failure(iid, spec.get("system", iid), op or "read", "NOT_CONFIGURED", f"{iid} is {s.get('certification', 'DECLARED')} / {s.get('health')} — {spec.get('unblock') or 'not configured'}", last_success=s.get("last_success"))
    # chat channels (Telegram / WhatsApp): read through the same layer; NOT_CONFIGURED is an honest visibility row, never 'no messages'
    for iid in ("INT-TG", "INT-WA"):
        if isinstance((inputs.get("chat_envelopes") or {}).get(iid), dict): env[iid] = inputs["chat_envelopes"][iid]; continue
        s = st.get(iid) or {}
        if s.get("configured") or inputs.get("read_chat"): env[iid] = layer.query(iid, "chat.messages", {"limit": 100}, use_cache=use_cache)
        else:
            import contracts as C; spec = registry.get(iid) or {}
            env[iid] = C.failure(iid, spec.get("system", iid), "chat.messages", "NOT_CONFIGURED", f"{iid} not configured — {spec.get('unblock', '')[:100]}", last_success=s.get("last_success"))
    vis = {iid: _vis_of(iid, env.get(iid), registry.get(iid), st.get(iid)) for iid in env}
    return env, vis

# ═══════════════════════════════ 2. CURRENT STATE ═══════════════════════════════
def _task_facts(rec, today):
    x = _x(); due = x._date(rec.get("due")); owner = str(rec.get("owner") or "").strip(); status = str(rec.get("status") or "").strip()
    holder, other = x._counterpart(owner)
    days = (due - today).days if due else None
    return {"id": int(rec["source_record_id"]) if str(rec.get("source_record_id", "")).isdigit() else rec.get("source_record_id"), "record_id": rec.get("record_id"), "title": rec.get("title") or rec.get("task") or "",
            "status": status, "open": bool(rec.get("open")), "owner": owner, "holder": holder or None, "due": due.isoformat() if due else None, "days": days, "comment": rec.get("comment") or "", "row": rec.get("row"),
            "overdue": bool(rec.get("open")) and days is not None and days < 0, "due_today": bool(rec.get("open")) and days == 0, "due_soon": bool(rec.get("open")) and days is not None and 0 < days <= 3,
            "no_deadline": bool(rec.get("open")) and due is None, "ownerless": bool(rec.get("open")) and (not owner or owner in ("—", "-", "?", UNKNOWN)),
            "gev_owned": bool(rec.get("open")) and not other and bool(owner), "waiting_for": bool(rec.get("open")) and other, "decision_needed": bool(rec.get("open")) and bool(owner) and owner.isupper(),
            "blocked": bool(rec.get("open")) and status in BLOCKED_STATUSES, "unclear": bool(rec.get("open")) and status in UNCLEAR_STATUSES, "not_started": status in NOT_STARTED,
            "critical": bool(CRITICAL_RX.search(rec.get("title") or "")), "source_updated_at": rec.get("source_updated_at")}

def _meeting_kind(m, related):
    text = (m.get("title") or "") + " " + (m.get("description_preview") or "")
    if m.get("all_day") and DEADLINE_MEETING_RX.search(text): return "DEADLINE"
    if DECISION_MEETING_RX.search(text): return "DECISION"
    if FOLLOWUP_MEETING_RX.search(text) or related: return "FOLLOW_UP"
    return "INFO"

def current_state(inputs=None, *, horizon_days=3, mail_days=3):
    """The canonical live management state: tasks, calendar, mail, commitments, decisions, actions, business context, visibility — with provenance on every item."""
    x = _x(); inputs = inputs or {}; today = x._today(inputs)
    env, vis = read_sources(inputs, today, horizon_days=horizon_days, mail_days=mail_days)
    te = env["INT-TASKS"]; tasks = [_task_facts(r, today) for r in te.get("records", [])] if te.get("status") == "OK" else []
    tprov = {"integration_id": "INT-TASKS", "retrieved_at": te.get("retrieved_at"), "freshness": te.get("freshness"), "mode": te.get("mode"), "business_source": "S09", "state": vis["INT-TASKS"]["state"]}
    open_tasks = [t for t in tasks if t["open"]]
    task_rows = [{"id": t["id"], "title": t["title"], "owner": t["owner"], "due": t["due"], "status": t["status"]} for t in open_tasks]
    # calendar — only a usable envelope (LIVE/CACHED/FIXTURE) feeds current state; STALE/UNAVAILABLE data is visible in `visibility`, never used as now
    ce = env["INT-OL-CAL"] if vis["INT-OL-CAL"]["usable"] else {"status": "STALE_OR_UNAVAILABLE", **{k: env["INT-OL-CAL"].get(k) for k in ("retrieved_at", "freshness", "mode", "code")}}
    lv_like = {"calendar": ce, "mail": env["INT-OL-MAIL"]}
    m_today, m_up, conflicts = x._meetings(lv_like, today)
    import reconcile as rc
    meetings = []
    for m in m_today + m_up:
        rel = [t for t in task_rows if len(rc.overlap((m.get("title") or "") + " " + (m.get("description_preview") or ""), t["title"])) >= 2]
        meetings.append({**{k: m.get(k) for k in ("record_id", "title", "start", "end", "all_day", "participant_count", "location", "organizer")}, "today": (m.get("start") or "")[:10] == today.isoformat(),
                         "kind": _meeting_kind(m, rel), "related_tasks": [t["id"] for t in rel], "missing_prep": [] if (m.get("description_preview") or "").strip() else ["purpose/agenda not in the invitation"],
                         "provenance": {"integration_id": "INT-OL-CAL", "record_id": m.get("record_id"), "retrieved_at": ce.get("retrieved_at"), "freshness": ce.get("freshness"), "mode": ce.get("mode")}})
    # mail → candidate loops (never permanent facts)
    me = env["INT-OL-MAIL"]; cands = []
    if me.get("status") == "OK" and vis["INT-OL-MAIL"]["usable"]:                          # stale mail never becomes a current candidate loop
        heads = (me.get("identity") or {}).get("addresses") or []
        cm = x.commitment_memory({})["commitments"]; dm = x.decision_memory({})["decisions"]
        cands = rc.open_loop_candidates(me.get("records", []), tasks=task_rows, commitments=cm, decisions=dm, today=today, head_addresses=heads)
        for c in cands: c["provenance"] = {"integration_id": "INT-OL-MAIL", "record_id": c["evidence"].get("record_id"), "retrieved_at": me.get("retrieved_at"), "freshness": me.get("freshness"), "mode": me.get("mode")}
    else: cm = x.commitment_memory({})["commitments"]; dm = x.decision_memory({})["decisions"]
    # Deputy's own durable memory (commitments / decisions / governed actions)
    commitments = [{**c, "overdue": bool(c.get("due")) and c["due"] < today.isoformat(), "due_soon": bool(c.get("due")) and today.isoformat() <= c["due"] <= (today + datetime.timedelta(days=3)).isoformat()} for c in cm]
    try:
        import actions as A
        acts = A.list_actions("status IN ('APPROVAL_REQUIRED','APPROVED','EXECUTING','EXECUTED_UNVERIFIED','RESULT_UNKNOWN')")
    except Exception: acts = []
    actions = [{"action_id": a["action_id"], "state": a["state"], "intent": (a.get("request") or {}).get("business_intent"), "system": (a.get("request") or {}).get("target_system"), "op": (a.get("request") or {}).get("target_operation")} for a in acts]
    bc = x._bc(inputs)
    try:
        import channels as CH
        chat = CH.summary(inputs, today=today.isoformat(), channels=("INT-TG", "INT-WA"), mail_candidates=cands, envelopes={k: env[k] for k in ("INT-TG", "INT-WA") if k in env})
    except Exception as e: chat = {"status": "UNAVAILABLE", "reason": f"{type(e).__name__}: {e}", "channels": {}, "items": [], "requests_to_answer": [], "commitment_candidates": [], "follow_ups_owed": [], "escalations": [], "duplicates": [], "injection_flagged": []}
    return {"today": today.isoformat(), "at": _now(), "tasks": tasks, "chat": chat, "open_tasks": open_tasks, "task_provenance": tprov, "meetings": meetings, "schedule_conflicts": conflicts,
            "mail_candidates": cands, "commitments": commitments, "decisions": dm, "actions": actions, "business": {"available": bool(bc.get("available")), "conflicts": bc.get("conflicts", []), "gaps": bc.get("gaps", []), "owner": bc.get("owner")},
            "envelopes": {k: {kk: v.get(kk) for kk in ("status", "code", "reason", "retrieved_at", "freshness", "mode", "count", "health", "last_success")} for k, v in env.items()}, "visibility": vis,
            "truth_mode": "PRODUCTION" if all(v["production_truth"] or v["state"] in ("UNAVAILABLE", "NOT_CONFIGURED", "DEFERRED") for v in vis.values()) else "NON_PRODUCTION (fixture/supplied data present)",
            "unavailable": [iid for iid, v in vis.items() if not v["usable"]], "critical_unavailable": [iid for iid, v in vis.items() if not v["usable"] and v["critical"]]}

# ═══════════════════════════════ 3. EXCEPTIONS · CAUSE · IMPACT · RECOMMENDATION ═══════════════════════════════
def _cause(t):
    """Cause discipline for a task exception: CONFIRMED only for a structural fact, HYPOTHESIS with its evidence signal, else UNKNOWN."""
    if t.get("ownerless"): return {"kind": "CONFIRMED CAUSE", "text": "no owner assigned — nobody is accountable for this item", "evidence": ["owner field empty in the register"]}
    if t.get("blocked"):
        who = t.get("holder") or UNKNOWN
        return {"kind": "SUPPORTED HYPOTHESIS", "text": f"progress may depend on {who} — the register marks the item as waiting", "evidence": [f"status {t['status']}", f"owner field '{t['owner']}'"]}
    if t.get("unclear"): return {"kind": "SUPPORTED HYPOTHESIS", "text": "the scope/next step is unclear to the owner — the register marks it 'Պարզ չէ'", "evidence": [f"status {t['status']}"]}
    return {"kind": "UNKNOWN", "text": "no evidence in the register or mail explains the delay — ask the owner, do not assume", "evidence": []}

def _impact(t, kind):
    if t.get("critical"): return {"category": "management attention", "level": "HIGH", "rationale": "the item is marked critical by the principal"}
    if kind == "OVERDUE_TASK" and t.get("days") is not None and t["days"] <= -7: return {"category": "deadline", "level": "HIGH", "rationale": f"{-t['days']} days overdue — the commitment is effectively broken"}
    if kind == "OVERDUE_TASK": return {"category": "deadline", "level": "MEDIUM", "rationale": f"{-t['days']} day(s) past the deadline"}
    if kind in ("BLOCKED_TASK", "OWNERLESS_TASK"): return {"category": "dependency/blocker", "level": "MEDIUM", "rationale": "the item cannot move without an owner/handoff"}
    if kind == "DUE_TODAY": return {"category": "deadline", "level": "MEDIUM", "rationale": "due today — still open"}
    if kind == "DECISION_PENDING": return {"category": "management attention", "level": "MEDIUM", "rationale": "an open decision holds dependent work"}
    return {"category": "management attention", "level": "LOW", "rationale": "no evidence of wider impact"}

def _urgency(t, kind):
    if kind in ("OVERDUE_TASK",) or t.get("critical"): return "NOW"
    if kind in ("DUE_TODAY", "DECISION_PENDING", "MAIL_DECISION"): return "TODAY"
    if t.get("due_soon"): return "THIS_WEEK"
    return "LATER"

def _severity(t, kind):
    if kind == "OVERDUE_TASK" and (t.get("critical") or (t.get("days") is not None and t["days"] <= -7) or t.get("decision_needed")): return "HIGH"
    if kind in ("OVERDUE_TASK", "ACTION_UNVERIFIED", "COMMITMENT_OVERDUE"): return "HIGH" if kind == "ACTION_UNVERIFIED" else "MEDIUM"
    if kind in ("DUE_TODAY", "BLOCKED_TASK", "OWNERLESS_TASK", "DECISION_PENDING", "SCHEDULE_CONFLICT", "MAIL_DECISION"): return "MEDIUM"
    return "LOW"

def _recommend(t, kind, today):
    owner = t.get("holder") or (t.get("owner") if t.get("owner") and not t.get("ownerless") else None)
    if kind == "OWNERLESS_TASK": return {"action": f"Assign ONE named owner to task {t['id']} '{t['title'][:50]}'", "owner": "OWNER NEEDED — Gev decides", "deadline": today, "verify": "register row shows a named owner on read-back"}
    if kind == "OVERDUE_TASK": return {"action": f"Get status + a new committed date for task {t['id']} '{t['title'][:50]}'", "owner": owner or "OWNER NEEDED", "deadline": today, "verify": "register row shows the new deadline or status Արված on read-back"}
    if kind == "DUE_TODAY": return {"action": f"Confirm completion evidence for task {t['id']} by end of day", "owner": owner or "OWNER NEEDED", "deadline": f"{today} EOD", "verify": "status Արված with evidence in the register"}
    if kind == "BLOCKED_TASK": return {"action": f"Unblock task {t['id']}: name what is awaited and from whom", "owner": owner or "OWNER NEEDED", "deadline": today, "verify": "status changes from Սպասում or the dependency is recorded"}
    if kind == "DECISION_PENDING": return {"action": f"Decide on task {t['id']} '{t['title'][:50]}'", "owner": "Գև", "deadline": t.get("due") or UNKNOWN, "verify": "decision logged (decision_logging) and the register updated"}
    if kind == "UNCLEAR_TASK": return {"action": f"Clarify scope/next step of task {t['id']}", "owner": owner or "Գև", "deadline": today, "verify": "status moves from Պարզ չէ to Ընթացքում/Չսկսված with a concrete next step"}
    return {"action": f"Review task {t['id']}", "owner": owner or UNKNOWN, "deadline": UNKNOWN, "verify": "register read-back"}

def _gev(t, kind):
    if kind == "OWNERLESS_TASK": return {"required": True, "category": "OWNER NEEDED", "why": "only Gev assigns ownership in the management register"}
    if kind == "DECISION_PENDING": return {"required": True, "category": "DECISION", "why": "the register marks this item as a decision held by Gev"}
    if kind == "OVERDUE_TASK" and t.get("gev_owned"): return {"required": True, "category": "DECISION", "why": "Gev owns the item — only Gev can close, delegate or re-date it"}
    if kind == "OVERDUE_TASK" and t.get("days") is not None and t["days"] <= -7 and t.get("waiting_for"): return {"required": True, "category": "ESCALATION", "why": f"{-t['days']} days overdue with the ball at {t.get('holder')} — escalation is Gev's call"}
    if kind == "UNCLEAR_TASK": return {"required": True, "category": "MISSING BUSINESS TRUTH", "why": "the register says 'Պարզ չէ' — the definition of done is missing"}
    return {"required": False}

def _exc(kind, subject, sev, urg, impact, cause, rec, gev, prov, what, why, deadline=None, dependency=None):
    return {"id": f"EXC-{_hid(kind, subject.get('ref'))}", "kind": kind, "severity": sev, "urgency": urg, "impact": impact, "cause": cause, "recommendation": rec, "gev": gev, "subject": subject,
            "what": what, "why": why, "deadline": deadline, "dependency": dependency, "provenance": prov}

def exceptions(state):
    """Proven exceptions only, ranked severity → urgency → impact → deadline → dependency. Visibility gaps are reported separately (never 'fine')."""
    today = datetime.date.fromisoformat(state["today"]); out = []; tp = state["task_provenance"]
    for t in state["open_tasks"]:
        subj = {"ref": f"task:{t['id']}", "id": t["id"], "title": t["title"], "owner": t["owner"] or UNKNOWN, "due": t["due"] or UNKNOWN, "status": t["status"], "source": "INT-TASKS"}
        prov = {**tp, "record_id": t["record_id"]}; dep = f"waiting on {t['holder']}" if t.get("waiting_for") and t.get("blocked") else None
        kinds = []
        if t["overdue"]: kinds.append("OVERDUE_TASK")
        elif t["due_today"]: kinds.append("DUE_TODAY")
        if t["ownerless"]: kinds.append("OWNERLESS_TASK")
        if t["blocked"]: kinds.append("BLOCKED_TASK")
        if t["unclear"]: kinds.append("UNCLEAR_TASK")
        if t["decision_needed"]: kinds.append("DECISION_PENDING")
        if t["critical"] and t["no_deadline"]: kinds.append("CRITICAL_NO_DEADLINE")
        late = (-t["days"]) if t["days"] is not None else UNKNOWN
        for k in kinds:
            what = {"OVERDUE_TASK": f"Task {t['id']} is {late} day(s) overdue, status {t['status']}, owner {t['owner'] or UNKNOWN}", "DUE_TODAY": f"Task {t['id']} is due today and still {t['status']}",
                    "OWNERLESS_TASK": f"Task {t['id']} has no owner", "BLOCKED_TASK": f"Task {t['id']} is waiting ({t['status']}) — ball with {t.get('holder') or UNKNOWN}", "UNCLEAR_TASK": f"Task {t['id']} is marked 'Պարզ չէ' (unclear)",
                    "DECISION_PENDING": f"Task {t['id']} awaits a decision by {t['owner']}", "CRITICAL_NO_DEADLINE": f"Task {t['id']} is marked critical but has no deadline"}[k]
            why = {"OVERDUE_TASK": "a missed commitment to the principal; every extra day erodes credibility", "DUE_TODAY": "today is the last day to keep the commitment", "OWNERLESS_TASK": "nobody will move it",
                   "BLOCKED_TASK": "the item cannot progress until the dependency answers", "UNCLEAR_TASK": "work cannot start without a definition of done", "DECISION_PENDING": "dependent work waits for the decision", "CRITICAL_NO_DEADLINE": "a critical item without a date will not be tracked"}[k]
            imp = _impact(t, k) if k != "CRITICAL_NO_DEADLINE" else {"category": "management attention", "level": "MEDIUM", "rationale": "critical item, undated"}
            cause = _cause(t) if k in ("OVERDUE_TASK", "BLOCKED_TASK", "UNCLEAR_TASK", "OWNERLESS_TASK") else {"kind": "UNKNOWN", "text": "not applicable", "evidence": []}
            rec = _recommend(t, k, today.isoformat()) if k != "CRITICAL_NO_DEADLINE" else {"action": f"Set a deadline for critical task {t['id']}", "owner": "Գև", "deadline": today.isoformat(), "verify": "register row carries a due date"}
            gev = _gev(t, k) if k != "CRITICAL_NO_DEADLINE" else {"required": True, "category": "DECISION", "why": "only Gev dates the principal's critical asks"}
            out.append(_exc(k, subj, _severity(t, k), _urgency(t, k), imp, cause, rec, gev, prov, what, why, deadline=t["due"], dependency=dep))
    for c in state["schedule_conflicts"]:
        subj = {"ref": f"conflict:{c['a']}|{c['b']}", "title": f"{c['a']} ↔ {c['b']}", "owner": "Գև", "due": state["today"], "status": "overlap", "source": "INT-OL-CAL"}
        out.append(_exc("SCHEDULE_CONFLICT", subj, "MEDIUM", "TODAY", {"category": "management attention", "level": "MEDIUM", "rationale": "two meetings overlap today"}, {"kind": "CONFIRMED CAUSE", "text": "overlapping calendar entries", "evidence": [f"{c['overlap_from']}–{c['until']}"]},
                        {"action": f"Choose which of '{c['a']}' / '{c['b']}' to keep or move", "owner": "Գև", "deadline": f"{state['today']} before {str(c['overlap_from'])[11:16]}", "verify": "calendar read-back shows no overlap"}, {"required": True, "category": "PRIORITY CONFLICT", "why": "only Gev decides which meeting wins"},
                        {"integration_id": "INT-OL-CAL", "retrieved_at": state["envelopes"]["INT-OL-CAL"].get("retrieved_at"), "freshness": state["envelopes"]["INT-OL-CAL"].get("freshness")}, f"Meetings overlap today: {c['a']} and {c['b']}", "Gev cannot attend both", deadline=state["today"]))
    for c in state["mail_candidates"]:
        if c.get("duplicate_of") or c["class"] not in ("DECISION", "ACTION"): continue
        k = "MAIL_DECISION" if c["class"] == "DECISION" else "MAIL_ACTION"
        if k == "MAIL_ACTION" and (c.get("age_days") or 0) < 2: continue                       # a request younger than two days is not yet an exception
        subj = {"ref": f"mail:{c['candidate_id']}", "title": str(c.get("subject"))[:80], "owner": "Գև", "due": UNKNOWN, "status": f"{c['class']} · {c.get('age_days')}d", "source": "INT-OL-MAIL", "counterpart": c.get("counterpart")}
        linked = c.get("matched_task") if c.get("task_match") == "MATCHED" else None
        out.append(_exc(k, subj, _severity({}, k), "TODAY" if k == "MAIL_DECISION" else "THIS_WEEK", {"category": "management attention", "level": "MEDIUM" if k == "MAIL_DECISION" else "LOW", "rationale": "a counterpart is waiting for Gev's answer" if k == "MAIL_DECISION" else f"request open {c.get('age_days')} days"},
                        {"kind": "UNKNOWN", "text": "mail alone does not say why it is unanswered", "evidence": c.get("signals", [])}, {"action": f"Reply to {c.get('counterpart')} on '{str(c.get('subject'))[:40]}'" + (f" (linked to task {linked['id']})" if linked else ""), "owner": "Գև", "deadline": state["today"] if k == "MAIL_DECISION" else "this week", "verify": "a sent reply in the conversation (mail read-back)"},
                        {"required": True, "category": "DECISION" if k == "MAIL_DECISION" else "DECISION", "why": "the mail asks Gev for an approval/decision"} if k == "MAIL_DECISION" else {"required": False}, c["provenance"], f"Mail from {c.get('counterpart')}: {str(c.get('subject'))[:60]} ({c['class']}, {c.get('age_days')}d, candidate open loop)",
                        "an explicit request to Gev is waiting" if k == "MAIL_DECISION" else "an unanswered request ages into a broken loop", dependency=(f"task {linked['id']}" if linked else None)))
    for c in state["commitments"]:
        if not c.get("overdue"): continue
        subj = {"ref": f"commitment:{c.get('op_id')}", "title": c.get("text", "")[:80], "owner": c.get("owner") or "Գև", "due": c.get("due"), "status": "OPEN", "source": "deputy-memory"}
        out.append(_exc("COMMITMENT_OVERDUE", subj, "MEDIUM", "NOW", {"category": "management attention", "level": "MEDIUM", "rationale": "Gev's own promise is past its date"}, {"kind": "UNKNOWN", "text": "no evidence why the promise slipped", "evidence": []},
                        {"action": f"Keep or re-date the promise '{c.get('text', '')[:40]}'", "owner": c.get("owner") or "Գև", "deadline": state["today"], "verify": "commitment closed or new due recorded"}, {"required": True, "category": "DECISION", "why": "it is Gev's own commitment"},
                        {"integration_id": "deputy-memory", "record_id": c.get("op_id"), "retrieved_at": state["at"], "freshness": "LIVE"}, f"Promise overdue since {c.get('due')}: {c.get('text', '')[:60]}", "a promise given by Gev is late", deadline=c.get("due")))
    for a in state["actions"]:
        if a["state"] not in ("EXECUTED_UNVERIFIED", "RESULT_UNKNOWN"): continue
        subj = {"ref": f"action:{a['action_id']}", "title": (a.get("intent") or "")[:80], "owner": "Deputy", "due": state["today"], "status": a["state"], "source": "action-runtime"}
        out.append(_exc("ACTION_UNVERIFIED", subj, "HIGH", "NOW", {"category": "compliance/governance", "level": "HIGH", "rationale": "an approved write has no verified outcome"}, {"kind": "CONFIRMED CAUSE", "text": f"the action is in {a['state']}", "evidence": [a["state"]]},
                        {"action": f"Reconcile action {a['action_id']} (re-read the target system) before any retry", "owner": "Deputy", "deadline": state["today"], "verify": "action state VERIFIED or explicitly FAILED"}, {"required": a["state"] == "RESULT_UNKNOWN", "category": "DECISION", "why": "RESULT_UNKNOWN after reconciliation needs Gev's retry decision"} if a["state"] == "RESULT_UNKNOWN" else {"required": False},
                        {"integration_id": "action-runtime", "record_id": a["action_id"], "retrieved_at": state["at"], "freshness": "LIVE"}, f"Approved action {a['action_id']} ({a.get('system')} {a.get('op')}) is {a['state']}", "an unverified write is neither done nor undone"))
    for c in state["business"]["conflicts"]:
        subj = {"ref": f"business:{c['id']}", "title": c.get("topic", "")[:80], "owner": "Գև", "due": UNKNOWN, "status": "SOURCE_CONFLICT", "source": "business-model"}
        out.append(_exc("SOURCE_CONFLICT", subj, "LOW", "LATER", {"category": "management attention", "level": "LOW", "rationale": "two current sources disagree on a business fact"}, {"kind": "CONFIRMED CAUSE", "text": "sources disagree", "evidence": [c["id"]]},
                        {"action": f"Resolve {c['id']}: {c.get('resolution_required', '')[:60]}", "owner": "Գև", "deadline": UNKNOWN, "verify": "the business model sources are updated and rebuilt"}, {"required": True, "category": "MISSING BUSINESS TRUTH", "why": "only the owner can settle which source is right"},
                        {"integration_id": "business-model", "record_id": c["id"], "retrieved_at": state["at"], "freshness": "LIVE"}, f"Business truth conflict {c['id']}: {c.get('topic', '')}", "decisions built on the wrong source misfire"))
    return rank(out)

def rank(items):
    order = {s: i for i, s in enumerate(SEVERITY)}; uo = {u: i for i, u in enumerate(URGENCY)}; io = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    def key(e): return (order.get(e["severity"], 9), uo.get(e["urgency"], 9), io.get((e.get("impact") or {}).get("level"), 9), str(e.get("deadline") or "9999"), 0 if e.get("dependency") else 1, e["id"])
    return sorted(items, key=key)

# ═══════════════════════════════ 4. CHECKPOINTS · CHANGE DETECTION ═══════════════════════════════
def signature(state, exc=None, queue=None):
    """Minimal durable signature for change detection — ids and states only, no payloads, no mail bodies."""
    exc = exc if exc is not None else exceptions(state); queue = queue if queue is not None else gev_queue(state, exc)
    return {"date": state["today"], "tasks": {str(t["id"]): {"status": t["status"], "owner": t["owner"], "due": t["due"], "open": t["open"], "overdue": t["overdue"]} for t in state["tasks"]},
            "mail": {c["candidate_id"]: c["class"] for c in state["mail_candidates"] if not c.get("duplicate_of") and c["class"] in ("ACTION", "DECISION", "DELEGATE")},
            "meetings": sorted(m["record_id"] for m in state["meetings"] if m.get("record_id")), "exceptions": {e["id"]: e["severity"] for e in exc}, "gev": sorted(q["id"] for q in queue),
            "visibility": {k: v["state"] for k, v in state["visibility"].items()}}

def record_checkpoint(state, kind="check", exc=None, queue=None):
    """Durable observation checkpoint (immutable row; one per run, ordered by time). Fixture/supplied runs are recorded as NON_PRODUCTION and ignored by change detection."""
    sig = signature(state, exc, queue); at = state["at"]
    rec = {"kind": kind, "at": at, "date": state["today"], "truth_mode": state["truth_mode"], "signature": sig, "counts": {"tasks": len(sig["tasks"]), "exceptions": len(sig["exceptions"]), "gev": len(sig["gev"])}}
    op = f"CKPT-{kind}-{at.replace(':', '').replace('-', '')}-{_hid(state['truth_mode'], json.dumps(sig, sort_keys=True))}"
    r = _st().record("checkpoints", op, rec); return {"op_id": op, "status": r["status"], "at": at}

def checkpoints(limit=200):
    rows = [r for r in _st().list("checkpoints") if str(r.get("truth_mode", "")).startswith("PRODUCTION") or r.get("kind") == "test"]
    return rows[-limit:]

def previous_checkpoint(since=None, *, before_at=None, allow_test=False):
    """Latest checkpoint at or before `since` (date or ISO time); default: the latest one recorded before `before_at` (the current run)."""
    rows = [r for r in _st().list("checkpoints") if str(r.get("truth_mode", "")).startswith("PRODUCTION") or (allow_test and r.get("kind") == "test")]
    if since:
        s = str(since); s = s + "T23:59:59" if len(s) == 10 else s
        rows = [r for r in rows if str(r.get("at", "")) <= s]
    if before_at: rows = [r for r in rows if str(r.get("at", "")) < str(before_at)]
    return rows[-1] if rows else None

def changes(prev, cur_sig):
    """NEW / CHANGED / RESOLVED / WORSENED / NEEDS_GEV between a previous signature and the current one. Field-level noise (titles, comments) is ignored."""
    out = {"NEW": [], "CHANGED": [], "RESOLVED": [], "WORSENED": [], "NEEDS_GEV": [], "GEV_RESOLVED": []}
    if not prev: return {"available": False, "reason": "no previous production checkpoint — nothing to compare against yet", **out}
    p = prev.get("signature") or prev; pt, ct = p.get("tasks", {}), cur_sig.get("tasks", {})
    for tid, c in ct.items():
        o = pt.get(tid)
        if o is None:
            if c["open"]: out["NEW"].append({"ref": f"task:{tid}", "text": f"new task {tid} ({c['owner'] or UNKNOWN}, due {c['due'] or UNKNOWN})"})
            continue
        if o["open"] and not c["open"]: out["RESOLVED"].append({"ref": f"task:{tid}", "text": f"task {tid} closed ({c['status']})"}); continue
        if not o["open"] and c["open"]: out["WORSENED"].append({"ref": f"task:{tid}", "text": f"task {tid} reopened ({c['status']})", "kind": "reopened"}); continue
        if not c["open"]: continue
        if o["owner"] != c["owner"]: out["CHANGED"].append({"ref": f"task:{tid}", "text": f"task {tid} owner {o['owner'] or UNKNOWN} → {c['owner'] or UNKNOWN}", "kind": "owner"})
        if o["due"] != c["due"]:
            kind = "postponed" if (o["due"] and c["due"] and c["due"] > o["due"]) else "deadline"
            (out["WORSENED"] if kind == "postponed" else out["CHANGED"]).append({"ref": f"task:{tid}", "text": f"task {tid} deadline {o['due'] or UNKNOWN} → {c['due'] or UNKNOWN}", "kind": kind})
        if o["status"] != c["status"]:
            worse = c["status"] in BLOCKED_STATUSES | UNCLEAR_STATUSES
            (out["WORSENED"] if worse else out["CHANGED"]).append({"ref": f"task:{tid}", "text": f"task {tid} status {o['status']} → {c['status']}", "kind": "blocked" if worse else "status"})
        if not o.get("overdue") and c.get("overdue"): out["WORSENED"].append({"ref": f"task:{tid}", "text": f"task {tid} became overdue (due {c['due']})", "kind": "newly_overdue"})
    pm, cm = p.get("mail", {}), cur_sig.get("mail", {})
    for cid, cls in cm.items():
        if cid not in pm: out["NEW"].append({"ref": f"mail:{cid}", "text": f"new {cls} request in mail", "kind": "mail"})
    for cid in pm:
        if cid not in cm: out["CHANGED"].append({"ref": f"mail:{cid}", "text": "mail request no longer in the read window (not proof of resolution)", "kind": "mail_unobserved"})
    for mid in cur_sig.get("meetings", []):
        if mid not in set(p.get("meetings", [])): out["NEW"].append({"ref": f"meeting:{mid}", "text": "new meeting in the horizon", "kind": "meeting"})
    pe, ce = p.get("exceptions", {}), cur_sig.get("exceptions", {}); sev = {s: i for i, s in enumerate(SEVERITY)}
    for eid, s in ce.items():
        if eid in pe and sev.get(s, 9) < sev.get(pe[eid], 9): out["WORSENED"].append({"ref": eid, "text": f"exception severity {pe[eid]} → {s}", "kind": "severity"})
    for eid in pe:
        if eid not in ce: out["RESOLVED"].append({"ref": eid, "text": "exception no longer present", "kind": "exception"})
    pg, cg = set(p.get("gev", [])), set(cur_sig.get("gev", []))
    out["NEEDS_GEV"] = [{"ref": g, "text": "newly requires Gev"} for g in sorted(cg - pg)]; out["GEV_RESOLVED"] = [{"ref": g, "text": "no longer requires Gev"} for g in sorted(pg - cg)]
    pv, cv = p.get("visibility", {}), cur_sig.get("visibility", {})
    for iid, s in cv.items():
        if pv.get(iid) and pv[iid] != s: (out["WORSENED"] if s in ("UNAVAILABLE", "NOT_CONFIGURED", "STALE") else out["CHANGED"]).append({"ref": f"visibility:{iid}", "text": f"{iid} {pv[iid]} → {s}", "kind": "visibility"})
    return {"available": True, "since": prev.get("at"), "since_kind": prev.get("kind"), **out, "meaningful": sum(len(v) for v in out.values())}

# ═══════════════════════════════ 5. GEV QUEUE · OPEN LOOPS ═══════════════════════════════
def gev_queue(state, exc=None):
    exc = exc if exc is not None else exceptions(state); q = {}
    for a in state["actions"]:
        if a["state"] == "APPROVAL_REQUIRED":
            q[f"GEV-{_hid('approval', a['action_id'])}"] = {"category": "APPROVAL", "issue": f"prepared action awaits approval: {(a.get('intent') or '')[:70]}", "why_gev": "AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE — only Gev approves", "required": "OK / GO / Արա / Հաստատում եմ, or reject", "deadline": "24h token validity", "consequence": "the action expires unexecuted", "ref": f"action:{a['action_id']}", "severity": "MEDIUM"}
    for e in exc:
        if not e["gev"].get("required"): continue
        q[f"GEV-{_hid(e['gev']['category'], e['subject']['ref'])}"] = {"category": e["gev"]["category"], "issue": e["what"], "why_gev": e["gev"]["why"], "required": e["recommendation"]["action"], "deadline": e["recommendation"]["deadline"], "consequence": e["why"], "ref": e["subject"]["ref"], "severity": e["severity"], "exception_id": e["id"]}
    head_today = [t for t in state["open_tasks"] if t["gev_owned"] and (t["due_today"] or t["overdue"])]
    if len(head_today) > 5:
        q[f"GEV-{_hid('priority', state['today'])}"] = {"category": "PRIORITY CONFLICT", "issue": f"{len(head_today)} Gev-owned items are due/overdue today", "why_gev": "only Gev can sequence his own commitments", "required": "pick the 3 that get done today; re-date the rest", "deadline": state["today"], "consequence": "everything slips a little instead of the important things closing", "ref": "tasks:head", "severity": "MEDIUM"}
    items = [{"id": k, **v} for k, v in q.items()]; cat = {c: i for i, c in enumerate(("APPROVAL", "ESCALATION", "DECISION", "PRIORITY CONFLICT", "OWNER NEEDED", "MISSING BUSINESS TRUTH"))}; sev = {s: i for i, s in enumerate(SEVERITY)}
    return sorted(items, key=lambda i: (sev.get(i["severity"], 9), cat.get(i["category"], 9), i["id"]))

def _loop_id(kind, ref): return f"LOOP-{_hid(kind, ref)}"

def open_loops(state, exc=None, *, persist=True):
    """Management-level unresolved loops, tracked durably by reference only. Loops close automatically when evidence proves resolution; a loop whose evidence merely left the read window stays OPEN and says so."""
    exc = exc if exc is not None else exceptions(state); st = _st(); now = state["at"]; today = state["today"]
    want = {}
    for t in state["open_tasks"]:
        if t["overdue"]: want[_loop_id("TASK_OVERDUE", t["id"])] = {"kind": "TASK_OVERDUE", "ref": f"task:{t['id']}", "text": f"task {t['id']} overdue since {t['due']}: {t['title'][:60]}", "owner": t["owner"] or UNKNOWN, "source": "INT-TASKS"}
        if t["waiting_for"]: want[_loop_id("WAITING_FOR", t["id"])] = {"kind": "WAITING_FOR", "ref": f"task:{t['id']}", "text": f"waiting for {t['holder']}: {t['title'][:60]}", "owner": t["holder"], "source": "INT-TASKS"}
        if t["decision_needed"]: want[_loop_id("DECISION_PENDING", t["id"])] = {"kind": "DECISION_PENDING", "ref": f"task:{t['id']}", "text": f"decision pending ({t['owner']}): {t['title'][:60]}", "owner": t["owner"], "source": "INT-TASKS"}
    for c in state["mail_candidates"]:
        if c.get("duplicate_of") or c["class"] not in ("ACTION", "DECISION"): continue
        want[_loop_id("MAIL_" + c["class"], c["candidate_id"])] = {"kind": "MAIL_" + c["class"], "ref": f"mail:{c['candidate_id']}", "text": f"{c['class'].lower()} from {c.get('counterpart')}: {str(c.get('subject'))[:60]}", "owner": "Գև", "source": "INT-OL-MAIL", "linked_task": (c.get("matched_task") or {}).get("id") if c.get("task_match") == "MATCHED" else None}
    for c in state["commitments"]:
        want[_loop_id("COMMITMENT", c.get("op_id"))] = {"kind": "COMMITMENT", "ref": f"commitment:{c.get('op_id')}", "text": f"promise: {c.get('text', '')[:60]} (due {c.get('due') or UNKNOWN})", "owner": c.get("owner") or "Գև", "source": "deputy-memory"}
    for a in state["actions"]:
        if a["state"] in ("EXECUTED_UNVERIFIED", "RESULT_UNKNOWN"): want[_loop_id("ACTION_UNVERIFIED", a["action_id"])] = {"kind": "ACTION_UNVERIFIED", "ref": f"action:{a['action_id']}", "text": f"approved action {a['action_id']} is {a['state']}", "owner": "Deputy", "source": "action-runtime"}
    existing = {r["op_id"]: r for r in st.list("loops")} if persist else {}
    result = {"open": [], "closed_now": [], "unobserved": []}
    task_by_id = {str(t["id"]): t for t in state["tasks"]}; act_by_id = {a["action_id"]: a for a in state["actions"]}; commit_ids = {c.get("op_id") for c in state["commitments"]}
    mail_seen = state["visibility"].get("INT-OL-MAIL", {}).get("usable", False)
    for lid, l in want.items():
        old = existing.get(lid) or {}
        lt = old.get("linked_task") if old.get("linked_task") is not None else l.get("linked_task")
        if l["kind"].startswith("MAIL_") and lt is not None and (task_by_id.get(str(lt)) or {}).get("open") is False:      # the task this mail was about is closed → the loop is resolved by evidence
            closed = {**old, **l, "linked_task": lt, "state": "CLOSED", "closed_at": now, "close_evidence": f"linked task {lt} closed"}
            if persist: st.upsert("loops", lid, closed)
            result["closed_now"].append({"id": lid, **closed}); continue
        rec = {**l, "linked_task": lt, "state": "OPEN", "opened_at": old.get("opened_at") or now, "last_seen": now, "seen_count": int(old.get("seen_count") or 0) + 1, "closed_at": None, "close_evidence": None}
        if persist: st.upsert("loops", lid, rec)
        result["open"].append({"id": lid, **rec})
    for lid, old in existing.items():
        if lid in want or old.get("state") != "OPEN": continue
        kind, ref = old.get("kind"), str(old.get("ref", "")); ev = None
        if kind in ("TASK_OVERDUE", "WAITING_FOR", "DECISION_PENDING"):
            t = task_by_id.get(ref.split(":", 1)[-1])
            if t is None: ev = None if state["task_provenance"]["state"] not in ("LIVE", "CACHED", "SUPPLIED", "FIXTURE") else "task no longer in the register"
            elif not t["open"]: ev = f"task {t['id']} closed ({t['status']})"
            elif kind == "TASK_OVERDUE" and not t["overdue"]: ev = f"task {t['id']} re-dated to {t['due']}"
            elif kind == "WAITING_FOR" and not t["waiting_for"]: ev = f"task {t['id']} owner now {t['owner']}"
            elif kind == "DECISION_PENDING" and not t["decision_needed"]: ev = f"task {t['id']} decision recorded / owner {t['owner']}"
        elif kind == "ACTION_UNVERIFIED":
            a = act_by_id.get(ref.split(":", 1)[-1])
            if a is None:
                try:
                    import actions as A; rec_a = A.get(ref.split(":", 1)[-1]); ev = f"action {rec_a['state']}" if rec_a and rec_a["state"] in ("VERIFIED", "FAILED", "REJECTED") else None
                except Exception: ev = None
        elif kind == "COMMITMENT": ev = "commitment no longer open" if ref.split(":", 1)[-1] not in commit_ids else None
        elif kind and kind.startswith("MAIL_"):
            lt = old.get("linked_task"); t = task_by_id.get(str(lt)) if lt is not None else None
            if t is not None and not t["open"]: ev = f"linked task {t['id']} closed"
            elif mail_seen: result["unobserved"].append({"id": lid, **old, "note": "not in the current mail window — not proof of resolution"}); continue
        if ev:
            closed = {**old, "state": "CLOSED", "closed_at": now, "close_evidence": ev}
            if persist: st.upsert("loops", lid, closed)
            result["closed_now"].append({"id": lid, **closed})
        else: result["open"].append({"id": lid, **old, "note": "kept open — no evidence of resolution in this read"})
    result["count_open"] = len(result["open"])
    return result

# ═══════════════════════════════ 6. SALES / OPERATIONS FRAMEWORKS ═══════════════════════════════
SALES_DIMENSIONS = {
 "target_vs_actual": {"needs": ["INT-MB (activations)", "business targets (targets.json APPROVED)"], "sources": ["INT-MB"]},
 "sales_pace": {"needs": ["INT-MB daily activations"], "sources": ["INT-MB"]},
 "forecast": {"needs": ["INT-MB activation history ≥ 3 months"], "sources": ["INT-MB"]},
 "funnel_conversion": {"needs": ["INT-B24 crm.leads + crm.deals + crm.stages"], "sources": ["INT-B24"]},
 "pipeline_health": {"needs": ["INT-B24 crm.deals"], "sources": ["INT-B24"]},
 "stagnant_opportunities": {"needs": ["INT-B24 crm.deals (date_modify)"], "sources": ["INT-B24"]},
 "lost_opportunities": {"needs": ["INT-B24 crm.deals + crm.stages (LOSE semantics)"], "sources": ["INT-B24"]},
 "retention_churn": {"needs": ["INT-MB subscriber status / churn export"], "sources": ["INT-MB"]},
 "revenue_leakage": {"needs": ["INT-MB billing vs activations"], "sources": ["INT-MB"]},
 "sales_backlog": {"needs": ["INT-B24 activities / b24 tasks"], "sources": ["INT-B24"]},
 "follow_up_failures": {"needs": ["INT-B24 crm.activities (overdue, not completed)"], "sources": ["INT-B24"]},
}
OPS_DIMENSIONS = {
 "operational_backlog": {"sources": ["INT-TASKS"], "needs": ["INT-B24 tasks/tickets for field work"]},
 "sla_risks": {"sources": ["INT-B24"], "needs": ["INT-B24 tickets with SLA fields"]},
 "overdue_work": {"sources": ["INT-TASKS"], "needs": []},
 "failed_rework": {"sources": ["INT-B24"], "needs": ["INT-B24 repeat-visit records"]},
 "complaints_escalations": {"sources": ["INT-B24", "INT-OL-MAIL"], "needs": ["INT-B24 complaint tickets"]},
 "capacity_bottlenecks": {"sources": ["INT-B24"], "needs": ["INT-B24 workload per technician"]},
 "people_bottlenecks": {"sources": ["INT-TASKS"], "needs": []},
 "cross_functional_blockers": {"sources": ["INT-TASKS"], "needs": []},
 "unresolved_handoffs": {"sources": ["INT-TASKS"], "needs": []},
 "aging_work": {"sources": ["INT-TASKS"], "needs": []},
 "repeated_exceptions": {"sources": ["deputy-memory"], "needs": []},
 "slipped_commitments": {"sources": ["INT-TASKS", "deputy-memory"], "needs": []},
}

def _unavail(dim, spec, vis):
    srcs = [s for s in spec["sources"] if s.startswith("INT-")]
    missing = [f"{s}: {vis.get(s, {}).get('state', 'UNKNOWN')}" + (f" — {vis[s].get('unblock')}" if vis.get(s, {}).get("unblock") else (" (by Gev, no activation requested)" if vis.get(s, {}).get("state") == "DEFERRED" else "")) for s in srcs if not vis.get(s, {}).get("usable")]
    return {"dimension": dim, "status": "UNAVAILABLE / NOT CONNECTED", "value": UNKNOWN, "missing": missing or spec["needs"], "needs": spec["needs"], "signals": []}

def sales_intelligence(state, envelopes=None):
    """Production framework: a dimension is computed only from a usable live source; otherwise UNAVAILABLE / NOT CONNECTED with the exact missing capability. Never a demo number."""
    vis = state["visibility"]; today = datetime.date.fromisoformat(state["today"]); out = {}; envs = envelopes or {}
    b24 = envs.get("INT-B24") if (envs.get("INT-B24") or {}).get("status") == "OK" else None
    deals = (b24 or {}).get("records", []) if b24 and (b24.get("kind") == "deal") else []
    acts = (envs.get("INT-B24-activities") or {}).get("records", []) if (envs.get("INT-B24-activities") or {}).get("status") == "OK" else []
    for dim, spec in SALES_DIMENSIONS.items():
        usable = all(vis.get(s, {}).get("usable") for s in spec["sources"]) and (dim not in ("funnel_conversion", "pipeline_health", "stagnant_opportunities", "lost_opportunities", "sales_backlog", "follow_up_failures") or deals or acts)
        if not usable: out[dim] = _unavail(dim, spec, vis); continue
        prov = {"integration_id": spec["sources"][0], "retrieved_at": (b24 or {}).get("retrieved_at"), "freshness": (b24 or {}).get("freshness"), "mode": (b24 or {}).get("mode")}
        if dim == "pipeline_health":
            open_d = [d for d in deals if not d.get("closed")]; by_stage = {}
            for d in open_d: by_stage[d.get("stage_id") or UNKNOWN] = by_stage.get(d.get("stage_id") or UNKNOWN, 0) + 1
            val = sum(float(d.get("opportunity") or 0) for d in open_d)
            out[dim] = {"dimension": dim, "status": "OK", "value": {"open_deals": len(open_d), "by_stage": by_stage, "pipeline_value": val if any(d.get("opportunity") for d in open_d) else UNKNOWN}, "signals": ([f"{len(open_d)} open deals"] if open_d else ["pipeline empty"]), "provenance": prov}
        elif dim == "stagnant_opportunities":
            stag = [d for d in deals if not d.get("closed") and d.get("date_modify") and (today - datetime.date.fromisoformat(str(d["date_modify"])[:10])).days >= 14]
            out[dim] = {"dimension": dim, "status": "OK", "value": {"stagnant_14d": len(stag), "deals": [{"id": d.get("source_record_id"), "title": d.get("title"), "stage": d.get("stage_id"), "idle_days": (today - datetime.date.fromisoformat(str(d["date_modify"])[:10])).days} for d in stag[:10]]}, "signals": [f"{len(stag)} deals idle ≥14 days"] if stag else ["no stagnant deal"], "provenance": prov}
        elif dim == "lost_opportunities":
            lost = [d for d in deals if d.get("closed") and "LOSE" in str(d.get("stage_id", "")).upper()]
            out[dim] = {"dimension": dim, "status": "OK", "value": {"lost": len(lost)}, "signals": [f"{len(lost)} lost deals in the read window"] if lost else ["no lost deal in the read window"], "provenance": prov}
        elif dim == "follow_up_failures":
            late = [a for a in acts if not a.get("completed") and a.get("deadline") and str(a["deadline"])[:10] < today.isoformat()]
            out[dim] = {"dimension": dim, "status": "OK", "value": {"overdue_activities": len(late)}, "signals": [f"{len(late)} CRM activities past deadline and not completed"] if late else ["no overdue CRM activity"], "provenance": prov}
        elif dim in ("funnel_conversion", "sales_backlog"):
            out[dim] = {"dimension": dim, "status": "PARTIAL", "value": UNKNOWN, "signals": ["deals readable; leads/stages/activities not read in this snapshot"], "needs": spec["needs"], "provenance": prov}
        else: out[dim] = _unavail(dim, spec, vis)
    avail = [d for d, v in out.items() if v["status"] in ("OK", "PARTIAL")]
    try:
        import kpis as KP; kb = KP.bindings_for_dimensions(vis)
        for dim in out: out[dim]["kpi_bindings"] = kb.get(dim, [])
    except Exception as e: kb = {"error": f"{type(e).__name__}: {e}"}
    return {"dimensions": out, "available": avail, "unavailable": [d for d in out if d not in avail], "kpi_bindings": kb, "verdict": ("UNAVAILABLE / NOT CONNECTED — no live sales source; the framework is ready, the sources are not" if not avail else f"{len(avail)}/{len(out)} dimensions readable"),
            "sources": {s: {"state": vis.get(s, {}).get("state"), "certification": vis.get(s, {}).get("certification"), "unblock": vis.get(s, {}).get("unblock")} for s in ("INT-B24", "INT-MB")}}

def operations_intelligence(state, exc=None):
    """Operations framework from what IS live (the task register, mail, Deputy memory); field/SLA/complaint dimensions stay UNAVAILABLE until INT-B24 is connected."""
    vis = state["visibility"]; exc = exc if exc is not None else exceptions(state); out = {}; ot = state["open_tasks"]; tasks_ok = vis.get("INT-TASKS", {}).get("usable")
    tp = state["task_provenance"]
    def ok(dim, value, signals): out[dim] = {"dimension": dim, "status": "OK", "value": value, "signals": signals, "provenance": tp}
    for dim, spec in OPS_DIMENSIONS.items():
        if not tasks_ok and "INT-TASKS" in spec["sources"]: out[dim] = _unavail(dim, spec, vis); continue
        if dim == "operational_backlog":
            by_owner = {}
            for t in ot: by_owner[t["owner"] or UNKNOWN] = by_owner.get(t["owner"] or UNKNOWN, 0) + 1
            ok(dim, {"open_tasks": len(ot), "by_owner": by_owner, "field_backlog": "UNAVAILABLE — " + "; ".join(spec["needs"])}, [f"{len(ot)} open register items"])
        elif dim == "overdue_work":
            od = [t for t in ot if t["overdue"]]; ok(dim, {"overdue": len(od), "ids": [t["id"] for t in od]}, [f"{len(od)} overdue" if od else "nothing overdue"])
        elif dim == "people_bottlenecks":
            cnt = {}
            for t in ot:
                if t["overdue"]: cnt[t["holder"] or t["owner"] or UNKNOWN] = cnt.get(t["holder"] or t["owner"] or UNKNOWN, 0) + 1
            hot = {k: v for k, v in cnt.items() if v >= 3}
            ok(dim, {"overdue_by_person": cnt, "bottlenecks": hot}, [f"{k} holds {v} overdue items" for k, v in hot.items()] or ["no person holds ≥3 overdue items"])
        elif dim == "cross_functional_blockers":
            wf = [t for t in ot if t["waiting_for"] and t["blocked"]]                       # evidence = explicit waiting status with the ball at a counterpart; lateness alone is not a block
            ok(dim, {"blocked_waiting": [{"id": t["id"], "holder": t["holder"], "days": t["days"]} for t in wf]}, [f"{len(wf)} items stuck with a counterpart"] if wf else ["no cross-functional block in evidence"])
        elif dim == "unresolved_handoffs":
            hh = [t for t in ot if t["ownerless"] or t["unclear"]]
            ok(dim, {"ownerless_or_unclear": [t["id"] for t in hh]}, [f"{len(hh)} items without owner or definition"] if hh else ["no unresolved handoff in evidence"])
        elif dim == "aging_work":
            ages = sorted([-t["days"] for t in ot if t["overdue"]], reverse=True)
            ok(dim, {"oldest_overdue_days": ages[0] if ages else 0, "overdue_age_distribution": ages}, [f"oldest overdue item: {ages[0]} days"] if ages else ["no aging overdue work"])
        elif dim == "slipped_commitments":
            sl = [c for c in state["commitments"] if c.get("overdue")] + [t for t in ot if t["overdue"] and t["gev_owned"]]
            ok(dim, {"slipped": len(sl)}, [f"{len(sl)} slipped commitments (register + memory)"] if sl else ["no slipped commitment in evidence"])
        elif dim == "repeated_exceptions":
            hist = checkpoints(60); rep = {}
            for r in hist:
                for eid in (r.get("signature") or {}).get("exceptions", {}): rep[eid] = rep.get(eid, 0) + 1
            cur = {e["id"]: e for e in exc}; repeated = [{"id": eid, "seen": n, "what": cur[eid]["what"]} for eid, n in rep.items() if n >= 3 and eid in cur]
            out[dim] = {"dimension": dim, "status": "OK" if hist else "PARTIAL", "value": {"repeated": repeated, "checkpoints_considered": len(hist)}, "signals": [f"{len(repeated)} exceptions seen in ≥3 checkpoints"] if hist else ["no checkpoint history yet"], "provenance": {"integration_id": "deputy-memory"}}
        elif dim == "complaints_escalations":
            esc = [c for c in state["mail_candidates"] if c["class"] in ("ACTION", "DECISION") and re.search(r"(complain|escalat|urgent|բողոք|շտապ|էսկալ)", str(c.get("subject", "")) + str(c.get("signals", "")), re.I)]
            if vis.get("INT-OL-MAIL", {}).get("usable"): out[dim] = {"dimension": dim, "status": "PARTIAL", "value": {"mail_escalation_candidates": len(esc)}, "signals": [f"{len(esc)} escalation-like mails"] if esc else ["no escalation signal in mail"], "needs": spec["needs"], "provenance": {"integration_id": "INT-OL-MAIL"}}
            else: out[dim] = _unavail(dim, spec, vis)
        else: out[dim] = _unavail(dim, spec, vis)
    avail = [d for d, v in out.items() if v["status"] in ("OK", "PARTIAL")]
    return {"dimensions": out, "available": avail, "unavailable": [d for d in out if d not in avail], "verdict": f"{len(avail)}/{len(out)} dimensions readable; field/SLA/complaint dimensions need INT-B24"}

# ═══════════════════════════════ 7. MANAGEMENT OUTPUT ═══════════════════════════════
def management_answer(e):
    """The seven-question management contract for one exception. Conclusion first."""
    return {"WHAT_HAPPENED": e["what"], "WHY_IT_MATTERS": f"{e['why']} (impact {e['impact']['level']} · {e['impact']['category']}: {e['impact']['rationale']})", "WHAT_CAUSED_IT": f"{e['cause']['kind']} — {e['cause']['text']}" + (f" [evidence: {'; '.join(e['cause']['evidence'])}]" if e["cause"].get("evidence") else ""),
            "RECOMMENDATION": e["recommendation"]["action"], "OWNER": e["recommendation"]["owner"], "BY_WHEN": e["recommendation"]["deadline"], "GEV_ACTION": (f"{e['gev']['category']}: {e['gev']['why']}" if e["gev"].get("required") else "none"),
            "VERIFY": e["recommendation"]["verify"], "severity": e["severity"], "urgency": e["urgency"], "provenance": e["provenance"], "id": e["id"]}

def action_line(e): r = e["recommendation"]; return f"{r['action']} → {r['owner']} → {r['deadline']} → {r['verify']}"

def visibility_lines(state):
    out = []
    for iid, v in state["visibility"].items():
        if v["usable"]: out.append(f"{iid}: {v['state']}" + (f" ({v.get('cache_age_seconds')}s cache)" if v["state"] == "CACHED" else "") + f" · {v['count']} · read {(v.get('retrieved_at') or '')[11:16]}")
        elif v["state"] == "DEFERRED": out.append(f"{iid}: DEFERRED by {(v.get('deferred') or {}).get('by', 'Gev')} — no activation requested")
        else: out.append(f"{iid}: {v['state']} ({v.get('code')}) — last successful read {(v.get('last_success') or 'never')[:16]}" + (f" · unblock: {v['unblock'][:80]}" if v.get("unblock") else ""))
    return out

def brief(state, *, exc=None, since=None, record=True, kind="brief"):
    """Morning brief: TOP LINE · CHANGES · SALES · OPERATIONS · TASKS · CALENDAR · MAIL · RISKS · ACTIONS · GEV — concise, evidence-only."""
    exc = exc if exc is not None else exceptions(state); queue = gev_queue(state, exc); sig = signature(state, exc, queue)
    prev = previous_checkpoint(since, before_at=state["at"]); ch = changes(prev, sig)
    loops = open_loops(state, exc, persist=record)
    sales = sales_intelligence(state); ops = operations_intelligence(state, exc)
    ot = state["open_tasks"]
    top = [management_answer(e) for e in exc[:5]]
    tasks = {"overdue": [t for t in ot if t["overdue"]], "due_today": [t for t in ot if t["due_today"]], "due_soon": [t for t in ot if t["due_soon"]], "blocked": [t for t in ot if t["blocked"] or t["unclear"]], "ownerless": [t for t in ot if t["ownerless"]], "gev_owned": [t for t in ot if t["gev_owned"]], "waiting_for": [t for t in ot if t["waiting_for"]], "decision_needed": [t for t in ot if t["decision_needed"]], "no_deadline": [t for t in ot if t["no_deadline"]], "provenance": state["task_provenance"]}
    cal = {"today": [m for m in state["meetings"] if m["today"]], "upcoming": [m for m in state["meetings"] if not m["today"]][:5], "conflicts": state["schedule_conflicts"], "decision_meetings": [m for m in state["meetings"] if m["kind"] == "DECISION"], "needs_preparation": [m for m in state["meetings"] if m["missing_prep"] or not m["related_tasks"]][:5], "visibility": state["visibility"]["INT-OL-CAL"]}
    mail = {"decision_requests": [c for c in state["mail_candidates"] if c["class"] == "DECISION" and not c.get("duplicate_of")], "action_requests": [c for c in state["mail_candidates"] if c["class"] == "ACTION" and not c.get("duplicate_of")], "linked_to_tasks": [c for c in state["mail_candidates"] if c.get("task_match") == "MATCHED"], "commitment_candidates": [c for c in state["mail_candidates"] if c.get("commitment_candidate")], "total_candidates": len(state["mail_candidates"]), "visibility": state["visibility"]["INT-OL-MAIL"]}
    risks = [{"level": e["severity"], "text": e["what"], "id": e["id"]} for e in exc] + [{"level": "MEDIUM" if v["critical"] else "LOW", "text": f"{iid} {v['state']} — visibility gap, not a business fact", "id": f"VIS-{iid}"} for iid, v in state["visibility"].items() if not v["usable"] and v["state"] != "DEFERRED"]
    chat = state.get("chat") or {}; chat_block = {"channels": chat.get("channels", {}), "requests_to_answer": chat.get("requests_to_answer", []), "follow_ups_owed": chat.get("follow_ups_owed", []), "commitment_candidates": chat.get("commitment_candidates", []), "escalations": chat.get("escalations", []), "injection_flagged": chat.get("injection_flagged", []), "duplicates": chat.get("duplicates", [])}
    out = {"status": "EXECUTED", "date": state["today"], "at": state["at"], "truth_mode": state["truth_mode"],
           "TOP_LINE": {"needs_gev": len(queue), "exceptions": len(exc), "highest": exc[0]["what"] if exc else "no proven exception in the visible systems", "visibility_gaps": state["unavailable"], "summary": top[:3]},
           "CHANGES": ch, "SALES": sales, "OPERATIONS": ops, "TASKS": tasks, "CALENDAR": cal, "MAIL": mail, "CHAT": chat_block, "RISKS": risks, "ACTIONS": [action_line(e) for e in exc[:7]], "GEV_ACTION": queue,
           "open_loops": loops, "exceptions": exc, "answers": top, "visibility": state["visibility"], "visibility_lines": visibility_lines(state), "unavailable": state["unavailable"], "critical_unavailable": state["critical_unavailable"]}
    if record: out["checkpoint"] = record_checkpoint(state, kind, exc, queue)
    return out

def exception_view(state, exc=None):
    exc = exc if exc is not None else exceptions(state)
    return {"status": "EXECUTED", "date": state["today"], "truth_mode": state["truth_mode"], "exceptions": [management_answer(e) for e in exc], "count": len(exc), "ranking": "severity → urgency → impact → deadline → dependency",
            "verdict": ("no proven exception in the systems Deputy can see" if not exc else f"{len(exc)} proven exception(s); highest: {exc[0]['what']}"), "visibility_incomplete": bool(state["unavailable"]), "unavailable": state["unavailable"], "visibility_lines": visibility_lines(state),
            "note": ("visibility is incomplete — " + ", ".join(state["unavailable"]) + " cannot be seen; 'no exception' covers only the visible systems") if state["unavailable"] else "all declared systems were readable"}

def change_view(state, since=None, exc=None, record=True):
    exc = exc if exc is not None else exceptions(state); queue = gev_queue(state, exc); sig = signature(state, exc, queue)
    prev = previous_checkpoint(since, before_at=state["at"]); ch = changes(prev, sig)
    out = {"status": "EXECUTED", "date": state["today"], "truth_mode": state["truth_mode"], "since": since or (prev or {}).get("at"), "changes": ch, "groups": {k: ch.get(k, []) for k in ("NEW", "CHANGED", "RESOLVED", "WORSENED", "NEEDS_GEV")}, "visibility_lines": visibility_lines(state)}
    if record: out["checkpoint"] = record_checkpoint(state, "change_review", exc, queue)
    return out

def eod_view(state, exc=None, record=True):
    exc = exc if exc is not None else exceptions(state); queue = gev_queue(state, exc); sig = signature(state, exc, queue)
    prev = previous_checkpoint(state["today"] + "T00:00:00", before_at=state["at"]) or previous_checkpoint(before_at=state["at"])
    ch = changes(prev, sig); ot = state["open_tasks"]; today = state["today"]
    planned = [t for t in state["tasks"] if t["due"] == today] + [t for t in ot if t["overdue"]]
    completed = [t for t in state["tasks"] if not t["open"] and (t["due"] == today or any(r["ref"] == f"task:{t['id']}" for r in ch.get("RESOLVED", [])))]
    slipped = [t for t in ot if t["due_today"] or t["overdue"]]
    moved = [r for r in ch.get("WORSENED", []) if r.get("kind") == "postponed"]
    out = {"status": "EXECUTED", "date": today, "truth_mode": state["truth_mode"], "planned_today": planned, "completed": completed, "slipped": slipped, "moved_to_tomorrow": moved,
           "unverified": [a for a in state["actions"] if a["state"] in ("EXECUTED_UNVERIFIED", "RESULT_UNKNOWN")], "escalation_required": [management_answer(e) for e in exc if e["gev"].get("category") == "ESCALATION" or (e["kind"] == "OVERDUE_TASK" and (e["subject"].get("due") or "") < today and e["severity"] == "HIGH")],
           "gev_decisions": queue, "changes_today": ch, "tomorrow": [t for t in ot if t["days"] == 1], "visibility_lines": visibility_lines(state), "note": "no external mutation; slipped items need a new committed date through the Action Runtime (approval)"}
    if record: out["checkpoint"] = record_checkpoint(state, "eod", exc, queue)
    return out

def weekly_view(state, exc=None, days=7):
    exc = exc if exc is not None else exceptions(state); queue = gev_queue(state, exc); today = datetime.date.fromisoformat(state["today"])
    hist = [r for r in checkpoints(400) if str(r.get("date", "")) >= (today - datetime.timedelta(days=days)).isoformat()]
    base = hist[0] if hist else None; ch = changes(base, signature(state, exc, queue)) if base else {"available": False, "reason": f"no production checkpoint within the last {days} days"}
    rep = {}
    for r in hist:
        for eid in (r.get("signature") or {}).get("exceptions", {}): rep[eid] = rep.get(eid, 0) + 1
    cur = {e["id"]: e for e in exc}; recurring = [{"id": eid, "seen": n, "what": cur[eid]["what"]} for eid, n in rep.items() if n >= 3 and eid in cur]
    ops = operations_intelligence(state, exc); sales = sales_intelligence(state)
    bott = ops["dimensions"].get("people_bottlenecks", {}).get("value", {}).get("bottlenecks", {})
    return {"status": "EXECUTED" if hist else "ASSISTED", "window_days": days, "checkpoints_in_window": len(hist), "truth_mode": state["truth_mode"],
            "major_outcomes": ch.get("RESOLVED", []) if base else [], "missed_commitments": [management_answer(e) for e in exc if e["kind"] in ("OVERDUE_TASK", "COMMITMENT_OVERDUE")], "recurring_issues": recurring,
            "sales_movement": sales["verdict"], "sales": sales, "operational_movement": ops["verdict"], "operations": ops, "top_risks": [{"level": e["severity"], "text": e["what"]} for e in exc[:5]],
            "unresolved_decisions": [q for q in queue if q["category"] in ("DECISION", "APPROVAL", "MISSING BUSINESS TRUTH")], "bottlenecks": bott, "actions_next_week": [action_line(e) for e in exc[:7]], "gev_decisions": queue,
            "changes_in_window": ch, "note": "KPIs without a live source are UNAVAILABLE by design — nothing is fabricated" if not sales["available"] else ""}

def task_view(state, exc=None):
    exc = exc if exc is not None else exceptions(state); ot = state["open_tasks"]
    return {"status": "EXECUTED", "date": state["today"], "truth_mode": state["truth_mode"], "provenance": state["task_provenance"], "overdue": [management_answer(e) for e in exc if e["kind"] == "OVERDUE_TASK"], "due_today": [t for t in ot if t["due_today"]], "due_soon": [t for t in ot if t["due_soon"]],
            "blocked": [management_answer(e) for e in exc if e["kind"] in ("BLOCKED_TASK", "UNCLEAR_TASK")], "ownerless": [management_answer(e) for e in exc if e["kind"] == "OWNERLESS_TASK"], "no_deadline": [t for t in ot if t["no_deadline"]],
            "gev_owned": [t for t in ot if t["gev_owned"]], "waiting_for_gev": [t for t in ot if t["decision_needed"]], "team_commitments": [t for t in ot if t["waiting_for"]], "late_by_person": operations_intelligence(state, exc)["dimensions"].get("people_bottlenecks", {}).get("value", {}).get("overdue_by_person", {}),
            "counts": {"open": len(ot), "overdue": sum(t["overdue"] for t in ot), "due_today": sum(t["due_today"] for t in ot), "blocked": sum(t["blocked"] or t["unclear"] for t in ot), "ownerless": sum(t["ownerless"] for t in ot)}}

def calendar_view(state):
    v = state["visibility"]["INT-OL-CAL"]
    return {"status": "EXECUTED", "date": state["today"], "truth_mode": state["truth_mode"], "visibility": v, "available": v["usable"], "today": [m for m in state["meetings"] if m["today"]], "upcoming": [m for m in state["meetings"] if not m["today"]], "conflicts": state["schedule_conflicts"],
            "by_kind": {k: [m["title"] for m in state["meetings"] if m["kind"] == k] for k in ("DECISION", "FOLLOW_UP", "DEADLINE", "INFO")}, "needs_preparation": [{"title": m["title"], "start": m["start"], "missing": m["missing_prep"] + ([] if m["related_tasks"] else ["no related open task"])} for m in state["meetings"] if m["missing_prep"] or not m["related_tasks"]],
            "linked_tasks": {m["title"]: m["related_tasks"] for m in state["meetings"] if m["related_tasks"]}, "note": None if v["usable"] else f"calendar {v['state']} ({v.get('code')}) — meetings UNKNOWN, last successful read {v.get('last_success') or 'never'}"}

def mail_view(state, exc=None):
    v = state["visibility"]["INT-OL-MAIL"]; c = state["mail_candidates"]
    return {"status": "EXECUTED", "date": state["today"], "truth_mode": state["truth_mode"], "visibility": v, "available": v["usable"], "decision_requests": [x for x in c if x["class"] == "DECISION" and not x.get("duplicate_of")], "action_requests": [x for x in c if x["class"] == "ACTION" and not x.get("duplicate_of")],
            "pending_loops": [x for x in c if x["class"] in ("ACTION", "DECISION") and not x.get("duplicate_of") and (x.get("age_days") or 0) >= 2], "linked_to_tasks": [x for x in c if x.get("task_match") == "MATCHED"], "uncertain_links": [x for x in c if x.get("task_match") == "ENTITY_MATCH_UNCERTAIN"],
            "escalations": [x for x in c if re.search(r"(complain|escalat|urgent|բողոք|շտապ|էսկալ)", str(x.get("subject", "")), re.I)], "promised_follow_ups": [x for x in c if x.get("commitment_candidate")], "total": len(c),
            "note": (None if v["usable"] else f"mail {v['state']} ({v.get('code')}) — nothing can be said about the inbox; last successful read {v.get('last_success') or 'never'}") or "candidates only — a mail becomes a task/commitment only when Gev confirms (no automatic fact); mail stays read-only"}

# ═══════════════════════════════ 8. TEXT RENDERING (concise, Armenian labels) ═══════════════════════════════
def render_brief(b, limit=5):
    L = []; a = L.append
    a(f"DEPUTY DAILY BRIEF — {b['date']} · truth: {b['truth_mode']}")
    tl = b["TOP_LINE"]; a(f"TOP LINE: {tl['needs_gev']} item(s) need Gev · {tl['exceptions']} exception(s) · highest: {tl['highest']}")
    if tl["visibility_gaps"]: a(f"  visibility gaps: {', '.join(tl['visibility_gaps'])}")
    ch = b["CHANGES"]
    a("CHANGES SINCE LAST CHECK: " + (f"since {ch.get('since')}: " + "; ".join(f"{k} {len(ch.get(k, []))}" for k in ("NEW", "CHANGED", "RESOLVED", "WORSENED", "NEEDS_GEV")) if ch.get("available") else ch.get("reason", "n/a")))
    a(f"SALES: {b['SALES']['verdict']}"); a(f"OPERATIONS: {b['OPERATIONS']['verdict']}")
    t = b["TASKS"]; a(f"TASKS: overdue {len(t['overdue'])} · due today {len(t['due_today'])} · blocked {len(t['blocked'])} · ownerless {len(t['ownerless'])} · Gev-owned {len(t['gev_owned'])} · waiting-for {len(t['waiting_for'])}")
    for x in t["overdue"][:limit]: a(f"  · {x['id']}. {x['title'][:55]} — {-x['days']}d overdue · {x['owner'] or 'OWNER NEEDED'}")
    c = b["CALENDAR"]; a(f"CALENDAR: {c['visibility']['state']} · today {len(c['today'])} · conflicts {len(c['conflicts'])} · decision meetings {len(c['decision_meetings'])}")
    for m in c["today"][:limit]: a(f"  · {(m['start'] or '')[11:16]} {m['title'][:50]} [{m['kind']}]" + (" — prep missing" if m["missing_prep"] else ""))
    m = b["MAIL"]; a(f"MAIL: {m['visibility']['state']} · decision requests {len(m['decision_requests'])} · action requests {len(m['action_requests'])} · linked to tasks {len(m['linked_to_tasks'])}")
    for x in (m["decision_requests"] + m["action_requests"])[:limit]: a(f"  · ✉ {x.get('counterpart')}: {str(x.get('subject'))[:50]} ({x['class']}, {x.get('age_days')}d)")
    cb = b.get("CHAT") or {}
    if cb: a("CHAT: " + " · ".join(f"{k} {v.get('state')}" for k, v in (cb.get("channels") or {}).items()) + f" · to answer {len(cb.get('requests_to_answer', []))} · promises {len(cb.get('commitment_candidates', []))} · escalations {len(cb.get('escalations', []))}" + (f" · ⚠ injection-flagged {len(cb['injection_flagged'])}" if cb.get("injection_flagged") else ""))
    a("RISKS: " + ("; ".join(f"[{r['level']}] {r['text'][:60]}" for r in b["RISKS"][:limit]) if b["RISKS"] else "none proven"))
    a("RECOMMENDED ACTIONS:"); [a(f"  · {x}") for x in b["ACTIONS"][:limit]] if b["ACTIONS"] else a("  · none")
    a("GEV ACTION:"); [a(f"  · [{q['category']}] {q['issue'][:70]} → {q['required'][:60]} (by {q['deadline']})") for q in b["GEV_ACTION"][:limit]] if b["GEV_ACTION"] else a("  · nothing requires Gev right now (visible systems only)")
    a("SOURCES: " + " | ".join(b["visibility_lines"]))
    return "\n".join(L)
