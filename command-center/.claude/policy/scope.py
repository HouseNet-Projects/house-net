# -*- coding: utf-8 -*-
"""HARD SCOPE LOCK — the execution-authority boundary: Deputy changes ONLY what Gev's current instruction requires.

The rule lives in workspace_policy.json -> scope_lock (one policy owner, no second governance system). This module is the
engine that makes it mechanical:

  SUBSYSTEM MAP     every mutable path belongs to a named subsystem (business_workspace, skill_system, integrations, …)
  EVIDENCE          which subsystems GEV'S OWN MESSAGE actually asked for — computed from the user's prompt when the gate
                    ticket is opened; Deputy cannot add evidence afterwards, so it cannot widen its own scope
  SCOPE CONTRACT    requested outcome · allowed subsystems · allowed paths · allowed operations · out-of-scope areas ·
                    task id · provenance — stored on the gate ticket (engine.py), not in a parallel task system
  DECISION          in_scope(path) / check_paths() — DEFAULT DENY: with no confirmed contract nothing may be mutated
  GIT GATE          check_diff(): changed paths vs the contract. One out-of-scope path = HARD FAIL, so an out-of-scope
                    change cannot reach a commit, a push or a PR.

CLI
  python .claude/policy/scope.py --staged            gate the staged index (installed as the git pre-commit hook)
  python .claude/policy/scope.py --worktree          gate the whole working tree (uncommitted work)
  python .claude/policy/scope.py --range A..B        gate a commit range (pre-push)
  python .claude/policy/scope.py --show              the current contract
  python .claude/policy/scope.py --explain <path>    which subsystem a path belongs to
Exit codes: 0 in scope · 1 OUT OF SCOPE (hard fail) · 2 no contract (default DENY) · 3 engine/policy unavailable (fail closed).
"""
import sys, os, re, json, fnmatch, pathlib, subprocess, datetime

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
POLICY_PATH = HERE / "workspace_policy.json"
sys.path.insert(0, str(HERE))
import paths

CODE = "OUT_OF_SCOPE"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_DERIVED = "DERIVED"


# ───────────────────────── policy access ─────────────────────────
def load(pol=None):
    """The scope_lock section. Fails closed: no section, no scope engine."""
    if pol is None:
        pol = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    sc = pol.get("scope_lock")
    if not isinstance(sc, dict) or not sc:
        raise ScopeError("scope_lock section missing from workspace_policy.json — fail closed")
    return sc, pol


class ScopeError(Exception):
    pass


def subsystems(pol=None):
    sc, _ = load(pol)
    return sc["subsystems"]


# ───────────────────────── path → subsystem ─────────────────────────
def _match(rel, pattern):
    """`a/b/**` matches everything under a/b; anything else is an exact path or an fnmatch pattern."""
    rel = rel.replace("\\", "/").strip("/")
    pattern = pattern.replace("\\", "/").strip("/")
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return rel == base or rel.startswith(base + "/")
    return rel == pattern or fnmatch.fnmatch(rel, pattern)


def subsystems_for(rel, pol=None):
    """Every subsystem a path belongs to (a path may sit in more than one, e.g. the sensitive scanner).

    The path is normalised through the business-root resolver first, so both sides of a rename resolve to the same
    subsystem: `01_Active/X.docx` and `WORKSPACE/01_Active/X.docx` are the same material, and a diff that deletes the
    old side is not an unknown mutation surface."""
    subs = subsystems(pol)
    forms = {rel.replace("\\", "/").strip("/")}
    try: forms.add(paths.to_repo(rel))
    except Exception: pass
    return sorted(k for k, d in subs.items() if any(_match(f, p) for f in forms for p in d.get("paths", [])))


def systems_subsystem(system_id, pol=None):
    """The subsystem that owns an external system id (INT-TASKS, INT-OL-MAIL, …), or None."""
    for k, d in subsystems(pol).items():
        if system_id in (d.get("systems") or []): return k
    return None


def always_allowed(rel, pol=None):
    sc, _ = load(pol)
    return any(_match(rel, p) for p in sc.get("always_allowed", []))


# ───────────────────────── evidence (what GEV asked for) ─────────────────────────
def _evidence_hit(text, needle):
    n = needle.lower()
    if re.fullmatch(r"[a-z0-9_.\-]+", n):                       # word-ish token → require a boundary so "test" ≠ "latest"
        return re.search(r"(?<![a-z0-9_])" + re.escape(n) + r"(?![a-z0-9_])", text) is not None
    return n in text


def derive_evidence(prompt, pol=None):
    """Which subsystems and operations GEV'S OWN words support. This is the ONLY source a contract may draw from."""
    sc, pol = load(pol)
    t = re.sub(r"\s+", " ", str(prompt or "")).lower()
    subs = sorted(k for k, d in sc["subsystems"].items() if any(_evidence_hit(t, e) for e in d.get("evidence", [])))
    ops = list(sc.get("default_operations", []))
    for op, needles in (sc.get("operation_evidence") or {}).items():
        if any(_evidence_hit(t, n) for n in needles) and op not in ops: ops.append(op)
    return {"subsystems": subs, "operations": [o for o in sc["operations"] if o in ops]}


# ───────────────────────── the contract ─────────────────────────
def new_contract(task_id, prompt, *, session_id="", source="", pol=None):
    """The DERIVED contract every ticket starts with: evidence recorded, nothing allowed yet (default DENY)."""
    sc, pol = load(pol)
    ev = derive_evidence(prompt, pol)
    return {
        "status": STATUS_DERIVED,
        "task_id": task_id,
        "requested_outcome": None,
        "allowed_subsystems": [],
        "allowed_paths": [],
        "allowed_operations": [],
        "out_of_scope": sorted(sc["subsystems"]),
        "evidence_subsystems": ev["subsystems"],
        "evidence_operations": ev["operations"],
        "provenance": {"source": source, "session_id": session_id, "at": datetime.datetime.now().isoformat(timespec="seconds")},
        "extensions": [],
    }


def confirm(contract, outcome, requested, pol=None, operations=None, extension=False):
    """Bind the contract to the subsystems Deputy states back to Gev. Refuses anything Gev's own message does not support —
    this is where 'Deputy cannot widen its own scope' is mechanical rather than a promise."""
    sc, pol = load(pol)
    known = set(sc["subsystems"])
    requested = [str(r).strip() for r in requested if str(r).strip()]
    unknown = [r for r in requested if r not in known]
    if unknown:
        return {"status": "REFUSED", "code": "UNKNOWN_SUBSYSTEM", "reason": f"unknown subsystem(s) {unknown}; known: {sorted(known)}"}
    ev = set(contract.get("evidence_subsystems") or [])
    unsupported = [r for r in requested if r not in ev]
    if unsupported:
        return {"status": "REFUSED", "code": CODE,
                "reason": f"Gev's message carries no evidence for {unsupported}. Deputy may not widen its own scope — "
                          f"ask Gev, or work only inside {sorted(ev)}."}
    if not requested:
        return {"status": "REFUSED", "code": "EMPTY_SCOPE", "reason": "a scope contract must name at least one subsystem"}
    if not outcome or len(str(outcome).strip()) < 10:
        return {"status": "REFUSED", "code": "NO_OUTCOME", "reason": "state the requested outcome (>=10 chars) Gev asked for"}
    ops = [o for o in (operations or contract.get("evidence_operations") or sc["default_operations"]) if o in sc["operations"]]
    allowed = sorted(set(contract.get("allowed_subsystems", [])) | set(requested)) if extension else sorted(set(requested))
    c = dict(contract)
    c.update(status=STATUS_CONFIRMED, requested_outcome=str(outcome).strip(), allowed_subsystems=allowed,
             allowed_paths=sorted({p for k in allowed for p in sc["subsystems"][k].get("paths", [])}),
             allowed_operations=ops, out_of_scope=sorted(set(sc["subsystems"]) - set(allowed)))
    if extension:
        c["extensions"] = list(contract.get("extensions") or []) + [{"added": sorted(set(requested) - set(contract.get("allowed_subsystems", []))),
                                                                     "at": datetime.datetime.now().isoformat(timespec="seconds")}]
    return {"status": "CONFIRMED", "contract": c}


def is_confirmed(contract):
    return bool(contract) and contract.get("status") == STATUS_CONFIRMED and bool(contract.get("allowed_subsystems"))


# ───────────────────────── the decision ─────────────────────────
def in_scope(rel, contract, pol=None):
    """(ok, reason). DEFAULT DENY: no confirmed contract → nothing may be mutated."""
    rel = str(rel).replace("\\", "/").strip("/")
    sc, pol = load(pol)
    if always_allowed(rel, pol): return True, "always-allowed runtime byproduct"
    if not is_confirmed(contract):
        return False, ("no confirmed Scope Contract for this task (default DENY) — state the scope to Gev and record it: "
                       "skill.py scope set --ticket <id> --outcome \"<outcome>\" <subsystem> ...")
    owners = subsystems_for(rel, pol)
    allowed = set(contract["allowed_subsystems"])
    if not owners:
        return False, f"{rel} belongs to no declared subsystem — unknown mutation surface, fail closed"
    hit = sorted(set(owners) & allowed)
    if hit: return True, f"{rel} is in {hit[0]}"
    return False, f"{rel} is in {owners} — outside this task's scope {sorted(allowed)}"


def check_paths(rels, contract, pol=None):
    """[{path, reason}] for every path outside the contract."""
    out = []
    for rel in sorted({str(r).replace("\\", "/").strip("/") for r in rels if str(r).strip()}):
        ok, why = in_scope(rel, contract, pol)
        if not ok: out.append({"path": rel, "reason": why})
    return out


def operation_allowed(op, contract):
    return is_confirmed(contract) and op in (contract.get("allowed_operations") or [])


# ───────────────────────── shell command targets ─────────────────────────
_TOKEN = re.compile(r"\"([^\"]+)\"|'([^']+)'|(\S+)")
_HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\1\s*$", re.S | re.M)


_NOT_A_PATH = re.compile(r"[|*?<>$()\[\]!`\"']")


def command_targets(cmd, root=ROOT):
    """Best-effort repository-relative paths a shell command may WRITE.

    Deliberately conservative: a search pattern or a regular expression must never be mistaken for a file, or the gate would
    deny ordinary reading. A token counts only when it carries no shell/regex metacharacter AND either the file already exists
    or its parent directory does (which is what a real write target looks like). Anything this misses is caught by the git
    scope-diff gate, which sees the actual change rather than the command text."""
    root = pathlib.Path(root).resolve()
    cmd = _HEREDOC.sub(" ", str(cmd or ""))
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*", " ", cmd, flags=re.S)
    found = set()
    for a, b, c in _TOKEN.findall(cmd):
        tok = (a or b or c).strip().strip(",;")
        if not tok or tok.startswith("-") or _NOT_A_PATH.search(tok): continue
        tok = tok.split("=")[-1] if tok.count("=") == 1 and "/" in tok.split("=")[-1] else tok
        if not re.search(r"[/\\]", tok) and "." not in tok: continue
        p = pathlib.Path(tok)
        try: q = (p if p.is_absolute() else root / p).resolve()
        except (OSError, ValueError): continue
        try: rel = q.relative_to(root).as_posix()
        except ValueError: continue
        if rel in (".", ""): continue
        try:
            if not (q.exists() or (re.search(r"[/\\]", tok) and q.parent.is_dir())): continue    # a pattern, not a place something can be written
        except OSError: continue
        found.add(rel)
    return sorted(found)


# ───────────────────────── git gate ─────────────────────────
def _git(args, root=ROOT):
    r = subprocess.run(["git"] + list(args), cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0: raise ScopeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def changed_paths(root=ROOT, mode="staged", rng=None):
    """Repository-relative paths this commit/push/working tree would carry."""
    if mode == "staged":
        out = _git(["diff", "--cached", "--name-only", "--diff-filter=ACMRDT"], root)
    elif mode == "range":
        out = _git(["diff", "--name-only", "--diff-filter=ACMRDT", rng], root)
    else:
        out = _git(["status", "--porcelain", "--untracked-files=all"], root)
        rels = []
        for line in out.splitlines():
            if not line.strip(): continue
            p = line[3:].strip()
            rels += [x.strip().strip('"') for x in (p.split(" -> ") if " -> " in p else [p])]
        return sorted({r for r in rels if r})
    return sorted({l.strip().strip('"') for l in out.splitlines() if l.strip()})


def current_contract():
    """The Scope Contract of the OPEN gate ticket. The ticket is the task owner — there is no second task system."""
    sys.path.insert(0, str(ROOT / ".claude" / "skills"))
    import engine
    t = engine.current_ticket()
    return (t or {}).get("scope"), t


def check_diff(root=ROOT, contract=None, pol=None, mode="staged", rng=None):
    """The scope-diff gate: changed paths → subsystems → the contract. One out-of-scope path = HARD FAIL."""
    rels = changed_paths(root, mode, rng)
    violations = check_paths(rels, contract, pol)
    return {"mode": mode, "changed": rels, "violations": violations,
            "contract": {"task_id": (contract or {}).get("task_id"), "status": (contract or {}).get("status"),
                         "allowed_subsystems": (contract or {}).get("allowed_subsystems"),
                         "requested_outcome": (contract or {}).get("requested_outcome")},
            "pass": not violations}


def render(rep):
    c = rep["contract"]
    if rep["pass"]:
        return (f"✓ scope gate — {len(rep['changed'])} changed path(s), all inside "
                f"{c.get('allowed_subsystems')} (task {c.get('task_id')})")
    lines = [f"⛔ {CODE} — the change leaves the scope Gev asked for.",
             f"   task {c.get('task_id')} · scope {c.get('allowed_subsystems')} · outcome: {c.get('requested_outcome')}",
             f"   {len(rep['violations'])} out-of-scope path(s):"]
    for v in rep["violations"][:20]: lines.append(f"     ✗ {v['path']}  —  {v['reason']}")
    if len(rep["violations"]) > 20: lines.append(f"     … {len(rep['violations']) - 20} more")
    lines.append("   → roll the out-of-scope change back, or ask Gev to extend the scope explicitly. No commit, no push, no PR.")
    return "\n".join(lines)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"): print(__doc__); return 2
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else ROOT
    try:
        sc, pol = load()
    except Exception as e:
        print(f"⛔ scope policy unavailable ({type(e).__name__}: {e}) — fail closed"); return 3
    if argv[0] == "--explain":
        rel = argv[1]
        print(json.dumps({"path": rel, "subsystems": subsystems_for(rel, pol), "always_allowed": always_allowed(rel, pol)}, ensure_ascii=False, indent=1)); return 0
    try:
        contract, ticket = current_contract()
    except Exception as e:
        print(f"⛔ scope contract unreadable ({type(e).__name__}: {e}) — fail closed"); return 3
    if argv[0] == "--show":
        print(json.dumps(contract or {"status": "NONE"}, ensure_ascii=False, indent=1)); return 0 if contract else 2
    mode = {"--staged": "staged", "--worktree": "worktree", "--range": "range"}.get(argv[0])
    if not mode: print(__doc__); return 2
    rng = argv[1] if mode == "range" and len(argv) > 1 else None
    if not is_confirmed(contract):
        if not ticket:
            print("· scope gate: no open Deputy task — the change is not Deputy's (nothing to gate)"); return 0
        print(f"⛔ {CODE} — gate ticket {ticket.get('ticket_id')} has no confirmed Scope Contract (default DENY).\n"
              f"   Record what Gev asked for first: python .claude/skills/skill.py scope set --ticket {ticket.get('ticket_id')} "
              f"--outcome \"<outcome>\" <subsystem> ...")
        return 2
    try:
        rep = check_diff(root, contract, pol, mode, rng)
    except ScopeError as e:
        print(f"⛔ scope gate failed ({e}) — fail closed"); return 3
    print(render(rep))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
