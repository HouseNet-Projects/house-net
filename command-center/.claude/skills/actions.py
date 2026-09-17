# -*- coding: utf-8 -*-
"""ACTION RUNTIME — Deputy's CONTROLLED HANDS (Mission 4.2). The ONE governed path for every real mutation.

    INTENT → UNDERSTAND → RESOLVE BUSINESS CONTEXT → RESOLVE SKILL → BUILD ACTION REQUEST → CHECK PRECONDITIONS → CHECK CAPABILITY →
    CHECK AUTHORITY → PREPARE EXACT ACTION → REQUEST GEV APPROVAL → VALIDATE APPROVAL BINDING → EXECUTE → VERIFY POSTCONDITION →
    RECONCILE → UPDATE MEMORY / OPEN LOOP → AUDIT → REPORT

LAW (.claude/policy/approval_rule.json): AUTONOMOUS EXTERNAL WRITE AUTHORITY = NONE. No approval → no execution. Approval is a
single-use token bound to the action FINGERPRINT (system, operation, object, recipient/owner, content, dates, participants,
amounts, scope, attachments, parameters, expected effect); any material change invalidates it. Provider success ≠ completion:
only an independent read-back produces VERIFIED. Timeout/unknown provider outcome → RESULT_UNKNOWN → RECONCILE FIRST, never a
blind retry. State lives in the hardened store (table `actions`, durable-exported), so idempotency survives restarts.
Providers (write adapters) are the only thing that touches an external system; they are reached ONLY through execute()."""
import sys, os, json, re, hashlib, uuid, datetime, pathlib, importlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "integrations")); sys.path.insert(0, str(HERE.parent / "policy"))

STATES = ("PREPARED", "APPROVAL_REQUIRED", "APPROVED", "EXECUTING", "EXECUTED_UNVERIFIED", "VERIFIED", "FAILED", "DENIED", "REJECTED", "RESULT_UNKNOWN", "PARTIAL")
RISK = {"R0": "local technical / non-business mutation", "R1": "low-impact business write", "R2": "material business write", "R3": "high-impact / sensitive write"}
RISK_LEVEL = {"R0": "EXECUTE_REVERSIBLE", "R1": "EXECUTE_EXTERNAL", "R2": "EXECUTE_EXTERNAL", "R3": "EXECUTE_MATERIAL"}
TOKEN_TTL_HOURS = 24
MATERIAL_KEYS = ("target_system", "target_operation", "target_object_type", "target_object_id", "parameters", "expected_effect", "authority_scope")
APPROVAL_RX = re.compile(r"^\s*(ok(ay)?|go|yes|approved?|do it|execute|confirm(ed)?|արա|արեք|այո|օք|օկ|գո|գօ|հաստատում եմ|հաստատեցի|կատարիր|go ahead|ok go|go ok)\s*[.!]*\s*$", re.I)   # օք/օկ/գո/գօ = Armenian-letter OK/GO (Gev, 2026-09-12)
MODIFIER_RX = re.compile(r"\b(but|except|instead|however|only if|change|բայց|փոխիր|փոխի|սակայն)\b", re.I)
REJECT_RX = re.compile(r"^\s*(no|nope|reject(ed)?|don't|do not|ոչ|չէ|մի արա)\b|^\s*(cancel|stop|չեղարկիր|չեղարկի)\s*(it|that|this|the action|էդ|դա)?\s*[.!]*$", re.I)   # 'cancel'/'stop' reject only standalone — "cancel tomorrow's meeting" is an ACTION to prepare

class ActionError(Exception):
    def __init__(self, code, reason): super().__init__(f"{code}: {reason}"); self.code, self.reason = code, reason
class ProviderError(Exception):
    """Provider clearly failed and nothing was written (safe to report FAILED)."""
class ProviderUnknown(Exception):
    """Timeout / ambiguous provider response: the mutation MAY have happened (→ RESULT_UNKNOWN, reconcile first)."""

def _now(): return datetime.datetime.now().isoformat(timespec="seconds")
def _norm(v):
    if isinstance(v, dict): return {k: _norm(v[k]) for k in sorted(v) if not str(k).startswith("_")}
    if isinstance(v, (list, tuple)): return [_norm(x) for x in v]
    if isinstance(v, str): return " ".join(v.split())
    return v
def _canon(obj): return json.dumps(_norm(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
def _store():
    import engine; return engine._store()
def _audit(rec, required=True):
    """Governed audit through the hardened core store; a required audit that cannot be persisted fails the action closed."""
    import engine
    try:
        aid = hashlib.sha256((_now() + uuid.uuid4().hex).encode()).hexdigest()[:16]
        out = engine.audit({"audit_id": aid, "skill_id": "<action_runtime>", **rec})
        if not out or not engine._store().get("audit", aid): raise RuntimeError("audit not re-readable")
        return aid
    except Exception as e:
        if required: raise ActionError("AUDIT_UNAVAILABLE", f"governed audit could not be persisted — action withheld ({type(e).__name__})")
        return None

# ───────────────────────── capability / provider resolution ─────────────────────────
PROVIDER_OVERRIDES = {}          # integration_id → provider object (tests/evals inject fakes; production resolves adapters)

def capability(iid, op):
    import capabilities; return capabilities.capability(iid, op)

def provider(iid):
    if iid in PROVIDER_OVERRIDES: return PROVIDER_OVERRIDES[iid]
    fx = os.environ.get("COMMAND_CENTER_ACTIONS_FIXTURE")
    if fx:
        data = json.loads(pathlib.Path(fx).read_text(encoding="utf-8")) if pathlib.Path(fx).exists() else {}
        if iid in data: return FakeProvider(data[iid])
    import capabilities
    spec = capabilities.write_spec(iid)
    if not spec or not spec.get("adapter"): raise ActionError("CAPABILITY_UNAVAILABLE", f"{iid} has no write adapter")
    return importlib.import_module(spec["adapter"])

class FakeProvider:
    """Programmable provider for tests/evals: behaviour per op = ok | error | timeout | success_no_evidence | wrong_value; keeps an in-memory 'remote'."""
    def __init__(self, behaviour=None):
        self.behaviour = dict(behaviour or {}); self.remote = {}; self.calls = []; self.crash_after_write = set()
    def _b(self, op): return self.behaviour.get(op, {}) if isinstance(self.behaviour.get(op, {}), dict) else {"result": self.behaviour.get(op)}
    def precondition(self, op, params):
        oid = params.get("target_object_id")
        return {"exists": oid in self.remote, "object": self.remote.get(oid)} if oid else {"exists": False, "object": None}
    def find_existing(self, op, params):
        for oid, o in self.remote.items():
            if o.get("op") == op and o.get("key") == params.get("_idem_key"): return {"id": oid, **o}
        return None
    def execute(self, op, params):
        self.calls.append((op, dict(params))); b = self._b(op); r = b.get("result", "ok")
        if r == "error": raise ProviderError(b.get("reason", "provider refused"))
        if r == "timeout":
            if b.get("committed"): self.remote[b.get("id", "obj-" + uuid.uuid4().hex[:6])] = {"op": op, "key": params.get("_idem_key"), **params}
            raise ProviderUnknown("provider timed out")
        oid = params.get("target_object_id") or b.get("id") or "obj-" + uuid.uuid4().hex[:6]
        if r == "success_no_evidence": return {"ok": True, "id": oid, "note": "provider said success but wrote nothing"}
        obj = {"op": op, "key": params.get("_idem_key"), **params}
        if r == "wrong_value": obj = {**obj, **b.get("wrong", {"owner": "SOMEONE ELSE"})}
        self.remote[oid] = obj
        if op in self.crash_after_write: raise ProviderUnknown("process crashed after remote success")
        return {"ok": True, "id": oid}
    def verify(self, op, params, result):
        oid = (result or {}).get("id"); obj = self.remote.get(oid)
        if not obj: return {"verified": False, "reason": "object not found on read-back", "evidence": None}
        diffs = {k: (params[k], obj.get(k)) for k in params if not k.startswith("_") and k != "target_object_id" and obj.get(k) != params[k]}
        return {"verified": not diffs, "reason": ("field mismatch: " + ", ".join(diffs)) if diffs else "read-back matches", "evidence": {"id": oid, **{k: obj.get(k) for k in obj if k != "key"}}}

# ───────────────────────── action request / fingerprint / idempotency ─────────────────────────
def build_request(*, skill_id, business_intent, business_domain, target_system, target_operation, target_object_type, parameters, expected_effect,
                  expected_postcondition, verification_method=None, target_object_id=None, requested_by="Gev", source_context=None, business_context=None, correlation_id=None):
    cap = capability(target_system, target_operation)
    req = {"action_id": "ACT-" + uuid.uuid4().hex[:10], "operation_id": f"{target_system}:{target_operation}", "correlation_id": correlation_id or uuid.uuid4().hex[:12],
           "requested_by": requested_by, "requested_at": _now(), "skill_id": skill_id, "business_intent": business_intent, "business_domain": business_domain,
           "target_system": target_system, "target_operation": target_operation, "target_object_type": target_object_type, "target_object_id": target_object_id,
           "parameters": _norm(parameters), "authority_scope": cap.get("authority_required", "EXECUTE_EXTERNAL"), "risk_class": cap.get("risk_class", "R2"),
           "expected_effect": expected_effect, "expected_postcondition": expected_postcondition, "verification_method": verification_method or cap.get("verification_method", "read-back"),
           "source_context": source_context or {}, "business_context": business_context or {}, "approval_required": True, "approval_token": None,
           "idempotency_method": cap.get("idempotency_method", "stable key on intended business action")}
    req["idempotency_key"] = idempotency_key(req); req["action_fingerprint"] = fingerprint(req)
    return req

def fingerprint(req):
    """Deterministic binding of approval to the MATERIAL action (system, operation, object, parameters incl. recipient/owner/content/dates/participants/amount/attachments, effect, scope)."""
    return hashlib.sha256(_canon({k: req.get(k) for k in MATERIAL_KEYS}).encode("utf-8")).hexdigest()[:32]

IDEM_IGNORE = {"note", "comment", "reason", "evidence", "body_preview", "_idem_key"}
def idempotency_key(req):
    p = {k: v for k, v in (req.get("parameters") or {}).items() if k not in IDEM_IGNORE}
    return hashlib.sha256(_canon({"s": req["target_system"], "o": req["target_operation"], "t": req["target_object_type"], "id": req.get("target_object_id"), "p": p}).encode("utf-8")).hexdigest()[:24]

# ───────────────────────── human presentation ─────────────────────────
def render_card(req, precondition=None, diff=None, batch=None):
    p = req["parameters"]; lines = ["**READY FOR YOUR APPROVAL**", ""]
    if batch: lines.append(f"Batch {batch['batch_id']} — step {batch['index']}/{batch['size']}"); lines.append("")
    lines += [f"WHAT: {req['target_operation']} — {req['business_intent']}", f"WHERE: {req['target_system']} ({capability(req['target_system'], req['target_operation']).get('system', req['target_system'])})",
              f"TARGET: {req['target_object_type']}" + (f" {req['target_object_id']}" if req.get("target_object_id") else " (new)")]
    lines.append("IMPORTANT PARAMETERS:")
    for k, v in p.items():
        if k.startswith("_"): continue
        lines.append(f"  · {k}: {v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False)}")
    if diff: lines.append("CHANGE (current → proposed):"); lines += [f"  · {k}: {a} → {b}" for k, (a, b) in diff.items()]
    lines += [f"RISK: {req['risk_class']} ({RISK[req['risk_class']]}) · authority {req['authority_scope']}", f"EXPECTED EFFECT: {req['expected_effect']}", f"VERIFY AFTER EXECUTION: {req['verification_method']} — {req['expected_postcondition']}", "", "**Nothing has been changed yet.**", "", "Approve?"]
    return "\n".join(lines)

# ───────────────────────── persistence helpers ─────────────────────────
def _save(a):
    _store().upsert("actions", a["action_id"], a, extra_cols={"status": a["state"], "fingerprint": a["request"]["action_fingerprint"], "idempotency_key": a["request"]["idempotency_key"], "session_id": a.get("session_id") or "", "batch_id": a.get("batch_id") or ""})
    return a
def get(action_id): return _store().get("actions", action_id)
def list_actions(where="", args=()): return _store().list("actions", where=where, args=args)
def pending(session_id=None):
    rows = list_actions("status='APPROVAL_REQUIRED'")
    return [a for a in rows if not session_id or a.get("session_id") in (session_id, "", None)]
def _same_key_active(req, exclude=None):
    return [a for a in list_actions("idempotency_key=?", (req["idempotency_key"],)) if a["action_id"] != exclude and a["state"] in ("APPROVED", "EXECUTING", "EXECUTED_UNVERIFIED", "VERIFIED", "RESULT_UNKNOWN")]

# ───────────────────────── PREPARE ─────────────────────────
def prepare(req, *, session_id=None, ticket_id=None, batch=None, reg=None):
    """PREPARE EXACT ACTION → APPROVAL_REQUIRED (or DENIED with a structured code). Never touches the provider except for a read of the precondition."""
    import engine
    a = {"action_id": req["action_id"], "request": req, "state": "PREPARED", "session_id": session_id or "", "ticket_id": ticket_id, "batch_id": (batch or {}).get("batch_id"), "history": [{"at": _now(), "state": "PREPARED"}],
         "approval": None, "execution": None, "verification": None, "reconciliation": None, "memory": None, "codes": []}
    cap = capability(req["target_system"], req["target_operation"]); a["capability"] = {k: cap.get(k) for k in ("level", "implemented", "configured", "connected", "runtime_available", "risk_class", "gev_approval_required", "machine_dependency", "certification_status")}
    def deny(code, reason):
        a["state"] = "DENIED"; a["codes"].append(code); a["history"].append({"at": _now(), "state": "DENIED", "code": code, "reason": reason}); a["reason"] = reason
        _audit({"execution_id": req["action_id"], "ticket_id": ticket_id, "result_status": "DENIED", "code": code, "reason": reason, "action": _summary(req)}, required=False); return _save(a)
    # HARD SCOPE LOCK: a system Gev did not ask about in THIS task is not proposed at all (workspace_policy.json -> scope_lock)
    ok_scope, why_scope = engine.scope_allows_system(engine.get_ticket(ticket_id) if ticket_id else None, req["target_system"])
    if not ok_scope: return deny("OUT_OF_SCOPE", f"{why_scope} — Gev did not ask for this in the current task; nothing prepared")
    if not cap.get("implemented"): return deny("CAPABILITY_UNAVAILABLE", f"{req['target_system']} {req['target_operation']}: {cap.get('level')} — {cap.get('note') or 'no write adapter'}")
    if cap.get("level") == "UNAVAILABLE" or not cap.get("configured"): return deny("NOT_CONFIGURED" if not cap.get("configured") else "CAPABILITY_UNAVAILABLE", f"{req['target_system']} is {cap.get('level')}: {cap.get('note') or cap.get('unblock') or 'not configured/connected'}")
    reg = reg or engine.load_registry(); skill = reg["_index"].get("action_runtime") or {"authority_boundary": {"max_action": "EXECUTE_MATERIAL"}}
    auth = engine.authority_check(reg, skill, req["authority_scope"], None)
    if not auth["ok"] and auth.get("code") != "APPROVAL_REQUIRED": return deny("AUTHORITY_EXCEEDED", auth["reason"])
    dup = _same_key_active(req)
    if dup:
        d = dup[0]; return deny("DUPLICATE", f"the same business action already exists as {d['action_id']} ({d['state']}) — reconcile/inspect it instead of creating a second one")
    try:
        prov = provider(req["target_system"]); pre = prov.precondition(req["target_operation"], dict(req["parameters"], target_object_id=req.get("target_object_id")))
        existing = prov.find_existing(req["target_operation"], dict(req["parameters"], _idem_key=req["idempotency_key"], target_object_id=req.get("target_object_id")))
    except ActionError as e: return deny(e.code, e.reason)
    except Exception as e: return deny("PRECONDITION_UNREADABLE", f"could not read the current state before proposing: {type(e).__name__}: {e}")
    if existing: return deny("ALREADY_EXISTS", f"the intended postcondition already exists ({existing.get('id')}) — nothing to do; no duplicate proposed")
    if req.get("target_object_id") and not pre.get("exists"): return deny("TARGET_NOT_FOUND", f"{req['target_object_type']} {req['target_object_id']} does not exist in {req['target_system']}")
    a["precondition"] = pre; a["diff"] = _diff(pre.get("object") or {}, req["parameters"]) if pre.get("object") else None
    a["card"] = render_card(req, pre, a["diff"], batch); a["state"] = "APPROVAL_REQUIRED"; a["history"].append({"at": _now(), "state": "APPROVAL_REQUIRED"})
    _audit({"execution_id": req["action_id"], "ticket_id": ticket_id, "result_status": "APPROVAL_REQUIRED", "action": _summary(req), "fingerprint": req["action_fingerprint"], "idempotency_key": req["idempotency_key"], "capability": a["capability"], "authority": auth, "card_sha": hashlib.sha256(a["card"].encode()).hexdigest()[:16]})
    return _save(a)

def _diff(current, proposed):
    d = {}
    for k, v in proposed.items():
        if k.startswith("_"): continue
        if k in current and current.get(k) != v: d[k] = (current.get(k), v)
    return d
def _summary(req): return {k: req.get(k) for k in ("action_id", "target_system", "target_operation", "target_object_type", "target_object_id", "risk_class", "authority_scope", "expected_effect")}

# ───────────────────────── APPROVAL ─────────────────────────
def classify_approval(text):
    """'APPROVAL' | 'REJECTION' | 'MODIFIED' (affirmative + change) | 'AMBIGUOUS'. Ambiguity fails closed."""
    t = (text or "").strip()
    if not t: return "AMBIGUOUS"
    if REJECT_RX.match(t): return "REJECTION"
    if APPROVAL_RX.match(t): return "APPROVAL"
    if re.match(r"^\s*(ok(ay)?|go|yes|արա|այո|օք|օկ|գո|գօ|հաստատում եմ)\b", t, re.I) and MODIFIER_RX.search(t): return "MODIFIED"
    return "AMBIGUOUS"

def approve(text, *, action_id=None, batch_id=None, session_id=None, by="Gev", ticket_id=None):
    """VALIDATE APPROVAL: unmistakable text, bound to ONE pending action (or one enumerated batch), token single-use, TTL. Never executes."""
    kind = classify_approval(text)
    if kind != "APPROVAL":
        _audit({"execution_id": action_id or batch_id or "?", "ticket_id": ticket_id, "result_status": "NOT_APPROVED", "kind": kind, "text": (text or "")[:120]}, required=False)
        return {"status": "NOT_APPROVED", "kind": kind, "reason": {"REJECTION": "Gev rejected — nothing executed", "MODIFIED": "affirmative with a change — the pending proposal is not what was approved; a changed action must be re-prepared and approved unambiguously", "AMBIGUOUS": "not an unmistakable approval of the pending action — nothing executed"}[kind]}
    if batch_id: targets = [a for a in list_actions("batch_id=?", (batch_id,)) if a["state"] == "APPROVAL_REQUIRED"]
    elif action_id: targets = [a for a in [get(action_id)] if a and a["state"] == "APPROVAL_REQUIRED"]
    else:
        p = pending(session_id); batches = {a.get("batch_id") for a in p if a.get("batch_id")}; singles = [a for a in p if not a.get("batch_id")]
        if len(batches) + len(singles) != 1:
            return {"status": "NOT_APPROVED", "kind": "AMBIGUOUS", "reason": f"approval target ambiguous: {len(singles)} pending action(s) and {len(batches)} pending batch(es) — name the action/batch"}
        targets = [a for a in p if a.get("batch_id") in batches] if batches else singles
    if not targets: return {"status": "NOT_APPROVED", "kind": "NO_PENDING", "reason": "no pending action awaits approval"}
    tokens = []
    for a in targets:
        req = a["request"]
        if fingerprint(req) != req["action_fingerprint"]: return {"status": "NOT_APPROVED", "kind": "TAMPERED", "reason": f"{a['action_id']}: stored action no longer matches its fingerprint"}
        tok = {"token_id": "APR-" + uuid.uuid4().hex[:12], "action_id": a["action_id"], "action_fingerprint": req["action_fingerprint"], "target": req["operation_id"], "target_object_id": req.get("target_object_id"),
               "approved_by": by, "approved_at": _now(), "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=TOKEN_TTL_HOURS)).isoformat(timespec="seconds"), "approval_text": text.strip()[:80],
               "batch_id": a.get("batch_id"), "consumed": False, "consumed_at": None}
        a["approval"] = tok; a["state"] = "APPROVED"; a["history"].append({"at": _now(), "state": "APPROVED", "token": tok["token_id"]}); _save(a); tokens.append(tok)
        _audit({"execution_id": a["action_id"], "ticket_id": ticket_id, "result_status": "APPROVED", "token": tok["token_id"], "fingerprint": req["action_fingerprint"], "approved_by": by, "approval_text": tok["approval_text"], "batch_id": a.get("batch_id")})
    return {"status": "APPROVED", "kind": "APPROVAL", "tokens": tokens, "action_ids": [a["action_id"] for a in targets], "batch_id": targets[0].get("batch_id")}

def reject(action_id, reason="rejected by Gev", ticket_id=None):
    a = get(action_id)
    if not a: raise ActionError("NOT_FOUND", action_id)
    a["state"] = "REJECTED"; a["history"].append({"at": _now(), "state": "REJECTED", "reason": reason}); _save(a)
    _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": "REJECTED", "reason": reason}, required=False); return a

def invalidate_if_changed(action_id, new_parameters):
    """A material change to a pending/approved action invalidates its approval: the old action is REJECTED (code CHANGED) and a new request must be prepared."""
    a = get(action_id); req = dict(a["request"]); req["parameters"] = _norm({**req["parameters"], **new_parameters})
    if fingerprint(req) == a["request"]["action_fingerprint"]: return {"changed": False, "action": a}
    a["state"] = "REJECTED"; a["codes"].append("CHANGED"); a["history"].append({"at": _now(), "state": "REJECTED", "code": "CHANGED", "reason": "material parameters changed after presentation — approval invalidated"}); _save(a)
    _audit({"execution_id": action_id, "result_status": "REJECTED", "code": "CHANGED", "old_fingerprint": a["request"]["action_fingerprint"], "new_fingerprint": fingerprint(req)}, required=False)
    return {"changed": True, "action": a, "new_request": {**req, "action_id": "ACT-" + uuid.uuid4().hex[:10], "requested_at": _now(), "idempotency_key": idempotency_key(req), "action_fingerprint": fingerprint(req), "approval_token": None}}

# ───────────────────────── EXECUTE / VERIFY / RECONCILE ─────────────────────────
def _token_valid(a, token_id=None):
    tok = a.get("approval")
    if not tok: return False, "APPROVAL_REQUIRED", "no approval token on this action"
    if token_id and tok["token_id"] != token_id: return False, "APPROVAL_MISMATCH", "token does not belong to this action"
    if tok.get("consumed"): return False, "APPROVAL_CONSUMED", f"token {tok['token_id']} already consumed at {tok.get('consumed_at')} — no replay"
    if tok["expires_at"] < _now(): return False, "APPROVAL_EXPIRED", f"token expired at {tok['expires_at']}"
    if tok["action_fingerprint"] != fingerprint(a["request"]) or tok["action_fingerprint"] != a["request"]["action_fingerprint"]: return False, "APPROVAL_MISMATCH", "approval is bound to a different action fingerprint"
    return True, None, None

def execute(action_id, *, token_id=None, ticket_id=None, retry=False):
    """EXECUTE only an APPROVED action whose token binds to its exact fingerprint; persist EXECUTING before the provider call (crash safety);
    unknown outcome → RESULT_UNKNOWN + reconcile; success → independent verification → VERIFIED (never on provider say-so)."""
    import engine, health
    with health.locked(health.state_dir() / "actions.lock"):                # one executor at a time per store: check-then-EXECUTING is atomic
        return _execute_locked(action_id, token_id=token_id, ticket_id=ticket_id, retry=retry)

def _execute_locked(action_id, *, token_id=None, ticket_id=None, retry=False):
    import engine
    a = get(action_id)
    if not a: raise ActionError("NOT_FOUND", action_id)
    req = a["request"]
    def fail(state, code, reason, **extra):
        a["state"] = state; a["codes"].append(code); a["reason"] = reason; a["history"].append({"at": _now(), "state": state, "code": code, "reason": reason}); a.update(extra); _save(a)
        _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": state, "code": code, "reason": reason, "action": _summary(req)}, required=False); return report(a)
    if a["state"] == "VERIFIED": return report(a)                                            # idempotent: already done, no second write
    if a["state"] == "RESULT_UNKNOWN" and not retry: return fail("RESULT_UNKNOWN", "RECONCILE_FIRST", "outcome unknown — reconcile before any retry")
    if a["state"] not in ("APPROVED", "RESULT_UNKNOWN"): return fail("DENIED" if a["state"] in ("PREPARED", "APPROVAL_REQUIRED", "DENIED", "REJECTED") else a["state"], "NOT_APPROVED", f"action is {a['state']} — NO GEV APPROVAL = DO NOT EXECUTE")
    ok, code, why = _token_valid(a, token_id)
    if not ok: return fail("REJECTED" if code in ("APPROVAL_MISMATCH", "APPROVAL_EXPIRED") else "DENIED", code, why)
    reg = engine.load_registry(); skill = reg["_index"].get("action_runtime") or {"authority_boundary": {"max_action": "EXECUTE_MATERIAL"}}
    auth = engine.authority_check(reg, skill, req["authority_scope"], a["approval"]["token_id"])
    if not auth["ok"]: return fail("DENIED", auth.get("code", "AUTHORITY_EXCEEDED"), auth["reason"])
    dups = _same_key_active(req, exclude=action_id)
    if dups: return fail("DENIED", "DUPLICATE", f"an equivalent action is already {dups[0]['state']} ({dups[0]['action_id']}) — no duplicate write")
    try: prov = provider(req["target_system"])
    except ActionError as e: return fail("FAILED", e.code, e.reason)
    params = dict(req["parameters"], _idem_key=req["idempotency_key"], target_object_id=req.get("target_object_id"))
    # stale-state protection: re-read the precondition immediately before mutating
    try: now_pre = prov.precondition(req["target_operation"], params)
    except Exception as e: return fail("FAILED", "PRECONDITION_UNREADABLE", f"{type(e).__name__}: {e}")
    if a.get("precondition") is not None and _norm(now_pre.get("object")) != _norm((a["precondition"] or {}).get("object")):
        return fail("REJECTED", "STALE_CONFLICT", "the target changed since the proposal was shown — approval invalidated; a new decision is required", stale={"proposed_on": a["precondition"], "now": now_pre})
    # AUDIT FIRST (fail closed): a material action without durable audit evidence is not executed
    try: _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": "EXECUTING", "action": _summary(req), "token": a["approval"]["token_id"], "fingerprint": req["action_fingerprint"], "attempt": len([h for h in a["history"] if h["state"] == "EXECUTING"]) + 1})
    except ActionError as e: return fail("DENIED", e.code, e.reason)
    a["state"] = "EXECUTING"; a["history"].append({"at": _now(), "state": "EXECUTING"}); _save(a)
    try:
        res = prov.execute(req["target_operation"], params)
    except ProviderUnknown as e:
        a["execution"] = {"at": _now(), "outcome": "UNKNOWN", "detail": str(e)[:200]}
        a["state"] = "RESULT_UNKNOWN"; a["codes"].append("RESULT_UNKNOWN"); a["history"].append({"at": _now(), "state": "RESULT_UNKNOWN", "reason": str(e)[:200]}); _save(a)
        _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": "RESULT_UNKNOWN", "reason": str(e)[:200]}, required=False)
        return reconcile(action_id, ticket_id=ticket_id)
    except ProviderError as e:
        return fail("FAILED", "PROVIDER_ERROR", str(e)[:200], execution={"at": _now(), "outcome": "FAILED", "detail": str(e)[:200]})
    except Exception as e:
        return fail("FAILED", "PROVIDER_EXCEPTION", f"{type(e).__name__}: {e}"[:200], execution={"at": _now(), "outcome": "FAILED"})
    a["execution"] = {"at": _now(), "outcome": "SUBMITTED", "provider_result": {k: v for k, v in (res or {}).items() if k not in ("raw",)}}
    a["state"] = "EXECUTED_UNVERIFIED"; a["history"].append({"at": _now(), "state": "EXECUTED_UNVERIFIED"}); a["approval"]["consumed"] = True; a["approval"]["consumed_at"] = _now(); _save(a)
    _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": "EXECUTED_UNVERIFIED", "provider_result": a["execution"]["provider_result"], "token_consumed": a["approval"]["token_id"]}, required=False)
    return _verify(a, prov, ticket_id)

def _verify(a, prov, ticket_id=None):
    req = a["request"]; params = dict(req["parameters"], _idem_key=req["idempotency_key"], target_object_id=req.get("target_object_id"))
    try: v = prov.verify(req["target_operation"], params, (a.get("execution") or {}).get("provider_result") or a.get("reconciliation", {}).get("evidence") or {})
    except Exception as e: v = {"verified": False, "reason": f"verification error {type(e).__name__}: {e}", "evidence": None}
    a["verification"] = {"at": _now(), **v}
    if v.get("verified"):
        a["state"] = "VERIFIED"; a["history"].append({"at": _now(), "state": "VERIFIED"}); a["memory"] = _update_memory(a); _save(a)
        _audit({"execution_id": a["action_id"], "ticket_id": ticket_id, "result_status": "VERIFIED", "evidence": v.get("evidence"), "memory": a["memory"]}, required=False)
        if (req.get("source_context") or {}).get("certification"):          # Gev-approved live certification write → durable VERIFIED_WRITE evidence (never inferred from tests)
            try:
                from capabilities import record_write_certification
                ev = {**(v.get("evidence") or {}), "approved_by": (a.get("approval") or {}).get("approved_by"), "approval_token": (a.get("approval") or {}).get("token_id"), "approved_at": (a.get("approval") or {}).get("approved_at"),
                      "fingerprint": req.get("action_fingerprint"), "ticket_id": ticket_id, "read_back": v.get("reason")}      # the durable certification carries the whole evidence chain, not only the read-back
                a["certification"] = record_write_certification(req["target_system"], req["target_operation"], a["action_id"], ev); _save(a)
            except Exception as e:
                a["codes"].append("CERTIFICATION_NOT_RECORDED"); a["history"].append({"at": _now(), "state": "VERIFIED", "code": "CERTIFICATION_NOT_RECORDED", "reason": str(e)[:200]}); _save(a)
    else:
        # honest sub-states of "not independently verified": no read-back exists (Telegram bot message) · provider evidence pending (WhatsApp status) · read-back contradicts
        code = "NO_INDEPENDENT_READBACK" if v.get("independent") is False else ("AWAITING_PROVIDER_STATUS" if v.get("pending") else "VERIFICATION_MISMATCH")
        a["state"] = "EXECUTED_UNVERIFIED"; a["codes"].append(code); a["history"].append({"at": _now(), "state": "EXECUTED_UNVERIFIED", "code": code, "reason": v.get("reason")}); _save(a)
        _audit({"execution_id": a["action_id"], "ticket_id": ticket_id, "result_status": "VERIFICATION_FAILED" if code == "VERIFICATION_MISMATCH" else code, "reason": v.get("reason")}, required=False)
    return report(a)

def reconcile(action_id, *, ticket_id=None):
    """RESULT_UNKNOWN → read the external state. Postcondition present → VERIFIED (no second write). Clearly absent → stays RESULT_UNKNOWN with retry_safe=True
    (a retry needs execute(..., retry=True) under the still-valid token). Undeterminable → RESULT_UNKNOWN, retry prohibited."""
    a = get(action_id); req = a["request"]
    try: prov = provider(req["target_system"]); found = prov.find_existing(req["target_operation"], dict(req["parameters"], _idem_key=req["idempotency_key"], target_object_id=req.get("target_object_id")))
    except Exception as e:
        a["reconciliation"] = {"at": _now(), "outcome": "UNDETERMINED", "reason": f"{type(e).__name__}: {e}", "retry_safe": False}; _save(a); return report(a)
    if found:
        a["reconciliation"] = {"at": _now(), "outcome": "FOUND", "evidence": found, "retry_safe": False}; a["execution"] = {**(a.get("execution") or {}), "provider_result": {"id": found.get("id")}}
        a["approval"]["consumed"] = True; a["approval"]["consumed_at"] = _now(); _save(a)
        _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": "RECONCILED_FOUND", "evidence": {"id": found.get("id")}}, required=False)
        return _verify(a, prov, ticket_id)
    ok, code, why = _token_valid(a)
    a["reconciliation"] = {"at": _now(), "outcome": "ABSENT", "retry_safe": bool(ok) and capability(req["target_system"], req["target_operation"]).get("retry_safe_when_absent", True), "reason": None if ok else why}; _save(a)
    _audit({"execution_id": action_id, "ticket_id": ticket_id, "result_status": "RECONCILED_ABSENT", "retry_safe": a["reconciliation"]["retry_safe"]}, required=False)
    return report(a)

def confirm_second_source(action_id, *, confirmed_by="Gev", evidence_note, ticket_id=None, certify=False):
    """Close an action that CANNOT have a machine read-back (a Telegram bot cannot read back its own sent message) with an
    out-of-band HUMAN confirmation. This is the ONLY route from NO_INDEPENDENT_READBACK to VERIFIED and it stays narrow:
    only the owner's own confirmation counts, only an already-executed action carrying NO_INDEPENDENT_READBACK qualifies,
    the observation must be stated, and NO provider call is made — nothing is re-sent. It can never be used to paper over a
    VERIFICATION_MISMATCH or a still-pending provider status."""
    a = get(action_id)
    if not a: raise ActionError("NOT_FOUND", f"no action {action_id}")
    if confirmed_by not in ("Gev", "Գև"): raise ActionError("AUTHORITY_EXCEEDED", "only Gev's own out-of-band confirmation counts as second-source evidence")
    if not str(evidence_note or "").strip(): raise ActionError("VERIFICATION_REQUIRED", "a second-source confirmation must state what was observed and where")
    if a["state"] != "EXECUTED_UNVERIFIED" or "NO_INDEPENDENT_READBACK" not in a.get("codes", []):
        raise ActionError("NOT_APPLICABLE", f"second-source confirmation applies only to an EXECUTED_UNVERIFIED action with NO_INDEPENDENT_READBACK (this one is {a['state']} {a.get('codes')})")
    req = a["request"]; ap = a.get("approval") or {}
    ev = dict((a.get("verification") or {}).get("evidence") or {})
    ev.update({"second_source": {"confirmed_by": confirmed_by, "confirmed_at": _now(), "method": "human out-of-band observation in the target chat", "observed": str(evidence_note)[:300]},
               "approved_by": ap.get("approved_by"), "approval_token": ap.get("token_id"), "approved_at": ap.get("approved_at"),
               "fingerprint": req.get("action_fingerprint"), "ticket_id": ticket_id})
    a["verification"] = {**(a.get("verification") or {}), "at": _now(), "verified": True, "independent": True, "independence_source": "HUMAN_SECOND_SOURCE",
                         "reason": f"provider accepted (message id {ev.get('provider_message_id')}) and {confirmed_by} independently confirmed the message is visible in the target chat", "evidence": ev}
    a["state"] = "VERIFIED"; a["codes"] = [c for c in a.get("codes", []) if c != "NO_INDEPENDENT_READBACK"] + ["SECOND_SOURCE_CONFIRMED"]
    a["history"].append({"at": _now(), "state": "VERIFIED", "code": "SECOND_SOURCE_CONFIRMED", "by": confirmed_by})
    a["memory"] = _update_memory(a); _save(a)
    _audit({"execution_id": a["action_id"], "ticket_id": ticket_id, "result_status": "VERIFIED", "code": "SECOND_SOURCE_CONFIRMED", "confirmed_by": confirmed_by, "evidence": ev}, required=False)
    if certify:
        from capabilities import record_write_certification
        a["certification"] = record_write_certification(req["target_system"], req["target_operation"], a["action_id"], ev); _save(a)
    return report(a)

def _update_memory(a):
    """UPDATE MEMORY / OPEN LOOP after a VERIFIED write — Deputy's own store, referencing (never overwriting) the external truth."""
    import executors
    req = a["request"]; p = req["parameters"]; op = req["target_operation"]; out = {}
    try:
        if op in ("tasks.create", "tasks.assign", "tasks.update"):
            r = executors._append_state("commitments", {"text": f"[{req['target_system']}] {p.get('title') or p.get('task') or op} → {p.get('owner', '?')}", "owner": p.get("owner", "?"), "due": p.get("due"), "condition": None, "state": "OPEN", "source_action": a["action_id"], "kind": "waiting_for"}, ["text", "owner", "due"])
            out["waiting_for"] = r["op_id"]
        elif op == "mail.send":
            r = executors._append_state("commitments", {"text": f"sent: {p.get('subject')} → {p.get('to')}", "owner": str(p.get("to")), "due": None, "condition": "awaiting reply", "state": "OPEN", "source_action": a["action_id"], "kind": "waiting_for"}, ["text", "owner", "due"])
            out["waiting_for"] = r["op_id"]
        elif op in ("tasks.close",):
            out["closed_loop"] = p.get("target_object_id") or req.get("target_object_id")
        elif op.startswith("calendar."):
            r = executors._append_state("decisions", {"decision": f"calendar {op}: {p.get('subject') or req.get('target_object_id')} @ {p.get('start')}", "reason": req["business_intent"], "source_action": a["action_id"]}, ["decision", "reason"])
            out["management_context"] = r["op_id"]
        out["execution_evidence"] = a["action_id"]
    except Exception as e: out["error"] = f"{type(e).__name__}: {e}"
    return out

# ───────────────────────── BATCH ─────────────────────────
def prepare_batch(reqs, *, session_id=None, ticket_id=None, reg=None):
    bid = "BATCH-" + uuid.uuid4().hex[:8]; out = []
    for i, r in enumerate(reqs, 1): out.append(prepare(r, session_id=session_id, ticket_id=ticket_id, batch={"batch_id": bid, "index": i, "size": len(reqs)}, reg=reg))
    card = "\n\n".join(f"### Step {i}/{len(out)}\n" + (a.get("card") or f"DENIED — {a.get('reason')}") for i, a in enumerate(out, 1))
    return {"batch_id": bid, "actions": out, "card": "**READY FOR YOUR APPROVAL — BATCH " + bid + "**\n\n" + card + "\n\n**Nothing has been changed yet.** Approve the whole enumerated batch?", "all_preparable": all(a["state"] == "APPROVAL_REQUIRED" for a in out)}

def execute_batch(batch_id, *, ticket_id=None):
    """Sequential execution of the exact approved steps; stops at the first non-VERIFIED step; the batch result is PARTIAL unless every step verified."""
    acts = sorted(list_actions("batch_id=?", (batch_id,)), key=lambda a: a["request"]["requested_at"]); results = []
    for a in acts:
        if a["state"] != "APPROVED":
            results.append({"action_id": a["action_id"], "state": a["state"], "note": "not executed"}); continue
        r = execute(a["action_id"], ticket_id=ticket_id); results.append({"action_id": a["action_id"], "state": r["state"], "codes": r.get("codes")})
        if r["state"] != "VERIFIED":
            for rest in acts[acts.index(a) + 1:]:
                if rest["state"] == "APPROVED": results.append({"action_id": rest["action_id"], "state": "APPROVED", "note": "NOT EXECUTED — an earlier step did not verify; Gev decides"})
            break
    states = [r["state"] for r in results]; overall = "VERIFIED" if all(s == "VERIFIED" for s in states) else ("PARTIAL" if any(s == "VERIFIED" for s in states) else "FAILED")
    summary = {"batch_id": batch_id, "state": overall, "approved": len(acts), "started": len([r for r in results if r["state"] not in ("APPROVED",)]), "verified": states.count("VERIFIED"), "steps": results,
               "rollback": "none performed — a rollback is a mutation and needs its own approval", "user_decision_required": overall != "VERIFIED"}
    _audit({"execution_id": batch_id, "ticket_id": ticket_id, "result_status": f"BATCH_{overall}", "steps": results}, required=False); return summary

# ───────────────────────── REPORT ─────────────────────────
def report(a):
    req = a["request"]; st = a["state"]
    canon = {"VERIFIED": "DONE", "EXECUTED_UNVERIFIED": "NOT DONE", "FAILED": "NOT DONE", "DENIED": "BLOCKED", "REJECTED": "BLOCKED", "RESULT_UNKNOWN": "RESULT_UNKNOWN", "PARTIAL": "PARTIAL", "APPROVAL_REQUIRED": "NOT DONE", "APPROVED": "NOT DONE", "PREPARED": "NOT DONE", "EXECUTING": "RESULT_UNKNOWN"}[st]
    ver = a.get("verification") or {}
    codes = a.get("codes", [])
    if st == "EXECUTED_UNVERIFIED" and ("NO_INDEPENDENT_READBACK" in codes or "AWAITING_PROVIDER_STATUS" in codes): canon = "PARTIAL"     # provider accepted; independent evidence absent/pending — never DONE, never NOT DONE
    gev = {"VERIFIED": "none", "APPROVAL_REQUIRED": "approve or reject the presented action", "RESULT_UNKNOWN": "decide after reconciliation (retry only if reconciliation proved the write is absent)",
           "EXECUTED_UNVERIFIED": ("confirm in the chat that the message is visible (no read-back exists for a bot's own message)" if "NO_INDEPENDENT_READBACK" in codes else "none yet — Deputy reconciles when the provider's delivery status arrives" if "AWAITING_PROVIDER_STATUS" in codes else "check the target system — provider reported success but the read-back does not match"),
           "REJECTED": "a new decision/approval is required", "DENIED": "see reason", "FAILED": "see reason"}.get(st, "see reason")
    return {"canonical": canon, "state": st, "action_id": a["action_id"], "what": f"{req['target_operation']} — {req['business_intent']}", "target": f"{req['target_system']} {req['target_object_type']} {req.get('target_object_id') or ''}".strip(),
            "result": (a.get("execution") or {}).get("provider_result") or a.get("reason") or (a.get("reconciliation") or {}).get("outcome"), "verification": ver.get("reason") if ver else "not verified", "evidence": ver.get("evidence"),
            "open_loop": a.get("memory"), "gev_action": gev, "codes": a.get("codes", []), "mutation_performed": st in ("VERIFIED", "EXECUTED_UNVERIFIED", "RESULT_UNKNOWN"), "approval": {k: (a.get("approval") or {}).get(k) for k in ("token_id", "approved_by", "approved_at", "consumed")} if a.get("approval") else None,
            "reconciliation": a.get("reconciliation"), "card": a.get("card") if st == "APPROVAL_REQUIRED" else None}
