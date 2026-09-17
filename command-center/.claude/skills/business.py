# -*- coding: utf-8 -*-
"""BUSINESS CONTEXT LAYER — the Skill System's read access to the Business Operating Model (.claude/business).

Two layers are combined at runtime: CORE (*.json, INTERNAL, versionable; people only as @P tokens; no compensation) and the
SENSITIVE OVERLAY (overlay.json, CONFIDENTIAL, local; token → name, role ↔ person assignments, compensation, commercials,
evidence). Nothing from the overlay is ever written back into the core.

Every governed execution gets `context_for(...)`: playbook, KPIs, processes, owner (ROLE → CURRENT PERSON only when a
CONFIRMED assignment exists), sources, rules, MODEL identity (model_version/schema/fingerprints/state) and GAP codes:
  BUSINESS_CONTEXT_MISSING · OWNER_UNKNOWN · KPI_DEFINITION_MISSING · PROCESS_UNDEFINED · TARGET_UNKNOWN · APPROVAL_RULE_UNKNOWN
  · SOURCE_CONFLICT · STALE_MODEL · SOURCE_CHANGED · SOURCE_MISSING
Fail closed: absent/incompatible/uncertified model → BUSINESS_CONTEXT_MISSING; a fact whose source changed → STALE_MODEL.
Precedence: REFERENCE_APPROVED/CHARTER > ACTIVE_* > EVIDENCE > HISTORICAL; equal-rank disagreement → SOURCE_CONFLICT;
HISTORICAL never overrides CURRENT. Knowledge from conversation enters only as OBSERVATION (state store), never the core.
Overrides for tests: COMMAND_CENTER_BUSINESS_DIR (model dir), COMMAND_CENTER_BUSINESS_ROOT (source root)."""
import json, os, sys, pathlib, re, hashlib, datetime

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CORE_FILES = ("sources", "business_model", "processes", "ownership", "kpis", "targets", "playbooks", "routines", "gaps")
COMPATIBLE_SCHEMAS = ("2.0",)
GAP_CODES = ["BUSINESS_CONTEXT_MISSING", "OWNER_UNKNOWN", "KPI_DEFINITION_MISSING", "PROCESS_UNDEFINED", "TARGET_UNKNOWN", "APPROVAL_RULE_UNKNOWN", "SOURCE_CONFLICT", "STALE_MODEL", "SOURCE_CHANGED", "SOURCE_MISSING"]
CONF_ORDER = ["CONFIRMED", "DERIVED", "UNVERIFIED", "UNKNOWN"]
PROMOTION_STATES = ["OBSERVATION", "PROPOSED", "CONFIRMED", "APPROVED", "SUPERSEDED"]
PERSON_TOKEN = re.compile(r"@P\d+")
_CACHE = {"key": None, "model": None}
LAST_ERROR = {"reason": None}

def _norm(t): return re.sub(r"\s+", " ", str(t or "").lower().strip())
def _dir(): return pathlib.Path(os.environ.get("COMMAND_CENTER_BUSINESS_DIR") or (HERE.parent / "business"))
sys.path.insert(0, str(HERE.parent / "policy")); import paths        # ONE business-root resolver (workspace_policy.json -> business_root)

def _root(): return pathlib.Path(os.environ.get("COMMAND_CENTER_BUSINESS_ROOT") or ROOT)

def _src(root, rel):
    """A declared source path is business-relative (bm_sources.py); the business root is resolved in one place."""
    return paths.resolve(root, rel)

def available():
    d = _dir(); return all((d / f"{f}.json").exists() for f in CORE_FILES)

def last_error(): return LAST_ERROR["reason"]

def load(force=False):
    """Load core (+ overlay + certification). Returns None (see last_error()) when absent, unreadable or schema-incompatible."""
    d = _dir()
    if not available(): LAST_ERROR["reason"] = f"business model not found at {d} — run .claude/business/build_business_model.py"; _CACHE.update(key=None, model=None); return None
    files = [d / f"{f}.json" for f in CORE_FILES] + [d / "overlay.json", d / "certification.json"]
    key = (str(d),) + tuple((p.stat().st_mtime_ns if p.exists() else None) for p in files)
    if not force and _CACHE["key"] == key: return _CACHE["model"]
    try: m = {f: json.loads((d / f"{f}.json").read_text(encoding="utf-8")) for f in CORE_FILES}
    except (OSError, ValueError) as e: LAST_ERROR["reason"] = f"unreadable model: {e}"; _CACHE.update(key=None, model=None); return None
    sv = m["sources"].get("meta", {}).get("schema_version")
    if sv not in COMPATIBLE_SCHEMAS: LAST_ERROR["reason"] = f"SCHEMA_INCOMPATIBLE: model schema {sv!r}, runtime accepts {COMPATIBLE_SCHEMAS} — rebuild the model"; _CACHE.update(key=key, model=None); return None
    try: m["_overlay"] = json.loads((d / "overlay.json").read_text(encoding="utf-8")) if (d / "overlay.json").exists() else None
    except (OSError, ValueError): m["_overlay"] = None
    try: m["_cert"] = json.loads((d / "certification.json").read_text(encoding="utf-8")) if (d / "certification.json").exists() else None
    except (OSError, ValueError): m["_cert"] = None
    m["_sources"] = {s["source_id"]: s for s in m["sources"]["sources"]}
    m["_rank"] = m["sources"].get("authority_rank", {})
    m["_names"] = {p["id"]: p["name"] for p in (m["_overlay"] or {}).get("persons", [])}
    m["_state_cache"] = None
    _CACHE.update(key=key, model=m); LAST_ERROR["reason"] = None
    return m

# ───────────────────────── model identity & staleness ─────────────────────────
def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def _structure_sha(p, s):
    """STRUCTURE fingerprint of a LIVE register — the one definition lives in the builder (no second fingerprint system)."""
    import sys as _sys; d = str(HERE.parent / "business")
    if d not in _sys.path: _sys.path.insert(0, d)
    import build_business_model as bb
    return bb.source_fingerprint({"source_id": "?", "fingerprint_scope": "STRUCTURE", "structure": s.get("structure") or {}}, p)["sha256"]

def model_state(m=None):
    """CURRENT · STALE_MODEL (a current source changed) · SOURCE_MISSING · UNCERTIFIED — with per-source detail."""
    m = m or load()
    if not m: return {"state": "BUSINESS_CONTEXT_MISSING", "reason": last_error(), "changed": [], "missing": [], "certified": False}
    if m.get("_state_cache"): return m["_state_cache"]
    snap = m["sources"].get("source_snapshot", {}); changed, missing = [], []
    root = _root()
    for sid, s in snap.items():
        if s.get("currency") != "CURRENT": continue
        p = _src(root, s["path"])
        if not p.exists(): missing.append(sid); continue
        if s.get("scope") == "STRUCTURE":                                                      # LIVE register: only its structure binds the model; rows are live data read through the integration layer
            try:
                if _structure_sha(p, s) != s.get("sha256"): changed.append(sid)
            except Exception: changed.append(sid)                                               # unreadable structure = fail closed (STALE_MODEL)
            continue
        st = p.stat()
        if st.st_size == s.get("size") and int(st.st_mtime) == s.get("mtime"): continue        # unchanged (cheap check)
        if _sha(p) != s.get("sha256"): changed.append(sid)
    cert = m.get("_cert") or {}; meta = m["sources"]["meta"]
    certified = bool(cert) and cert.get("result") == "PASS" and cert.get("core_fingerprint") == meta.get("core_fingerprint") and cert.get("source_snapshot_id") == meta.get("source_snapshot_id")
    state = "SOURCE_MISSING" if missing else ("STALE_MODEL" if changed else ("UNCERTIFIED" if not certified else "CURRENT"))
    out = {"state": state, "changed": changed, "missing": missing, "certified": certified, "model_version": meta.get("model_version"), "schema_version": meta.get("schema_version"),
           "core_fingerprint": meta.get("core_fingerprint"), "overlay_fingerprint": meta.get("overlay_fingerprint"), "overlay_present": m.get("_overlay") is not None,
           "source_snapshot_id": meta.get("source_snapshot_id"), "generated_at": meta.get("generated_at"), "business_effective_date": meta.get("business_effective_date")}
    m["_state_cache"] = out
    return out

def model_id(m=None):
    st = model_state(m)
    return {k: st.get(k) for k in ("model_version", "schema_version", "core_fingerprint", "overlay_fingerprint", "overlay_present", "source_snapshot_id", "state", "certified")}

def stale_sources_for(src_ids, m=None):
    st = model_state(m); s = set(src_ids or [])
    return {"changed": sorted(s & set(st["changed"])), "missing": sorted(s & set(st["missing"]))}

# ───────────────────────── provenance & precedence ─────────────────────────
def source(sid):
    m = load(); return (m or {}).get("_sources", {}).get(sid)

def is_current(sid):
    s = source(sid); return bool(s) and s.get("currency") == "CURRENT"

def authority(sid):
    s = source(sid); m = load()
    return (m or {}).get("_rank", {}).get(s["authority"], 0) if s else 0

def source_status(sid):
    """What supports a fact: known? current? approved? conflicting? changed since the model was built?"""
    s = source(sid)
    if not s: return {"source_id": sid, "known": False}
    st = stale_sources_for([sid])
    return {"source_id": sid, "known": True, "path": s["path"], "authority": s["authority"], "currency": s["currency"], "approved": s["authority"] in ("REFERENCE_APPROVED", "CHARTER"),
            "status": s["status"], "conflicts": s.get("conflicts", []), "changed_since_build": sid in st["changed"], "missing": sid in st["missing"]}

def resolve_fact(candidates):
    cur = [c for c in candidates if any(is_current(s) for s in c.get("src", []))]
    hist = [c for c in candidates if c not in cur]
    if not cur:
        if hist: return {"status": "HISTORICAL_ONLY", "value": None, "src": sum((c.get("src", []) for c in hist), []), "reason": "only superseded/historical sources hold this fact — not current truth", "historical": hist}
        return {"status": "UNKNOWN", "value": None, "src": [], "reason": "no source"}
    ranked = sorted(cur, key=lambda c: -max((authority(s) for s in c.get("src", []) if is_current(s)), default=0))
    top_rank = max(authority(s) for s in ranked[0].get("src", []) if is_current(s))
    top = [c for c in ranked if max(authority(s) for s in c.get("src", []) if is_current(s)) == top_rank]
    values = {json.dumps(c.get("value"), ensure_ascii=False, sort_keys=True) for c in top}
    if len(values) > 1:
        return {"status": "SOURCE_CONFLICT", "value": None, "src": sum((c.get("src", []) for c in top), []), "reason": "two current sources of equal authority disagree — resolution required, not chosen", "candidates": top}
    out = dict(top[0]); out.update(status="RESOLVED", reason="highest-authority current source" + (" (lower-authority current source overridden, shown)" if len(ranked) > len(top) else ""))
    if len(ranked) > len(top): out["overridden"] = [c for c in ranked if c not in top]
    return out

# ───────────────────────── people: tokens → names only through the overlay ─────────────────────────
def render(text, m=None):
    m = m or load(); names = (m or {}).get("_names", {})
    return PERSON_TOKEN.sub(lambda x: names.get(x.group(0), x.group(0) + "(name withheld — overlay absent)"), str(text))

def person_for_role(role_code, m=None):
    """OWNER ROLE → CURRENT PERSON only through a CONFIRMED overlay assignment; candidates are reported, never promoted."""
    m = m or load(); ov = (m or {}).get("_overlay")
    if not ov: return {"status": "PERSON_UNKNOWN", "reason": "overlay absent — person mappings are CONFIDENTIAL and local", "candidates": []}
    asg = [a for a in ov.get("assignments", []) if a["role"] == role_code]
    conf = [a for a in asg if a["conf"] == "CONFIRMED"]
    if conf:
        a = conf[0]; return {"status": "PERSON_KNOWN", "person": m["_names"].get(a["person"], a["person"]), "token": a["person"], "conf": "CONFIRMED", "src": a["src"], "verified_by": a.get("verified_by"), "date": a.get("date")}
    return {"status": "PERSON_UNKNOWN", "reason": "no CONFIRMED assignment for this role (candidates are DERIVED/UNVERIFIED — not guessed)",
            "candidates": [{"token": a["person"], "person": m["_names"].get(a["person"], a["person"]), "conf": a["conf"], "src": a["src"], "note": a.get("note")} for a in asg]}

def _role_codes(text):
    return re.findall(r"\((\d+\.\d+|EXEC-[A-Z]+|CTR-[A-Z]+)\)", str(text or ""))

def resolve_owner(entry, m=None):
    """Ownership entry → PROCESS/KPI → OWNER ROLE → CURRENT PERSON (or PERSON_UNKNOWN)."""
    codes = _role_codes(entry.get("owner_role"))
    res = {"owner_role": entry.get("owner_role"), "role_codes": codes, "status": entry["status"]}
    if entry["status"] == "OWNER_UNKNOWN": res.update(person_status="OWNER_UNKNOWN"); return res
    if not codes:
        if str(entry.get("owner_person")) in ("Gev", "Deputy"): res.update(person_status="PERSON_KNOWN", person=entry["owner_person"], person_conf="CONFIRMED"); return res
        res.update(person_status="PERSON_UNKNOWN", reason="owner role carries no role code (principal or conflict)"); return res
    p = person_for_role(codes[0], m); res.update(person_status=p["status"], person=p.get("person"), person_conf=p.get("conf"), candidates=p.get("candidates", []))
    return res

# ───────────────────────── queries ─────────────────────────
def _score_words(text, blob):
    q = {w for w in re.findall(r"[\w&-]+", _norm(text)) if len(w) >= 4}
    b = _norm(blob)
    return sum(1 for w in q if w in b)

def find_owner(query):
    m = load()
    if not m: return {"status": "BUSINESS_CONTEXT_MISSING", "code": "BUSINESS_CONTEXT_MISSING", "reason": last_error()}
    q = _norm(query); best, score = None, 0
    for o in m["ownership"]["ownership"]:
        s = sum(3 for a in o.get("aliases", []) if _norm(a) in q) + _score_words(q, o["primitive"] + " " + o["kind"])
        if s > score: best, score = o, s
    if not best or score == 0: return {"status": "OWNER_UNKNOWN", "code": "OWNER_UNKNOWN", "query": query, "reason": "no ownership entry matches; the organization has not defined it"}
    st = best["status"]; code = {"OWNER_UNKNOWN": "OWNER_UNKNOWN", "CONFLICT": "SOURCE_CONFLICT"}.get(st)
    out = {"status": st, "entry": best, "owner_role": best.get("owner_role"), "owner_person_note": best.get("owner_person"), "src": best["src"],
           "conf": "CONFIRMED" if st == "ROLE_AND_PERSON" else ("DERIVED" if st in ("ROLE_DEFINED_PERSON_UNKNOWN", "ROLE_VACANT_INTERIM") else "UNKNOWN"), "resolution": resolve_owner(best, m)}
    if code: out["code"] = code
    if st == "CONFLICT": out["conflicts"] = [c for c in m["business_model"]["conflicts"] if c["id"] in str(best.get("note", ""))]
    stale = stale_sources_for(best["src"], m)
    if stale["missing"]: out["stale"] = "SOURCE_MISSING"; out["stale_sources"] = stale["missing"]
    elif stale["changed"]: out["stale"] = "SOURCE_CHANGED"; out["stale_sources"] = stale["changed"]
    return out

def find_kpis(query, limit=6):
    m = load()
    if not m: return []
    q = _norm(query); scored = []
    for k in m["kpis"]["kpis"]:
        s = _score_words(q, " ".join([k["name"], k["definition"], k["business_purpose"], " ".join(k.get("drill_down", []))]))
        if _norm(k["name"]) in q: s += 5
        if s: scored.append((s, k))
    return [k for s, k in sorted(scored, key=lambda x: -x[0])[:limit]]

def targets_for(ref, m=None):
    m = m or load(); return [t for t in (m or {}).get("targets", {}).get("targets", []) if t["ref"] == ref]

PROCESS_KEYWORDS = {
 "P-SALES-01": ["new sale", "activation", "sale to activation", "վաճառք", "ակտիվացում"], "P-SALES-02": ["d2d", "door to door", "sector", "field sales"], "P-SALES-03": ["telesales", "outbound calls", "հեռավաճառք"],
 "P-SALES-04": ["lead handoff", "marketing lead", "lead response"], "P-SALES-05": ["corporate", "legal entities", "corporate report", "կորպ"], "P-RET-01": ["retention", "churn calls", "save list", "cancellation", "հրաժար", "չըռն"],
 "P-OPS-01": ["installation", "failed installation", "install", "new connection", "տեղադրում", "միացում"], "P-OPS-02": ["repair", "fault", "in-home", "broken internet", "վերանորոգում", "խափանում"],
 "P-OPS-03": ["incident", "outage", "mass outage", "ինցիդենտ"], "P-OPS-04": ["network build", "line acceptance", "splice", "ցանցի կառուցում"], "P-OPS-05": ["cpe", "warehouse", "provisioning", "stock", "պահեստ"],
 "P-CS-01": ["inbound call", "call center", "call handling", "զանգ"], "P-CS-02": ["complaint", "բողոք"], "P-BILL-01": ["billing account", "technical handoff", "tariff attach"], "P-BILL-02": ["invoice", "payment", "unidentified payment", "reconcile payments"],
 "P-BILL-03": ["overdue", "suspension", "collections", "promise to pay", "restoration", "պարտք"], "P-BILL-04": ["discount approval", "correction", "reactivation exception", "write-off", "approval"], "P-BILL-05": ["month-end", "closing", "reconciliation", "համադրում"],
 "P-BILL-06": ["leakage", "revenue assurance", "unbilled"], "P-MGMT-01": ["task intake", "whatsapp", "principal ask"], "P-MGMT-02": ["hiring", "recruit", "phase 1 hires"], "P-MGMT-03": ["bonus", "kpi cycle", "payroll", "բոնուս"],
 "P-MGMT-04": ["weekly review", "s&o review", "weekly sales & operations"], "P-MGMT-05": ["retention tracking", "tracking system"],
}

def find_processes(query, limit=4):
    m = load()
    if not m: return []
    q = _norm(query); scored = []
    for p in m["processes"]["processes"]:
        s = 4 * sum(1 for k in PROCESS_KEYWORDS.get(p["process_id"], []) if _norm(k) in q) + 2 * _score_words(q, p["name"]) + _score_words(q, " ".join([p["purpose"], p["trigger"]]))
        if s: scored.append((s, p))
    return [p for s, p in sorted(scored, key=lambda x: -x[0])[:limit]]

def playbook_for(chain_name=None, query=None):
    m = load()
    if not m: return None
    pbs = m["playbooks"]["playbooks"]
    if chain_name:
        for p in pbs:
            if p["chain"] == chain_name: return p
    if query:
        scored = [(_score_words(query, p["name"] + " " + p["trigger"]), p) for p in pbs]
        scored = [x for x in scored if x[0] > 0]
        if scored: return max(scored, key=lambda x: x[0])[1]
    return None

def routine_for(chain_name=None, skill_id=None):
    m = load()
    if not m: return None
    for r in m["routines"]["routines"]:
        if chain_name and r["skill_chain"] == chain_name: return r
    for r in m["routines"]["routines"]:
        if skill_id and skill_id in r["skill_chain"]: return r
    return None

def role(query):
    m = load()
    if not m: return None
    q = _norm(query)
    for r in m["business_model"]["roles"]:
        if _norm(r["title"]) in q or q == _norm(r["code"]): return r
    scored = [(_score_words(q, r["title"] + " " + r["purpose"]), r) for r in m["business_model"]["roles"]]
    scored = [x for x in scored if x[0] > 0]
    return max(scored, key=lambda x: x[0])[1] if scored else None

def role_kpis(code):
    m = load(); return (m or {}).get("kpis", {}).get("role_kpis", {}).get(code)

def compensation_for(code, m=None):
    """CONFIDENTIAL — available only with the local overlay; never enters the core or any versioned artifact."""
    m = m or load(); ov = (m or {}).get("_overlay")
    if not ov: return {"status": "CONFIDENTIAL_UNAVAILABLE", "reason": "compensation lives in the sensitive overlay (absent)"}
    v = ov.get("compensation", {}).get("fix_salary_net_amd", {}).get(code)
    return {"status": "OK", "fix_salary_net_amd": v, "src": ov.get("compensation", {}).get("src", [])} if v is not None else {"status": "UNKNOWN"}

def gaps_for(text):
    m = load()
    if not m: return []
    return [g for g in m["gaps"]["gaps"] if _score_words(text, g["gap"] + " " + g["category"]) >= 2]

# ───────────────────────── change control: observations never touch the core ─────────────────────────
def _obs_path():
    import engine
    return pathlib.Path(engine.STATE_DIR) / "business_observations.jsonl"

def promotion_allowed(current, target, authority_level):
    """May a business fact move current → target, given the authority of what supports the move?"""
    m = load(); rules = (m or {}).get("targets", {}).get("promotion_rules") or {}
    order = PROMOTION_STATES
    if current not in order or target not in order: return False, "unknown state"
    if target == "SUPERSEDED": return authority_level in ("REFERENCE_APPROVED", "CHARTER", "HISTORICAL_MOVE"), "supersede requires an approved newer fact or archiving"
    if order.index(target) < order.index(current): return False, "no demotion without supersession"
    if order.index(target) - order.index(current) > 1: return False, "one step at a time (OBSERVATION → APPROVED directly is forbidden)"
    max_state = (rules.get("max_state_by_authority") or {}).get(authority_level)
    if max_state is None: return False, f"unknown authority {authority_level}"
    if order.index(target) > order.index(max_state): return False, f"authority {authority_level} may create at most {max_state}"
    return True, "allowed"

def record_observation(text, src=None, kind="OBSERVATION_FROM_CONVERSATION", subject=None):
    """New business knowledge from conversation is stored as an OBSERVATION in the state store — the core is never modified."""
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "state": "OBSERVATION", "kind": kind, "subject": subject, "text": str(text)[:600], "src": list(src or []),
           "model_version": (load() or {}).get("sources", {}).get("meta", {}).get("model_version"), "promotion": "requires Gev's confirmation → PROPOSED/CONFIRMED; the primitive's approver → APPROVED; never auto-promoted"}
    p = _obs_path(); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec

def observations(limit=50):
    p = _obs_path()
    if not p.exists(): return []
    lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(l) for l in lines if l.strip()]

# ───────────────────────── skill context ─────────────────────────
SKILL_TOPICS = {
 "sales_kpi_monitoring": "sales activations plan branch channel", "target_vs_actual": "sales plan target activations", "sales_forecasting": "sales forecast activations",
 "sales_funnel_analysis": "conversion leads funnel", "pipeline_management": "pipeline deals crm activation", "channel_performance_analysis": "channel d2d telesales branch",
 "lost_opportunity_analysis": "lost sale", "upsell_analysis": "upsell", "customer_acquisition_analysis": "acquisition leads new connections", "churn_analysis": "churn retention cancellations save list",
 "revenue_leakage_detection": "leakage billing accuracy collections", "campaign_performance_analysis": "marketing leads campaign", "pricing_performance_analysis": "tariff pricing",
 "operations_kpi_monitoring": "sla installation repair backlog", "workload_analysis": "capacity vacancies workload", "backlog_management": "backlog installation queue aging",
 "bottleneck_detection": "bottleneck installation handoff", "failure_rework_analysis": "repeat visits rework failed installation", "operational_incident_management": "incident outage uptime",
 "customer_complaint_pattern_analysis": "complaints", "operational_risk_detection": "operational risk sla", "performance_gap_diagnosis": "employee performance kpi bonus",
 "daily_briefing": "daily brief", "end_of_day_control": "end of day", "weekly_executive_review": "weekly review target actual", "executive_reporting": "report", "meeting_preparation": "meeting sales review",
 "decision_support": "decision approval", "escalation_management": "escalation", "waiting_for_tracking": "waiting for owner", "follow_up_management": "follow-up owner", "deadline_management": "deadline overdue tasks",
 "approval_management": "approval discount billing exception", "authority_checking": "approval pricing", "risk_classification": "tariff price salary contract",
}

def context_for(skill_id, intent="", inputs=None, chain_name=None):
    """Business context bundle injected into every governed execution (never raises)."""
    m = load()
    if not m: return {"available": False, "gaps": ["BUSINESS_CONTEXT_MISSING"], "reason": last_error(), "skill": skill_id, "model": None}
    text = " ".join([_norm(intent), _norm(SKILL_TOPICS.get(skill_id, "")), _norm(json.dumps({k: v for k, v in (inputs or {}).items() if isinstance(v, str)}, ensure_ascii=False))])
    qtext = " ".join([_norm(intent) if not re.match(r"^run \w+$", _norm(intent)) else "", _norm(" ".join(v for k, v in (inputs or {}).items() if isinstance(v, str) and k in ("query", "intent", "text", "issue", "description", "item", "meeting", "topic")))]).strip()
    pb = playbook_for(chain_name, qtext or SKILL_TOPICS.get(skill_id, ""))
    kpis = (find_kpis(qtext) if qtext else []) or find_kpis(text)
    procs = find_processes(qtext or SKILL_TOPICS.get(skill_id, "")) or find_processes(SKILL_TOPICS.get(skill_id, ""))
    own = find_owner(qtext or SKILL_TOPICS.get(skill_id, "")); rt = routine_for(chain_name, skill_id)
    st = model_state(m); gaps, rules = [], []
    if st["state"] == "SOURCE_MISSING": gaps.append("SOURCE_MISSING")
    if st["state"] == "STALE_MODEL": gaps.append("STALE_MODEL")
    if st["state"] == "UNCERTIFIED": gaps.append("BUSINESS_CONTEXT_MISSING")
    if own.get("code"): gaps.append(own["code"])
    if not kpis and skill_id in SKILL_TOPICS and any(w in text for w in ("kpi", "target", "plan", "sales", "churn", "backlog", "sla")): gaps.append("KPI_DEFINITION_MISSING")
    if kpis and all(str(k.get("target")) == "UNKNOWN" for k in kpis): gaps.append("TARGET_UNKNOWN")
    if any(p["status"].startswith("GAP") for p in procs) or (not procs and skill_id in ("process_mapping", "failure_rework_analysis", "bottleneck_detection")): gaps.append("PROCESS_UNDEFINED")
    if skill_id in ("approval_management", "authority_checking", "decision_support") and any(w in text for w in ("discount", "correction", "write-off", "reactivation", "billing exception", "զեղչ")): gaps.append("APPROVAL_RULE_UNKNOWN")
    conflicts = [c for c in m["business_model"]["conflicts"] if _score_words(text, c["topic"]) >= 1]
    if conflicts: gaps.append("SOURCE_CONFLICT")
    srcs = sorted(set(sum([k["src"] for k in kpis], []) + sum([p["src"] for p in procs], []) + (pb["src"] if pb else []) + own.get("src", [])))
    stale = stale_sources_for(srcs, m)
    if stale["changed"] and "STALE_MODEL" not in gaps: gaps.append("SOURCE_CHANGED")
    if pb: rules.append(f"playbook {pb['playbook_id']}: authority — {pb['authority_boundary']}; escalate when — {pb['escalation_threshold']}")
    rules.append("sale = ACTIVATED deal only (S01); targets/thresholds only from targets.json (APPROVED vs PROPOSED); unknown stays UNKNOWN; people resolved only via CONFIRMED assignments")
    owner = {k: own.get(k) for k in ("status", "owner_role", "conf", "code") if own.get(k) is not None}
    if own.get("resolution"): owner.update(person_status=own["resolution"].get("person_status"), person=own["resolution"].get("person"))
    return {"available": True, "skill": skill_id, "chain": chain_name, "playbook": pb["playbook_id"] if pb else None, "playbook_name": pb["name"] if pb else None,
            "diagnostic_steps": pb["diagnostic_steps"] if pb else [], "questions": pb["questions_to_answer"] if pb else [], "required_data": pb["required_data"] if pb else [],
            "kpis": [{"id": k["kpi_id"], "name": k["name"], "kind": k["kind"], "owner": k["owner"], "target": k["target"], "target_ref": k.get("target_ref"), "proposed_targets": [t["id"] for t in k.get("proposed_targets", [])], "source": k["source"], "conf": k["conf"]} for k in kpis],
            "processes": [{"id": p["process_id"], "name": p["name"], "owner": p["accountable_owner"], "status": p["status"]} for p in procs],
            "owner": owner, "routine": rt["routine_id"] if rt else None, "routine_sections": rt["sections"] if rt else [], "routine_missing_data": rt["data_missing"] if rt else [],
            "conflicts": [{"id": c["id"], "topic": c["topic"], "resolution_required": c["resolution_required"]} for c in conflicts],
            "sources": srcs, "stale_sources": stale, "rules": rules, "gaps": sorted(set(gaps)), "output_format": m["playbooks"]["executive_format"], "model": model_id(m)}

def summary(ctx):
    if not ctx or not ctx.get("available"): return {"available": False, "gaps": (ctx or {}).get("gaps", ["BUSINESS_CONTEXT_MISSING"]), "reason": (ctx or {}).get("reason"), "model": None}
    return {"available": True, "playbook": ctx.get("playbook"), "kpis": [k["id"] for k in ctx.get("kpis", [])], "processes": [p["id"] for p in ctx.get("processes", [])],
            "owner": ctx.get("owner"), "routine": ctx.get("routine"), "sources": ctx.get("sources"), "stale_sources": ctx.get("stale_sources"), "conflicts": [c["id"] for c in ctx.get("conflicts", [])], "gaps": ctx.get("gaps", []),
            "required_data": ctx.get("required_data", []), "rules": ctx.get("rules", []), "model": ctx.get("model")}
