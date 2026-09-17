# -*- coding: utf-8 -*-
"""Skill Engine: registry validation · intent router (minimum complete graph) · authority gate ·
fail-closed enforcement · execution with validation + completion verification · hardened audit · gate tickets.

Mandatory pipeline (every meaningful request; enforced mechanically by .claude/hooks/gate.py):
  INTENT CAPTURE → SKILL RESOLUTION → REQUIRED SKILL GRAPH → PRECONDITIONS → AUTHORITY → EXECUTION
  → VALIDATION → COMPLETION VERIFICATION → AUDIT

Blocked codes (every one has a test in test_failclosed.py):
  MISSING_SKILL DISABLED_SKILL MISSING_INPUT TOOL_UNAVAILABLE NOT_OPERATIONAL AUTHORITY_EXCEEDED APPROVAL_REQUIRED
  INVALID_SOURCE STALE_SOURCE CONFLICTING_SOURCE VALIDATION_FAILED VERIFICATION_FAILED
"""
import json, re, time, uuid, hashlib, datetime, pathlib, inspect

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # Command-center/ (workspace root)
import os as _os
REGISTRY_PATH = pathlib.Path(_os.environ.get("SKILL_REGISTRY_PATH") or (HERE / "registry.json"))
CERT_DIR = HERE / "certifications"
AUDIT_JSONL = HERE.parent / "audit" / "skill_audit.jsonl"     # human-readable append-only mirror of the audit table
POLICY_PATH = HERE.parent / "policy" / "workspace_policy.json"
STATE_DIR = pathlib.Path(_os.environ.get("SKILL_STATE_DIR") or (HERE.parent / "state"))     # .claude/state (workspace contract); tests/hook-harness redirect

MATURITY = ["L0", "L1", "L2", "L3", "L4"]
BLOCK_CODES = ["MISSING_SKILL","DISABLED_SKILL","MISSING_INPUT","TOOL_UNAVAILABLE","NOT_OPERATIONAL","AUTHORITY_EXCEEDED",
               "APPROVAL_REQUIRED","INVALID_SOURCE","STALE_SOURCE","CONFLICTING_SOURCE","VALIDATION_FAILED","VERIFICATION_FAILED"]
SUCCESS_STATUSES = {"EXECUTED","VERIFIED","RECORDED","DUPLICATE","ASSISTED"}
NON_SUCCESS = {"BLOCKED","FAILED","VALIDATION_FAILED","VERIFICATION_FAILED","ATTEMPTED"}
REQUIRED_FIELDS = ["skill_id","name","version","domain","purpose","business_outcome","description",
  "maturity_level","status","triggers","anti_triggers","required_inputs","optional_inputs","preconditions",
  "required_context","authoritative_sources","dependencies","required_skills","allowed_tools","required_tools",
  "execution_steps","expected_outputs","validation_rules","approval_requirements","authority_boundary",
  "failure_conditions","fallback_behavior","logging_requirements","success_metrics","test_cases","eval_cases",
  "last_verified"]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SENSITIVE = re.compile(r"(password|passwd|token|secret|api[_-]?key|գաղտնաբառ)", re.I)
# CREDENTIAL VALUES — a secret does not only arrive under a sensitive KEY NAME: it is pasted into a prompt, an intent or a
# command line as an ordinary string. Those shapes are scrubbed everywhere Deputy persists text (audit rows, audit mirror,
# ticket excerpts) so a credential can never reach the durable export or Git. Shapes only — no secret is stored here.
CREDENTIAL_VALUE_RX = [
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b"),                  # Telegram bot token
    re.compile(r"\bEAA[A-Za-z0-9]{20,}\b"),                        # Meta / WhatsApp Cloud API access token
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{16,}\b"),               # OpenAI-style API key
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),                 # GitHub token
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),               # Slack token
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                           # AWS access key id
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{20,}"),             # bearer header pasted into text
]
BITRIX_CODE_RX = re.compile(r"(/rest/\d+/)[A-Za-z0-9]{8,}(/?)")    # Bitrix24 inbound webhook code inside a URL

def scrub(text):
    """Replace credential-shaped VALUES inside free text with a marker (key-name redaction stays in SENSITIVE)."""
    t = str(text)
    for rx in CREDENTIAL_VALUE_RX: t = rx.sub("<secret>", t)
    return BITRIX_CODE_RX.sub(r"\1<secret>\2", t)
CERT_FIELDS_EXCLUDED = {"evidence", "certification", "last_verified", "maturity_level"}

class SkillError(Exception): pass

def _norm(t): return re.sub(r"\s+", " ", str(t).lower().strip())
def _now(): return datetime.datetime.now().isoformat(timespec="seconds")

# ───────────────────────── store access (redirectable by tests) ─────────────────────────
def _store():
    import store
    return store.get(STATE_DIR)

def _scope():
    """HARD SCOPE LOCK engine (.claude/policy/scope.py) — the rule lives in the policy, never duplicated here."""
    import sys as _sys
    _sys.path.insert(0, str(HERE.parent / "policy"))
    import scope
    return scope

# ───────────────────────── registry ─────────────────────────
def load_registry(path=REGISTRY_PATH):
    if not pathlib.Path(path).exists():
        raise SkillError(f"registry missing: {path}")
    reg = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    reg["_index"] = {s["skill_id"]: s for s in reg["skills"]}
    reg["_alias"] = {old: r["merged_into"] for old, r in reg.get("retired", {}).items()}
    return reg

def canonical_contract(skill):
    return {k: v for k, v in skill.items() if k not in CERT_FIELDS_EXCLUDED}

def _closure_source(fn, mod, seen=None):
    """Source of fn plus every module-level function it references, transitively (implementation fingerprint)."""
    seen = seen if seen is not None else set()
    if fn.__name__ in seen: return ""
    seen.add(fn.__name__)
    try: src = inspect.getsource(fn)
    except (OSError, TypeError): src = repr(fn)
    for name in getattr(fn, "__code__", None).co_names if hasattr(fn, "__code__") else ():
        obj = getattr(mod, name, None)
        if inspect.isfunction(obj) and obj.__module__ == mod.__name__: src += _closure_source(obj, mod, seen)
    return src

def core_fingerprint():
    h = hashlib.sha256()
    for f in ("engine.py", "store.py"):
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:16]

def skill_fingerprint(reg, skill):
    """sha256(contract ⊕ executor implementation closure ⊕ engine/store core). Any change → stale certification."""
    import executors
    h = hashlib.sha256(json.dumps(canonical_contract(skill), ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))
    fn = getattr(executors, skill.get("executor") or "", None)
    if fn: h.update(_closure_source(fn, executors).encode("utf-8"))
    h.update(_closure_source(executors.validate_output, executors).encode("utf-8"))
    h.update(_closure_source(executors.verify_completion, executors).encode("utf-8"))
    h.update(core_fingerprint().encode("utf-8"))
    return h.hexdigest()[:24]

def read_certification(skill_id):
    p = CERT_DIR / f"{skill_id}.json"
    if not p.exists(): return None
    try: return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError: return {"result": "CORRUPT"}

def validate_registry(reg, require_evidence=True):
    """Returns list of problems (empty = valid).
    require_evidence=True  → certified validity: every L3+/L2+ skill must carry a PASS, non-stale per-skill certification (production gate).
    require_evidence=False → structural validity only (used by the test suite, which runs before certification)."""
    problems, seen = [], set()
    ladder, tools = reg["authority_ladder"], reg["tools_available"]
    ids = {s["skill_id"] for s in reg["skills"]}
    retired = set(reg.get("retired", {}))
    for s in reg["skills"]:
        sid = s.get("skill_id", "?")
        for f in REQUIRED_FIELDS:
            if f not in s: problems.append(f"{sid}: missing field {f}")
        if sid in seen: problems.append(f"duplicate skill_id {sid}")
        if sid in retired: problems.append(f"{sid}: active skill uses a retired id")
        seen.add(sid)
        if not SEMVER.match(str(s.get("version",""))): problems.append(f"{sid}: bad version {s.get('version')}")
        if s.get("maturity_level") not in MATURITY: problems.append(f"{sid}: bad maturity {s.get('maturity_level')}")
        if s.get("status") not in ("active","disabled","deprecated"): problems.append(f"{sid}: bad status")
        if s["authority_boundary"].get("max_action") not in ladder: problems.append(f"{sid}: bad max_action")
        for d in s.get("dependencies", []) + s.get("required_skills", []):
            if d not in ids: problems.append(f"{sid}: unknown dependency {d}")
        for t in s.get("required_tools", []):
            if t not in tools: problems.append(f"{sid}: unknown tool {t}")
        for a in s.get("absorbed", []):
            if reg.get("retired", {}).get(a, {}).get("merged_into") != sid: problems.append(f"{sid}: absorbed {a} not retired into it")
        lvl = MATURITY.index(s.get("maturity_level","L0"))
        if lvl >= 2 and not s.get("executor"): problems.append(f"{sid}: {s['maturity_level']} without executor")
        if lvl > MATURITY.index(s.get("declared_maturity", "L4")): problems.append(f"{sid}: maturity above declared target")
        if require_evidence and lvl >= 3:
            cert = read_certification(sid)
            if not cert: problems.append(f"{sid}: {s['maturity_level']} requires a per-skill certification record (UNCERTIFIED)")
            elif cert.get("result") != "PASS": problems.append(f"{sid}: certification result {cert.get('result')} (must be PASS)")
            elif MATURITY.index(cert.get("maturity_level", "L0")) < lvl: problems.append(f"{sid}: certified {cert.get('maturity_level')} < declared {s['maturity_level']}")
            elif cert.get("fingerprint") != skill_fingerprint(reg, s): problems.append(f"{sid}: STALE_CERTIFICATION (implementation/contract changed since certification)")
            elif cert.get("skill_version") != s["version"]: problems.append(f"{sid}: certification is for version {cert.get('skill_version')} not {s['version']}")
        elif not require_evidence and lvl >= 3 and not (s.get("test_cases") or s.get("eval_cases") or True):
            pass
    graph = {s["skill_id"]: set(s.get("dependencies", [])) for s in reg["skills"]}
    problems += [f"circular dependency: {c}" for c in find_cycles(graph)]
    for name, chain in reg.get("chains", {}).items():
        for sid in chain:
            if sid not in ids: problems.append(f"chain {name}: unknown skill {sid}")
    for name in reg.get("chain_triggers", {}):
        if name not in reg.get("chains", {}): problems.append(f"chain_triggers: unknown chain {name}")
    for key in reg.get("tool_intents", {}):
        if key not in tools: problems.append(f"tool_intents: unknown tool {key}")
    return problems

def find_cycles(graph):
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}; cycles = []
    def dfs(n, path):
        color[n] = GREY; path.append(n)
        for m in graph.get(n, ()):
            if m not in color: continue
            if color[m] == GREY: cycles.append(" -> ".join(path[path.index(m):] + [m]))
            elif color[m] == WHITE: dfs(m, path)
        path.pop(); color[n] = BLACK
    for n in graph:
        if color[n] == WHITE: dfs(n, [])
    return cycles

def topo_order(reg, skill_ids):
    """Dependencies first. Raises on cycle."""
    idx, order, state = reg["_index"], [], {}
    def visit(sid, stack):
        if state.get(sid) == 2: return
        if state.get(sid) == 1: raise SkillError("cycle: " + " -> ".join(stack + [sid]))
        state[sid] = 1
        for d in idx[sid].get("dependencies", []): visit(d, stack + [sid])
        state[sid] = 2; order.append(sid)
    for sid in skill_ids: visit(sid, [])
    return order

# ───────────────────────── router (minimum complete graph) ─────────────────────────
def _hit(trigger, text):
    """Trigger matches only at a word start (prefix allowed: 'priorit' → 'prioritize'); avoids 'week' inside 'weekly'-style over-routing
    by requiring curated triggers to be specific."""
    t = _norm(trigger)
    if not t: return False
    return re.search(r"(?:^|(?<=[^\w]))" + re.escape(t), text) is not None

def _specific(trigger, chain_matched=False):
    """With a curated chain already selected, only multi-word triggers may add skills (single words like 'retention' inside
    'retention flow' are noise); without a chain, a single specific word (≥7 chars) may route."""
    t = _norm(trigger)
    return len(t.split()) >= 2 or (not chain_matched and len(t) >= 7)

def resolve_alias(reg, skill_id):
    """Retired id → survivor (or '<tool:x>' marker). Active ids pass through."""
    if skill_id in reg["_index"]: return skill_id
    return reg["_alias"].get(skill_id, skill_id)

# ───────────────────────── domain boundary: SYSTEM/MAINTENANCE intents never route to business skills ─────────────────────────
# Requests about the agent runtime, Skill System, hooks, workspace policy, tests, repository, configuration, architecture or
# state/audit infrastructure are NOT business Sales/Operations work, even when they contain overlapping words ('pipeline',
# 'audit', 'analysis'). They resolve UNRESOLVED (domain SYSTEM) → fail closed: state tools stay denied until an audited
# `skill.py maintenance` (protected files, only if the USER asked) or `skill.py declare` path exists. Bare business words
# ('pipeline', 'audit', 'test the tariff', 'network maintenance') are deliberately NOT system terms.
SYSTEM_PATTERNS = [
    # agent runtime / Skill System / enforcement machinery
    r"skill[ _-]?(system|execution|graph|gate|registry|engine|resolver|chain|routing|pipeline|certif)", r"skill\.py", r"engine\.py", r"store\.py", r"executors?\.py",
    r"build_registry", r"evals?\.py", r"test_[a-z_]+\.py", r"python_runtime", r"hook\.sh", r"\bhooks?\b", r"\bgate\b", r"\bresolver\b", r"\bregistry\b", r"\bcertif",
    r"\benforcement\b", r"\bhardening\b", r"\bfail[- ]?closed\b", r"\bagent runtime\b", r"\bruntime\b", r"\bdeputy'?s? (code|runtime|hooks?|engine)\b",
    r"(system|skill|hook|gate|runtime|agent|deputy) maintenance", r"maintenance (grant|mode|intent|routing|request)",
    r"(skill|intent|prompt|maintenance) routing", r"routing (boundary|defect|fix|correction|logic|eval)",
    # workspace policy / configuration / architecture
    r"workspace[ _-]?(policy|guard|contract|validat)", r"validate_workspace", r"settings(\.local)?\.json", r"claude\.md", r"\.gitignore", r"\.claude[/\\]",
    r"\bconfig\b", r"configuration (file|of the (agent|deputy|hook|skill|gate|runtime|workspace|repo))", r"\barchitecture\b",
    # tests / evals / release
    r"\b(unit|regression|store|enforcement|hardening|workspace|routing|integration) tests?\b", r"\btests\b", r"\btest (suite|file|coverage)\b", r"\bevals?\b", r"\brelease suite\b", r"\bunittest\b",
    # repository / git
    r"\bgit\b", r"\bgithub\b", r"\brepo(sitory)?\b", r"\bbranch (main|master)\b", r"\bgit commit\b", r"\bcommits? (the |these |all |my |our )?(changes|files|fix|work|code)\b", r"\bpull request\b", r"\bremote origin\b",
    # interpreter / dependencies / deployment / code
    r"\binterpreter\b", r"\bpython\b", r"\bvenv\b", r"\bvirtual ?env", r"\bpip\b", r"\bdependenc(y|ies)\b", r"\brequirements\.(txt|lock)\b",
    r"\bdeployment pipeline\b", r"\bdeploy(ment)? (of |the )?(agent|hook|skill|runtime|code|release|system)\b", r"\bci/?cd\b", r"\bcodebase\b", r"\brefactor", r"\btraceback\b", r"\bstack ?trace\b",
    # state / audit infrastructure
    r"\bsqlite\b", r"\bstate (store|dir|db|directory)\b", r"skill_state", r"skill_audit", r"\baudit (store|mirror|infrastructure|jsonl|db)\b", r"\baudit log (store|infrastructure|table)\b",
    # Armenian
    r"հմտությունների համակարգ", r"հուկ", r"դարպաս", r"թեստ", r"ռեպոզիտոր", r"վկայագ", r"կոդը", r"կոնֆիգ", r"ինտերպրետ", r"հմտության (կոդ|ուղղորդ)",
]
_SYSTEM_RX = [re.compile(p) for p in SYSTEM_PATTERNS]

def system_terms(text):
    """Matched system-domain terms in a normalized intent (empty list = business domain)."""
    t = _norm(text); hits = []
    for rx in _SYSTEM_RX:
        m = rx.search(t)
        if m and m.group(0) not in hits: hits.append(m.group(0))
    return hits

def resolve(reg, intent):
    """USER INTENT → minimum complete skill graph.
    1. Longest matching chain trigger selects a curated chain (prevents under-routing).
    2. Individual skill triggers add skills only when SPECIFIC (multi-word or ≥7 chars) if a chain matched, or any trigger if no chain
       (prevents over-routing by generic words). Anti-triggers exclude.
    3. Tool intents attach tool requirements (fail closed at the gate: TOOL_UNAVAILABLE) instead of routing to fake tool-skills.
    4. Dependencies are added in topological order."""
    text = _norm(intent); idx = reg["_index"]
    try:                               # Mission 4.2: 'GO' / 'OK' / 'Արա' / 'no' about a pending action is an approval event, not a business intent
        import actions
        if "action_runtime" in idx and actions.classify_approval(intent) in ("APPROVAL", "REJECTION", "MODIFIED"):
            return {"intent": intent, "primary": "action_runtime", "supporting": [], "chain": ["action_runtime"], "status": "RESOLVED", "domain": "BUSINESS", "chain_name": "approval",
                    "reasons": ["approval/rejection text → action_runtime (bound to the pending exact action)"], "required_inputs": [], "tool_requirements": []}
    except Exception: pass
    sysm = system_terms(text)          # 0. domain boundary — system/maintenance work is never business-skill work
    if sysm:
        return {"intent": intent, "primary": None, "supporting": [], "chain": [], "status": "UNRESOLVED", "domain": "SYSTEM", "system_terms": sysm,
                "reasons": [f"SYSTEM/MAINTENANCE intent (matched {sysm[:4]}): business Sales/Operations skills are not routed for agent-runtime / Skill System / hooks / "
                            f"workspace-policy / tests / repository / configuration / architecture / state-audit work; governed path = skill.py maintenance (protected files) or declare (audited)"],
                "tool_requirements": []}
    reasons, chain_name, best = [], None, 0
    for name, trigs in reg.get("chain_triggers", {}).items():
        for t in trigs:
            if _hit(t, text) and len(_norm(t)) > best: chain_name, best, why = name, len(_norm(t)), t
    if chain_name: reasons.append(f"chain '{chain_name}' via trigger {why!r}")
    selected = list(reg["chains"][chain_name]) if chain_name else []
    long_prompt = len(text.split()) > 60          # specs/essays: the word-sweep only adds noise → chain-only (else UNRESOLVED, classified by prompt kind)
    for s in reg["skills"]:
        if long_prompt: reasons.append("long prompt: individual trigger sweep skipped (chain-only resolution)") if s is reg["skills"][0] else None; break
    for s in ([] if long_prompt else reg["skills"]):
        if s["status"] != "active": continue
        if any(_hit(a, text) for a in s["anti_triggers"]): continue
        hit = [t for t in s["triggers"] if _hit(t, text)]
        if not hit or s["skill_id"] in selected: continue
        if chain_name and not any(_specific(t, chain_matched=True) for t in hit): continue
        selected.append(s["skill_id"]); reasons.append(f"{s['skill_id']} via {hit[0]!r}")
    tool_req = sorted({tool for tool, trigs in reg.get("tool_intents", {}).items() if any(_hit(t, text) for t in trigs)})
    for tool in tool_req: reasons.append(f"tool '{tool}' required via tool_intents")
    if not selected:
        return {"intent": intent, "primary": None, "supporting": [], "chain": [], "reasons": reasons or ["no trigger matched"],
                "status": "UNRESOLVED", "domain": "BUSINESS", "tool_requirements": tool_req}
    primary = selected[0]
    try: ordered = topo_order(reg, selected)
    except SkillError as e:
        return {"intent": intent, "primary": primary, "supporting": selected[1:], "chain": [], "reasons": [str(e)], "status": "BLOCKED", "domain": "BUSINESS"}
    return {"intent": intent, "primary": primary, "supporting": [s for s in selected[1:]], "chain": ordered,
            "explicit": selected, "chain_name": chain_name, "reasons": reasons, "status": "RESOLVED", "domain": "BUSINESS",
            "required_tools": sorted({t for sid in ordered for t in idx[sid]["required_tools"]}),
            "tool_requirements": tool_req,
            "required_inputs": sorted({i for sid in ordered for i in idx[sid]["required_inputs"]}),
            "approval_requirements": sorted({a for sid in ordered for a in idx[sid]["approval_requirements"]})}

# ───────────────────────── gate (fail-closed) ─────────────────────────
def authority_check(reg, skill, action_level, approval_token=None):
    ladder = reg["authority_ladder"]
    if action_level not in ladder: return {"ok": False, "reason": f"unknown action level {action_level!r}", "code": "AUTHORITY_EXCEEDED"}
    mx = skill["authority_boundary"]["max_action"]
    if ladder.index(action_level) > ladder.index(mx):
        return {"ok": False, "reason": f"{action_level} exceeds skill max_action {mx}", "code": "AUTHORITY_EXCEEDED"}
    if action_level in ("EXECUTE_EXTERNAL", "EXECUTE_MATERIAL") and not approval_token:
        return {"ok": False, "reason": f"{action_level} requires explicit approval token from the Head", "code": "APPROVAL_REQUIRED"}
    return {"ok": True}

def _source_check(reg, skill, inputs, cache):
    """INVALID_SOURCE / STALE_SOURCE for skills bound to an authoritative file source."""
    import executors
    srcs = skill.get("authoritative_sources") or []
    if not srcs or "tasks" in inputs: return None                       # caller supplied data explicitly
    path = inputs.get("path") or srcs[0]
    key = str(path)
    if key not in cache: cache[key] = executors.source_verification({"path": path, "schema": "tasks"})
    v = cache[key]
    if v["status"] != "VERIFIED":
        return {"code": "INVALID_SOURCE", "reason": f"{v.get('code')}: {v.get('reason') or v.get('path')}"}
    max_age = (skill.get("source_policy") or {}).get("max_age_hours")
    if max_age and v.get("age_hours", 0) > max_age and not inputs.get("accept_stale"):
        return {"code": "STALE_SOURCE", "reason": f"{v['path']} is {v['age_hours']}h old (> {max_age}h policy); pass accept_stale=true to acknowledge (audited)"}
    return None

def _conflict_check(skill, inputs):
    """CONFLICTING_SOURCE: contradictory sources may only be consumed by the reconciliation/confidence skills."""
    if skill["skill_id"] in ("source_reconciliation", "confidence_handling"): return None
    if inputs.get("_conflict"):
        return {"code": "CONFLICTING_SOURCE", "reason": f"unresolved contradiction: {inputs['_conflict']}"}
    srcs = inputs.get("sources")
    if isinstance(srcs, list) and len(srcs) >= 2 and len({str(s.get("value")) for s in srcs if isinstance(s, dict)}) > 1:
        return {"code": "CONFLICTING_SOURCE", "reason": "inputs.sources disagree; run source_reconciliation first"}
    return None

def gate(reg, plan, inputs=None, action_level="ANALYZE", approval_token=None, allow_assisted=True):
    """Precondition + authority check for every skill in the chain. Fail-closed. Never raises on bad input."""
    inputs = inputs or {}; idx = reg["_index"]; tools = reg["tools_available"]
    if plan.get("status") != "RESOLVED":
        missing = [t for t in plan.get("tool_requirements", []) if not tools.get(t)]      # a tool intent with no integrated tool: the specific, fail-closed reason
        blocked = [{"skill": f"<tool:{t}>", "code": "TOOL_UNAVAILABLE", "reason": f"intent requires tool '{t}' which is not integrated in this runtime"} for t in missing]
        blocked.append({"skill": None, "code": "MISSING_SKILL", "reason": f"no skill resolved: {plan.get('reasons')}"})
        return {"status": "BLOCKED", "code": "TOOL_UNAVAILABLE" if missing else "UNRESOLVED", "blocked": blocked, "runnable": [], "assisted": [], "action_level": action_level}
    blocked, runnable, assisted, cache = [], [], [], {}
    for tool in plan.get("tool_requirements", []):
        if not tools.get(tool):
            blocked.append({"skill": f"<tool:{tool}>", "code": "TOOL_UNAVAILABLE", "reason": f"intent requires tool '{tool}' which is not integrated in this runtime"})
    for sid in plan["chain"]:
        s = idx.get(sid)
        if not s:
            alias = reg["_alias"].get(sid)
            blocked.append({"skill": sid, "code": "MISSING_SKILL", "reason": f"skill not in registry" + (f" (retired → {alias})" if alias else "")}); continue
        if s["status"] != "active": blocked.append({"skill": sid, "code": "DISABLED_SKILL", "reason": f"status={s['status']}"}); continue
        missing_tools = [t for t in s["required_tools"] if not tools.get(t)]
        if missing_tools: blocked.append({"skill": sid, "code": "TOOL_UNAVAILABLE", "reason": f"tools not integrated: {missing_tools}"}); continue
        lvl = MATURITY.index(s["maturity_level"])
        if lvl == 0 or not s.get("executor"):
            blocked.append({"skill": sid, "code": "NOT_OPERATIONAL", "reason": f"maturity {s['maturity_level']} — declared only, cannot execute"}); continue
        missing_in = [i for i in s["required_inputs"] if i not in inputs and i != "tasks"]  # tasks auto-loaded from xlsx
        if missing_in: blocked.append({"skill": sid, "code": "MISSING_INPUT", "reason": f"required inputs missing: {missing_in}"}); continue
        src = _source_check(reg, s, inputs, cache)
        if src: blocked.append({"skill": sid, **src}); continue
        con = _conflict_check(s, inputs)
        if con: blocked.append({"skill": sid, **con}); continue
        a = authority_check(reg, s, action_level, approval_token)
        if not a["ok"]: blocked.append({"skill": sid, "code": a.get("code", "AUTHORITY_EXCEEDED"), "reason": a["reason"]}); continue
        if lvl >= 2: runnable.append(sid)
        elif lvl == 1 and allow_assisted: assisted.append(sid)
        else: blocked.append({"skill": sid, "code": "NOT_OPERATIONAL", "reason": f"maturity {s['maturity_level']} — assisted execution disabled"})
    status = "OK" if not blocked else ("PARTIAL" if (runnable or assisted) else "BLOCKED")
    return {"status": status, "runnable": runnable, "assisted": assisted, "blocked": blocked, "action_level": action_level}

# ───────────────────────── audit (hardened store) ─────────────────────────
def _redact(obj):
    if isinstance(obj, dict): return {k: ("<redacted>" if SENSITIVE.search(k) else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list): return [_redact(v) for v in obj]
    if isinstance(obj, str):
        t = scrub(obj)                                   # credential-shaped values are scrubbed before anything is persisted
        return t[:400] + "…" if len(t) > 400 else t
    return obj

_IDENTITY = None
def identity():
    """Canonical agent/workspace identity — the single source of truth is .claude/policy/workspace_policy.json → identity."""
    global _IDENTITY
    if _IDENTITY is None:
        try: _IDENTITY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))["identity"]
        except Exception: _IDENTITY = {"name": "UNKNOWN", "role": "UNKNOWN", "workspace": "UNKNOWN", "owner": "UNKNOWN"}
    return _IDENTITY

_INTERACTION = None
def interaction():
    """Canonical INTERACTION contract - single source of truth is .claude/policy/workspace_policy.json -> interaction.
    Fails closed: if the block cannot be read, the Armenian rule is still returned, never an empty permission to switch language."""
    global _INTERACTION
    if _INTERACTION is None:
        try: _INTERACTION = json.loads(POLICY_PATH.read_text(encoding="utf-8"))["interaction"]
        except Exception:
            _INTERACTION = {"user_language": "hy-AM", "rule": "Every user-facing communication with the owner is in Eastern Armenian.",
                            "degraded": "policy unreadable - the Armenian default still applies"}
    return _INTERACTION

def audit(record):
    record = dict(record); record.setdefault("ts", _now()); record.setdefault("audit_id", uuid.uuid4().hex[:16]); record.setdefault("agent", identity()["name"])
    rec = _redact(record)
    _store().record("audit", record["audit_id"], rec, extra_cols={"execution_id": rec.get("execution_id"), "skill_id": rec.get("skill_id"),
                                                                   "result_status": rec.get("result_status")})
    try:
        AUDIT_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_JSONL.open("a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except OSError: pass                                    # the SQLite table is the truth; the mirror is best-effort
    return rec

def read_audit(limit=50):
    return _store().tail("audit", limit)

def audit_for_execution(execution_id):
    return _store().list("audit", where="execution_id=?", args=(execution_id,))

# ───────────────────────── canonical Deputy request entry ─────────────────────────
def run_deputy_request(reg, intent, inputs=None, *, action_level="ANALYZE", approval_token=None, session_id="", source="DeputyRuntime"):
    """Canonical Deputy production entry: ticket → brain evidence → Skill Engine resolution → execution/audit.

    Professional Brains only provide auditable reasoning context. The existing resolver, gate,
    executors, Action Runtime and Store remain authoritative for executable behavior.
    """
    inputs = dict(inputs or {})
    ticket = open_ticket(reg, intent, session_id=session_id, source=source, inputs=inputs)
    try:
        arch = pathlib.Path(ROOT) / ".claude" / "architecture"
        import sys as _sys
        if str(arch) not in _sys.path: _sys.path.insert(0, str(arch))
        from brain_router import route as _route
        brain_evidence = _route(intent)
    except Exception as exc:
        return {"status":"BLOCKED", "blocked":[{"code":"BRAIN_ROUTER_UNAVAILABLE", "reason":str(exc)}], "ticket_id":ticket["ticket_id"]}
    plan = resolve(reg, intent)
    if plan.get("status") != "RESOLVED":
        return {"status":"BLOCKED", "ticket_id":ticket["ticket_id"], "brains":brain_evidence,
                "plan":plan, "blocked":[{"code":"NO_APPLICABLE_SKILL", "reason":plan.get("reasons")}]}
    inputs["_brain_context"] = {"identity":"DEPUTY", "selected_brains":brain_evidence["selected_brains"],
                                  "synthesis_required":brain_evidence["synthesis_required"]}
    result = run_plan(reg, plan, inputs, action_level=action_level, approval_token=approval_token,
                      ticket_id=ticket["ticket_id"])
    result["brains"] = brain_evidence
    result["resolved_skills"] = plan.get("chain", [])
    result["ticket_id"] = ticket["ticket_id"]
    return result

# ───────────────────────── execution ─────────────────────────
def run_skill(reg, skill_id, inputs=None, *, intent="", action_level="ANALYZE", approval_token=None,
              execution_id=None, selection_reason="direct", ticket_id=None):
    """Execute ONE skill through the full pipeline; always writes an audit record. Never returns a success status
    without validation AND completion verification passing."""
    import executors
    inputs = inputs or {}
    alias = resolve_alias(reg, skill_id)
    if alias != skill_id: selection_reason = f"{selection_reason}; alias {skill_id}→{alias}"; skill_id = alias
    s = reg["_index"].get(skill_id)
    execution_id = execution_id or uuid.uuid4().hex[:12]
    t0 = time.perf_counter()
    rec = {"execution_id": execution_id, "ticket_id": ticket_id, "intent": intent, "skill_id": skill_id,
           "skill_version": s["version"] if s else None, "selection_reason": selection_reason,
           "inputs": inputs, "action_level": action_level, "approval_required": action_level in ("EXECUTE_EXTERNAL","EXECUTE_MATERIAL"),
           "sources": s["authoritative_sources"] if s else [], "tools": s["required_tools"] if s else []}
    if inputs.get("accept_stale"): rec["stale_source_acknowledged"] = True
    def done(status, **extra):
        rec.update(result_status=status, duration_ms=round((time.perf_counter() - t0) * 1000, 1), **extra)
        audit(rec)
        out = {"status": status, "skill": skill_id, "execution_id": execution_id, "ticket_id": ticket_id}
        out.update({k: v for k, v in extra.items() if k in ("blocked", "result", "validated", "validation_error", "verification", "error", "business_context")})
        if ticket_id: _ticket_attach(ticket_id, {"execution_id": execution_id, "skill": skill_id, "status": status})
        return out
    plan = {"status": "RESOLVED", "chain": [skill_id]}
    g = gate(reg, plan, inputs, action_level, approval_token)
    if g["status"] != "OK" and skill_id not in g["assisted"]:
        return done("BLOCKED", blocked=g["blocked"], validated=False)
    fn = getattr(executors, s["executor"] or "", None)
    if not fn:
        return done("BLOCKED", blocked=[{"skill": skill_id, "code": "NOT_OPERATIONAL", "reason": "executor not implemented"}], validated=False)
    # BUSINESS CONTEXT — the Business Operating Model (.claude/business) is consulted for EVERY execution: playbook, KPIs,
    # processes, owner, sources, rules and structured gap codes. Absent model → BUSINESS_CONTEXT_MISSING (never invented).
    try:
        import business
        bctx = business.context_for(skill_id, intent, inputs, inputs.get("_chain_name"))
    except Exception as e: bctx = {"available": False, "gaps": ["BUSINESS_CONTEXT_MISSING"], "reason": f"{type(e).__name__}: {e}"}
    rec["business_context"] = business.summary(bctx) if "business" in globals() or True else None
    try:
        result = fn({**({"intent": intent} if intent and not str(intent).startswith("run ") else {}), **{k: v for k, v in inputs.items() if not k.startswith("_")}, "business_context": bctx}, skill=s, reg=reg)
        ok, verr = executors.validate_output(skill_id, result)
        if not ok:
            return done("VALIDATION_FAILED", validated=False, validation_error=verr, result_summary=executors.summarize(result))
        status = result.get("status", "EXECUTED")
        if s["maturity_level"] == "L1" and status == "EXECUTED": status = "ASSISTED"
        if status == "BLOCKED":
            return done("BLOCKED", blocked=[{"skill": skill_id, "code": result.get("code", "MISSING_INPUT"), "reason": result.get("reason")}], validated=True, result=result, business_context=rec["business_context"])
        vok, vinfo = executors.verify_completion(skill_id, result, inputs)
        if not vok:
            return done("VERIFICATION_FAILED", validated=True, verification={"ok": False, "detail": vinfo}, result_summary=executors.summarize(result), result=result, business_context=rec["business_context"])
        return done(status, validated=True, verification={"ok": True, "detail": vinfo}, result_summary=executors.summarize(result), result=result, business_context=rec["business_context"])
    except Exception as e:
        return done("FAILED", validated=False, error=f"{type(e).__name__}: {e}")

def _lctx(sid, reg):
    """Live-source status for a gate-blocked Sales/Operations step: which integration could answer and where it stands (READ-ONLY layer)."""
    s = reg["_index"].get(sid) or {}; dom = str(s.get("domain", ""))
    if not (dom.startswith("B_") or dom.startswith("C_")): return None
    try:
        import executors
        return executors._live_sources("operations" if dom.startswith("C_") else "sales")
    except Exception: return None

def _bctx(sid, plan, inputs):
    """Business context for a step that the gate blocked before execution — the BLOCKED answer still names the playbook, KPIs, data and owner."""
    try:
        import business
        return business.summary(business.context_for(sid, plan.get("intent", ""), inputs, plan.get("chain_name")))
    except Exception as e: return {"available": False, "gaps": ["BUSINESS_CONTEXT_MISSING"], "reason": f"{type(e).__name__}: {e}"}

def run_plan(reg, plan, inputs=None, *, action_level="ANALYZE", approval_token=None, ticket_id=None):
    inputs = dict(inputs or {}); inputs["_chain_name"] = plan.get("chain_name")          # business context resolves the playbook from the chain
    return _run_plan_impl(reg, plan, inputs, action_level=action_level, approval_token=approval_token, ticket_id=ticket_id)

def _run_plan_impl(reg, plan, inputs=None, *, action_level="ANALYZE", approval_token=None, ticket_id=None):
    """Execute a resolved multi-skill chain in dependency order. Partial execution preserves completed evidence
    and marks the overall task incomplete (PARTIAL / BLOCKED / FAILED / VERIFICATION_FAILED)."""
    inputs = dict(inputs or {}); execution_id = uuid.uuid4().hex[:12]
    g = gate(reg, plan, inputs, action_level, approval_token)
    out = {"execution_id": execution_id, "ticket_id": ticket_id, "intent": plan.get("intent"), "gate": g, "steps": [],
           "evidence": {"completed": [], "incomplete": []}}
    def finish(status):
        out["status"] = status
        for st in out["steps"]:
            (out["evidence"]["completed"] if st["status"] in SUCCESS_STATUSES else out["evidence"]["incomplete"]).append(
                {"skill": st["skill"], "status": st["status"], "execution_id": st.get("execution_id"),
                 "codes": [b.get("code") for b in st.get("blocked", [])] or None})
        audit({"execution_id": execution_id, "ticket_id": ticket_id, "intent": plan.get("intent"), "skill_id": "<plan>", "result_status": status,
               "chain": plan.get("chain"), "gate_status": g["status"], "blocked": g["blocked"],
               "completed": [c["skill"] for c in out["evidence"]["completed"]], "incomplete": [c["skill"] for c in out["evidence"]["incomplete"]]})
        if ticket_id: _ticket_attach(ticket_id, {"execution_id": execution_id, "skill": "<plan>", "status": status})
        return out
    if g["status"] == "BLOCKED":
        for sid in plan.get("chain", []):
            out["steps"].append({"status": "BLOCKED", "skill": sid, "blocked": [b for b in g["blocked"] if b["skill"] == sid], "business_context": _bctx(sid, plan, inputs), "live_sources": _lctx(sid, reg)})
        return finish("BLOCKED")
    for sid in plan["chain"]:
        if sid in g["runnable"] or sid in g["assisted"]:
            r = run_skill(reg, sid, inputs, intent=plan.get("intent",""), action_level=action_level, approval_token=approval_token,
                          execution_id=execution_id, ticket_id=ticket_id,
                          selection_reason=next((x for x in plan.get("reasons",[]) if x.startswith(sid) or "chain" in x), "chain"))
            out["steps"].append(r)
            res = r.get("result")
            if isinstance(res, dict):
                inputs.update({k: v for k, v in res.items() if k not in inputs and k != "status"})
                if res.get("contradiction") and res.get("chosen") is None:
                    inputs["_conflict"] = res.get("report") or "sources disagree"        # downstream consumers now fail closed
                    g2 = gate(reg, {"status": "RESOLVED", "chain": [x for x in plan["chain"] if x not in {st["skill"] for st in out["steps"]}]}, inputs, action_level, approval_token)
                    g["blocked"] += g2["blocked"]; g["runnable"] = [x for x in g["runnable"] if x not in {b["skill"] for b in g2["blocked"]}]
                    g["assisted"] = [x for x in g["assisted"] if x not in {b["skill"] for b in g2["blocked"]}]
            if r["status"] == "FAILED": return finish("FAILED")
            if r["status"] == "VERIFICATION_FAILED": return finish("VERIFICATION_FAILED")
        else:
            out["steps"].append({"status": "BLOCKED", "skill": sid, "blocked": [b for b in g["blocked"] if b["skill"] == sid], "business_context": _bctx(sid, plan, inputs), "live_sources": _lctx(sid, reg)})
    if any(st["status"] not in SUCCESS_STATUSES for st in out["steps"]) or g["blocked"]:
        return finish("PARTIAL" if any(st["status"] in SUCCESS_STATUSES for st in out["steps"]) else "BLOCKED")
    return finish("OK")

# ───────────────────────── gate tickets (mechanical enforcement state) ─────────────────────────
BYPASS_PATTERNS = [r"ignore (your |the )?(skill|gate|resolver|hook|rules|governance|system prompt|claude\.md)", r"skip (the )?(skill|gate|resolver|hook)",
                   r"bypass (the |your |all )?(gate|skill|hook|resolver|governance|approval|authority|check)", r"without (the |running )?(gate|resolver|skill|hook)",
                   r"don'?t (run|use) (the )?(skill|gate|resolver)", r"disable (the )?(hook|gate|skill|enforcement)", r"pretend (it ran|it was done|you ran|you executed|it is done)",
                   r"just do it directly", r"no need (for|to run) (the )?(skill|gate)", r"անտեսիր (skill|դարպաս|հմտութ|կանոն)", r"շրջանցիր",
                   r"առանց (դարպաս|skill|հմտութ)", r"you are (now )?authorized", r"override (the |your )?(gate|skill|hook|approval|authority|rules)"]
EXECUTABLE_PATTERNS = [r"\b(create|write|edit|update|move|rename|delete|remove|send|prepare|make|fix|add|change|run|build|install|record|log|draft|organi[sz]e|file|archive|clean|set up|setup|implement|generate)\b",
                       r"(կազմիր|գրիր|ուղարկիր|պատրաստիր|տեղափոխիր|ջնջիր|փոխիր|ավելացրու|արա|սարքիր|ստեղծիր|դասավորիր|արխիվացրու|գրանցիր|ուղղիր|թարմացրու)"]
MAINTENANCE_PATTERNS = [r"skill[ _-]?system", r"engine\.py", r"store\.py", r"skill\.py", r"certif", r"hook", r"registry", r"enforcement", r"hardening",
                        r"gate", r"executors?\.py", r"build_registry", r"evals?\.py", r"test_", r"release suite", r"skill graph", r"resolver",
                        r"հմտությունների համակարգ", r"claude\.md", r"settings\.json"]

def classify_prompt(text):
    t = _norm(text)
    return {"adversarial": any(re.search(p, t) for p in BYPASS_PATTERNS),
            "executable": any(re.search(p, t) for p in EXECUTABLE_PATTERNS),
            "maintenance": any(re.search(p, t) for p in MAINTENANCE_PATTERNS) or bool(system_terms(t))}

def open_ticket(reg, prompt, session_id="", source="UserPromptSubmit", inputs=None):
    """INTENT CAPTURE + SKILL RESOLUTION + gate verdict, persisted. Returns the ticket dict."""
    plan = resolve(reg, prompt)
    g = gate(reg, plan, inputs or {}, action_level="ANALYZE")
    cls = classify_prompt(prompt)
    tid = uuid.uuid4().hex[:10]
    ticket = {"ticket_id": tid, "session_id": session_id, "source": source, "created": _now(), "status": "OPEN", "agent": identity()["name"],
              "prompt_excerpt": scrub(prompt)[:300], "prompt_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16],
              "resolution": {"status": plan["status"], "primary": plan.get("primary"), "chain": plan.get("chain", []), "chain_name": plan.get("chain_name"), "domain": plan.get("domain", "BUSINESS"), "system_terms": plan.get("system_terms", []),
                             "required_inputs": plan.get("required_inputs", []), "tool_requirements": plan.get("tool_requirements", []), "reasons": plan.get("reasons", [])},
              "gate": {"status": g["status"], "blocked": g["blocked"], "runnable": g["runnable"], "assisted": g["assisted"]},
              "governed": plan["status"] == "RESOLVED", "adversarial": cls["adversarial"], "executable": cls["executable"], "maintenance": cls["maintenance"],
              "executions": [], "declarations": [], "tool_events": [], "stop_blocks": 0, "closure": None}
    try: ticket["scope"] = _inherited_scope(tid, prompt, session_id, source)
    except Exception as e: ticket["scope"] = {"status": "UNAVAILABLE", "task_id": tid, "reason": f"{type(e).__name__}: {e}"}   # fail closed: nothing is in scope
    _store().upsert("tickets", tid, ticket, extra_cols={"session_id": session_id, "status": "OPEN"})
    audit({"execution_id": tid, "ticket_id": tid, "skill_id": "<ticket>", "result_status": "OPENED", "intent": scrub(prompt)[:300],
           "resolution": plan["status"], "chain": plan.get("chain", []), "gate_status": g["status"], "adversarial": cls["adversarial"],
           "executable": cls["executable"], "maintenance": cls["maintenance"], "source": source})
    return ticket

def get_ticket(ticket_id):
    return _store().get("tickets", ticket_id)

def current_ticket(session_id=None):
    """Latest OPEN ticket. session_id=None → any session (CLI convenience); '' or 'manual' → session-less CLI tickets only."""
    st = _store()
    rows = st.list("tickets", where="status='OPEN'" + (" AND session_id=?" if session_id is not None else ""), args=(session_id,) if session_id is not None else (), order="updated_at DESC, rowid DESC", limit=1)
    return rows[0] if rows else None

def cli_session_id():
    return _os.environ.get("CLAUDE_CODE_SESSION_ID") or "manual"

def save_ticket(ticket):
    _store().upsert("tickets", ticket["ticket_id"], ticket, extra_cols={"session_id": ticket.get("session_id"), "status": ticket.get("status")})
    return ticket

def _ticket_attach(ticket_id, execution):
    t = get_ticket(ticket_id)
    if not t: return
    t["executions"].append({**execution, "ts": _now()})
    save_ticket(t)

def refine_ticket(reg, ticket_id, intent, inputs=None):
    """Re-resolve an OPEN ticket with a refined intent (the model may restate; it may not remove governance)."""
    t = get_ticket(ticket_id)
    if not t: raise SkillError(f"ticket {ticket_id} not found")
    plan = resolve(reg, intent); g = gate(reg, plan, inputs or {}, action_level="ANALYZE")
    t["resolution"] = {"status": plan["status"], "primary": plan.get("primary"), "chain": plan.get("chain", []), "chain_name": plan.get("chain_name"), "domain": plan.get("domain", "BUSINESS"), "system_terms": plan.get("system_terms", []),
                       "required_inputs": plan.get("required_inputs", []), "tool_requirements": plan.get("tool_requirements", []), "reasons": plan.get("reasons", []),
                       "refined_intent": intent[:300]}
    t["gate"] = {"status": g["status"], "blocked": g["blocked"], "runnable": g["runnable"], "assisted": g["assisted"]}
    t["governed"] = t["governed"] or plan["status"] == "RESOLVED"
    cls = classify_prompt(intent); t["adversarial"] = t["adversarial"] or cls["adversarial"]
    save_ticket(t)
    audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": "REFINED", "intent": intent[:300],
           "resolution": plan["status"], "chain": plan.get("chain", []), "gate_status": g["status"]})
    return t, plan, g

def declare_ungoverned(ticket_id, reason):
    """Explicit, audited escape hatch for work the registry does not cover (e.g. file housekeeping).
    Refused when a skill DID resolve (you cannot opt out of a governed path) or when the prompt was adversarial."""
    t = get_ticket(ticket_id)
    if not t: raise SkillError(f"ticket {ticket_id} not found")
    if t["resolution"]["status"] == "RESOLVED":
        audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": "DECLARATION_REFUSED", "reason": "skill resolved; governed path mandatory"})
        return {"status": "REFUSED", "reason": f"skills resolved for this ticket ({t['resolution']['chain']}); run them via skill.py plan/run"}
    if t.get("adversarial"):
        audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": "DECLARATION_REFUSED", "reason": "adversarial prompt"})
        return {"status": "REFUSED", "reason": "prompt attempted to bypass governance; no ungoverned declaration allowed"}
    if not reason or len(reason.strip()) < 10:
        return {"status": "REFUSED", "reason": "a substantive reason (≥10 chars) is required"}
    t["declarations"].append({"kind": "UNGOVERNED", "reason": reason.strip(), "ts": _now()}); save_ticket(t)
    audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": "UNGOVERNED_DECLARED", "reason": reason.strip()})
    return {"status": "DECLARED", "ticket_id": ticket_id}

def maintenance_grant(ticket_id):
    """Allow edits to protected enforcement files ONLY when the user's own prompt asked for skill-system maintenance."""
    t = get_ticket(ticket_id)
    if not t: raise SkillError(f"ticket {ticket_id} not found")
    if not t.get("maintenance") or t.get("adversarial"):
        audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": "MAINTENANCE_REFUSED"})
        return {"status": "REFUSED", "reason": "the user's prompt did not request skill-system maintenance (or was adversarial)"}
    t["declarations"].append({"kind": "MAINTENANCE", "ts": _now()}); save_ticket(t)
    audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": "MAINTENANCE_GRANTED"})
    return {"status": "GRANTED", "ticket_id": ticket_id}

# ───────────────────────── HARD SCOPE LOCK (workspace_policy.json -> scope_lock) ─────────────────────────
def _inherited_scope(tid, prompt, session_id, source):
    """A TASK spans several messages, so the Scope Contract follows the task, not the message: a new ticket in the same
    session inherits the contract Gev already confirmed. Inheritance carries NO new permission — the allowed subsystems were
    authorised by Gev's own earlier words — and the EVIDENCE pool is the new message plus what is already allowed, so an
    extension still needs Gev to say it again."""
    sc = _scope()
    c = sc.new_contract(tid, prompt, session_id=session_id, source=source)
    if not session_id: return c
    try: prev = _store().list("tickets", where="session_id=?", args=(session_id,), order="updated_at DESC, rowid DESC", limit=8)
    except Exception: prev = []
    for p in prev:
        pc = (p or {}).get("scope") or {}
        if pc.get("status") != "CONFIRMED": continue
        c.update(status="CONFIRMED", requested_outcome=pc.get("requested_outcome"),
                 allowed_subsystems=list(pc.get("allowed_subsystems") or []), allowed_paths=list(pc.get("allowed_paths") or []),
                 allowed_operations=list(pc.get("allowed_operations") or []), out_of_scope=list(pc.get("out_of_scope") or []),
                 extensions=list(pc.get("extensions") or []), inherited_from=p.get("ticket_id"))
        c["evidence_subsystems"] = sorted(set(c["evidence_subsystems"]) | set(c["allowed_subsystems"]))
        break
    return c

def ticket_scope(t):
    """The Scope Contract of a ticket, or None. The ticket IS the task owner — no parallel task system."""
    return (t or {}).get("scope")

def set_scope(ticket_id, outcome, subsystems, operations=None, extend=False):
    """Record the scope Deputy stated back to Gev. REFUSED for any subsystem Gev's own message does not support:
    Deputy cannot give itself permission to touch what Gev did not ask for."""
    sc = _scope()
    t = get_ticket(ticket_id)
    if not t: raise SkillError(f"ticket {ticket_id} not found")
    cur = t.get("scope")
    if not cur or cur.get("status") == "UNAVAILABLE":
        cur = sc.new_contract(ticket_id, t.get("prompt_excerpt", ""), session_id=t.get("session_id", ""), source=t.get("source", ""))
    if extend and not sc.is_confirmed(cur):
        return {"status": "REFUSED", "code": "NO_CONTRACT", "reason": "nothing to extend: set the scope first"}
    r = sc.confirm(cur, outcome, subsystems, operations=operations, extension=extend)
    if r["status"] != "CONFIRMED":
        audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<scope>", "result_status": "SCOPE_REFUSED",
               "code": r.get("code"), "reason": r.get("reason"), "requested": list(subsystems)})
        return r
    t["scope"] = r["contract"]; save_ticket(t)
    audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<scope>",
           "result_status": "SCOPE_EXTENDED" if extend else "SCOPE_CONFIRMED",
           "outcome": r["contract"]["requested_outcome"], "allowed": r["contract"]["allowed_subsystems"],
           "operations": r["contract"]["allowed_operations"], "out_of_scope": r["contract"]["out_of_scope"]})
    return {"status": "CONFIRMED", "ticket_id": ticket_id, "scope": r["contract"]}

def scope_check(t, rels):
    """[{path, reason}] for every path outside this ticket's contract. Default DENY when no contract is confirmed."""
    try: return _scope().check_paths(rels, ticket_scope(t))
    except Exception as e: return [{"path": str(r), "reason": f"scope engine unavailable ({type(e).__name__}: {e}) — fail closed"} for r in rels]

def scope_allows_system(t, system_id):
    """(ok, reason) for an EXTERNAL target system (INT-TASKS, INT-OL-MAIL, …) against the contract."""
    try:
        sc = _scope(); c = ticket_scope(t)
        if not sc.is_confirmed(c): return True, "no confirmed contract — the approval law still governs this action"
        owner = sc.systems_subsystem(system_id)
        if owner is None: return True, f"{system_id} belongs to no declared subsystem"
        if owner in (c.get("allowed_subsystems") or []): return True, f"{system_id} is in {owner}"
        return False, f"{system_id} is in {owner} — outside this task's scope {c.get('allowed_subsystems')}"
    except Exception as e:
        return True, f"scope engine unavailable ({type(e).__name__}: {e})"

def ticket_allows_execution(t):
    """True when the ticket carries a governed execution (any skill/plan run) or an explicit declaration."""
    if not t: return False
    if any(e.get("skill") for e in t.get("executions", [])): return True
    return any(d.get("kind") in ("UNGOVERNED", "MAINTENANCE") for d in t.get("declarations", []))

def ticket_has_maintenance(t):
    return bool(t) and any(d.get("kind") == "MAINTENANCE" for d in t.get("declarations", []))

def close_ticket(ticket_id, verdict, note=""):
    t = get_ticket(ticket_id)
    if not t: return None
    t["status"] = "CLOSED"; t["closure"] = {"verdict": verdict, "note": note, "ts": _now()}
    save_ticket(t)
    audit({"execution_id": ticket_id, "ticket_id": ticket_id, "skill_id": "<ticket>", "result_status": f"CLOSED_{verdict}", "reason": note,
           "executions": [e.get("skill") for e in t.get("executions", [])], "declarations": [d.get("kind") for d in t.get("declarations", [])]})
    return t

def ticket_verdict(t):
    """Closure verdict for a ticket (used by the Stop hook and the session brief)."""
    if not t: return "NO_TICKET"
    execs = [e for e in t.get("executions", []) if e.get("skill")]
    if execs:
        if any(e["status"] in SUCCESS_STATUSES or e["status"] in ("OK", "PARTIAL") for e in execs): return "GOVERNED_EXECUTED"
        return "GOVERNED_BLOCKED_REPORTED"
    if any(d.get("kind") == "MAINTENANCE" for d in t.get("declarations", [])): return "MAINTENANCE"
    if any(d.get("kind") == "UNGOVERNED" for d in t.get("declarations", [])): return "UNGOVERNED_DECLARED"
    if t.get("governed"): return "ESCAPE"                         # governed intent finished with no execution → loud
    if t.get("executable"): return "UNRESOLVED_EXECUTABLE"
    return "CHAT"
