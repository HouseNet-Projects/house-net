# -*- coding: utf-8 -*-
"""Skill System CLI — the ONLY sanctioned entry point for governed execution (the PreToolUse hook denies direct engine access).

  skill.py resolve [--ticket T] "<intent>"          intent → minimum skill graph + gate verdict (refines ticket T if given)
  skill.py plan    [--ticket T] "<intent>" [json]   resolve + gate + execute chain (attaches to the current open ticket by default)
  skill.py run     [--ticket T] <skill_id> [json]   execute one skill through the full pipeline
  skill.py ticket  open "<prompt>" | show [id] | current | close <id> <verdict>
  skill.py declare [--ticket T] "<reason>"          audited UNGOVERNED declaration (refused if a skill resolved / prompt adversarial)
  skill.py maintenance [--ticket T]                 grant protected-file edits (only if the USER asked for skill-system maintenance)
  skill.py scope show | set | extend | check        HARD SCOPE LOCK — the Scope Contract of the current task
      scope set    [--ticket T] --outcome "<what Gev asked for>" <subsystem> [<subsystem> ...]
      scope extend [--ticket T] --outcome "<...>"  <subsystem> ...   (only with evidence in GEV'S OWN message)
      scope check  [--staged|--worktree]                              scope-diff gate before commit/push/PR
  skill.py audit [n] | audit export <path>          hardened audit trail
  skill.py store check | recover | export <table> <path>
  skill.py certs [skill_id]                         per-skill certification status (fresh / stale / missing)
  skill.py enforcement                              enforcement status: hooks configured, open/escaped tickets
  skill.py validate | status | test | hardening | eval | certify | build | release   (release = workspace → build → certify → validate → eval)
  skill.py sync [--dry-run] [--no-push]             LIVE DATA SYNC: persist live operational data + durable state (Tasks.xlsx, Journal, durable/*)
                                                    without a rebuild/certification/release; refuses product/model/unknown changes (→ release)
json inputs may carry _action_level and _approval_token.
"""
import sys, json, pathlib, subprocess
sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()        # deterministic project interpreter (<root>/.venv)
sys.path.insert(0, str(HERE))
import engine

def _j(o): return json.dumps(o, ensure_ascii=False, indent=1, default=str)

def _opt(rest, flag):
    if flag in rest:
        i = rest.index(flag); v = rest[i + 1]; del rest[i:i + 2]; return v
    return None

def _ticket_id(rest):
    tid = _opt(rest, "--ticket")
    if tid: return tid
    t = engine.current_ticket(engine.cli_session_id()) or engine.current_ticket("manual") or engine.current_ticket()
    return t["ticket_id"] if t else None

def _levels(inputs):
    return inputs.pop("_action_level", "ANALYZE"), inputs.pop("_approval_token", None)

def main(argv):
    if not argv: print(__doc__); return 0
    cmd, rest = argv[0], list(argv[1:])
    if cmd == "build":
        return subprocess.call([sys.executable, str(HERE / "build_registry.py")], cwd=str(HERE))
    reg = engine.load_registry()

    if cmd == "validate":
        p = engine.validate_registry(reg)
        print(f"skills: {len(reg['skills'])}  problems: {len(p)}")
        for x in p: print("  ✗", x)
        return 1 if p else 0

    if cmd == "resolve":
        tid = _opt(rest, "--ticket"); intent = " ".join(rest)
        if tid:
            t, plan, g = engine.refine_ticket(reg, tid, intent)
            print(_j({"ticket": tid, "plan": plan, "gate": g})); return 0 if g["status"] != "BLOCKED" else 2
        plan = engine.resolve(reg, intent); g = engine.gate(reg, plan, {}, action_level="ANALYZE")
        print(_j({"plan": plan, "gate": g})); return 0 if g["status"] != "BLOCKED" else 2

    if cmd == "run":
        tid = _ticket_id(rest); sid = rest[0]; inputs = json.loads(rest[1]) if len(rest) > 1 else {}
        lvl, tok = _levels(inputs)
        r = engine.run_skill(reg, sid, inputs, intent=f"run {sid}", action_level=lvl, approval_token=tok, ticket_id=tid)
        print(_j(r)); return 0 if r["status"] in engine.SUCCESS_STATUSES else 2

    if cmd == "plan":
        tid = _ticket_id(rest); intent = rest[0]; inputs = json.loads(rest[1]) if len(rest) > 1 else {}
        lvl, tok = _levels(inputs)
        # Every user plan now traverses the canonical Deputy request entry; an existing ticket is reused only for context.
        if not tid:
            r = engine.run_deputy_request(reg, intent, inputs, action_level=lvl, approval_token=tok, session_id=engine.cli_session_id())
            print(_j(r)); return 0 if r["status"] in ("OK", "PARTIAL") else 2
        plan = engine.resolve(reg, intent)
        if tid:
            t = engine.get_ticket(tid)
            if t and t["resolution"]["status"] == "RESOLVED" and plan["status"] != "RESOLVED":
                plan = engine.resolve(reg, t["resolution"].get("refined_intent") or t["prompt_excerpt"])   # cannot down-route a governed ticket
        r = engine.run_plan(reg, plan, inputs, action_level=lvl, approval_token=tok, ticket_id=tid)
        print(_j(r)); return 0 if r["status"] in ("OK", "PARTIAL") else 2

    if cmd == "ticket":
        sub = rest[0] if rest else "current"
        if sub == "open":
            t = engine.open_ticket(reg, " ".join(rest[1:]), session_id=engine.cli_session_id(), source="MANUAL"); print(_j(t)); return 0
        if sub == "show":
            t = engine.get_ticket(rest[1]) if len(rest) > 1 else engine.current_ticket(); print(_j(t)); return 0 if t else 2
        if sub == "current":
            t = engine.current_ticket(); print(_j(t) if t else "no open ticket"); return 0
        if sub == "close":
            t = engine.close_ticket(rest[1], rest[2] if len(rest) > 2 else "MANUAL_CLOSE"); print(_j(t)); return 0
        print(__doc__); return 1

    if cmd == "declare":
        tid = _ticket_id(rest); reason = " ".join(rest)
        if not tid: print("no open ticket"); return 2
        r = engine.declare_ungoverned(tid, reason); print(_j(r)); return 0 if r["status"] == "DECLARED" else 2

    if cmd == "scope":
        sub = rest[0] if rest else "show"; rest = rest[1:]
        tid = _ticket_id(rest)
        if sub == "check":
            import subprocess as sp
            mode = "--staged" if "--staged" in rest else "--worktree"
            return sp.call([sys.executable, str(HERE.parent / "policy" / "scope.py"), mode], cwd=str(HERE.parent.parent))
        if sub == "show":
            t = engine.get_ticket(tid) if tid else None
            print(_j(engine.ticket_scope(t) or {"status": "NONE", "reason": "no open ticket"})); return 0 if t else 2
        if sub in ("set", "extend"):
            outcome = _opt(rest, "--outcome") or ""
            ops = (_opt(rest, "--operations") or "").replace(",", " ").split() or None
            subs = [r for r in rest if not r.startswith("--")]
            if not tid: print("no open ticket"); return 2
            r = engine.set_scope(tid, outcome, subs, operations=ops, extend=(sub == "extend"))
            print(_j(r)); return 0 if r["status"] == "CONFIRMED" else 2
        print(__doc__); return 1

    if cmd == "maintenance":
        tid = _ticket_id(rest)
        if not tid: print("no open ticket"); return 2
        r = engine.maintenance_grant(tid); print(_j(r)); return 0 if r["status"] == "GRANTED" else 2

    if cmd == "audit":
        if rest and rest[0] == "export":
            p = engine._store().export_jsonl("audit", rest[1]); print(f"exported → {p}"); return 0
        n = int(rest[0]) if rest else 20
        for rec in engine.read_audit(n):
            print(f"{rec.get('ts','')}  {str(rec.get('execution_id','')):12}  {str(rec.get('skill_id','')):28}  {str(rec.get('result_status','')):22}  {rec.get('duration_ms','')}")
        return 0

    if cmd == "store":
        st = engine._store(); sub = rest[0] if rest else "check"
        if sub == "check": r = st.check(); print(_j(r)); return 0 if r["ok"] else 2
        if sub == "recover": print(_j(st.recover(reason="cli"))); return 0
        if sub == "export": print(st.export_jsonl(rest[1], rest[2])); return 0
        print(__doc__); return 1

    if cmd == "certs":
        rows = []
        for s in reg["skills"]:
            if rest and s["skill_id"] != rest[0]: continue
            c = engine.read_certification(s["skill_id"]); fp = engine.skill_fingerprint(reg, s)
            state = ("MISSING" if not c else "CORRUPT" if c.get("result") == "CORRUPT" else "STALE" if c.get("fingerprint") != fp else c.get("result"))
            rows.append((s["skill_id"], s["declared_maturity"], s["maturity_level"], c.get("maturity_level") if c else "-", state, (c or {}).get("certified_at", "-")))
        print(f"{'skill':36} {'declared':8} {'current':8} {'certified':9} {'state':8} certified_at")
        for r in rows: print(f"{r[0]:36} {r[1]:8} {r[2]:8} {str(r[3]):9} {r[4]:8} {r[5]}")
        return 0

    if cmd == "enforcement":
        settings = json.loads((HERE.parent / "settings.json").read_text(encoding="utf-8"))
        hooks = {k: [h["command"] for grp in v for h in grp.get("hooks", [])] for k, v in settings.get("hooks", {}).items()}
        st = engine._store()
        open_t = st.list("tickets", where="status='OPEN'"); esc = [t for t in st.list("tickets") if (t.get("closure") or {}).get("verdict") == "ESCAPE"]
        print(_j({"hooks_configured": hooks, "open_tickets": [t["ticket_id"] for t in open_t], "escapes_total": len(esc),
                  "last_ticket": (st.list("tickets", order="updated_at DESC, rowid DESC", limit=1) or [None])[0]}))
        return 0

    if cmd == "status":
        from collections import Counter
        c = Counter(s["maturity_level"] for s in reg["skills"]); core = [s for s in reg["skills"] if s.get("core")]
        print(f"skills={len(reg['skills'])} (retired {len(reg.get('retired', {}))})  " + "  ".join(f"{k}={c[k]}" for k in sorted(c)))
        print(f"core={len(core)}  core L3+={sum(s['maturity_level']>='L3' for s in core)}  core L2={sum(s['maturity_level']=='L2' for s in core)}  core L1={sum(s['maturity_level']=='L1' for s in core)}")
        print("tools:", {k: v for k, v in reg["tools_available"].items()})
        return 0

    if cmd == "test":
        return subprocess.call([sys.executable, "-m", "unittest", "-v", "test_skills", "test_store", "test_failclosed", "test_enforcement", "test_workspace", "test_scope", "test_runtime", "test_business", "test_boundary", "test_integrations", "test_portability", "test_actions", "test_live_data", "test_intelligence", "test_outlook_write"], cwd=str(HERE.parent / "tests"))
    if cmd == "hardening":
        return subprocess.call([sys.executable, "-m", "unittest", "-v", "test_hardening"], cwd=str(HERE.parent / "tests"))
    if cmd == "eval":
        return subprocess.call([sys.executable, str(HERE.parent / "tests" / "evals.py")], cwd=str(HERE.parent / "tests"))
    if cmd == "certify":
        return subprocess.call([sys.executable, str(HERE / "certify.py")], cwd=str(HERE))
    if cmd == "routine":
        import routines
        name = args[0] if args else ""; r = routines.run(name, ticket_id=_opt(args, "--ticket"), from_scheduler="--from-scheduler" in args)
        print(routines.render(r) if r.get("steps") is not None else json.dumps(r, ensure_ascii=False)); return 0 if r.get("status") in ("EXECUTED", "PARTIAL") else 1
    if cmd == "readiness":
        sys.path.insert(0, str(HERE.parent / "integrations")); import readiness; print(readiness.render()); return 0
    if cmd == "sync":
        # LIVE DATA SYNC (data only): classify → export durable state → static model still certified → checksums → commit → push. Product changes are refused → release.
        return subprocess.call([sys.executable, str(HERE.parent / "runtime" / "data_sync.py")] + rest, cwd=str(HERE.parent.parent))
    if cmd == "release":
        # Controlled change management: BUILD → CERTIFY (all suites, per-skill evidence) → VALIDATE (fresh certs) → EVAL. Stops at first failure.
        biz = HERE.parent / "business"
        if (biz / "sources.json").exists():
            print("\n══════ BUSINESS MODEL CERTIFICATION ══════")
            rc = subprocess.call([sys.executable, str(biz / "certify_business.py")], cwd=str(biz))
            if rc != 0: print("\nRELEASE STOPPED at business model certification (rc={}) — rebuild: python .claude/business/build_business_model.py".format(rc)); return rc
        else: print("\n══════ BUSINESS MODEL ══════\nnot built on this machine (BUSINESS_CONTEXT_MISSING) — release continues; business queries stay BLOCKED")
        # INTEGRATION CERTIFICATION (Mission 4): evidence-based states, structural read-only proof, leak check — real reads where configured
        print("\n══════ INTEGRATION CERTIFICATION ══════")
        rc = subprocess.call([sys.executable, str(HERE.parent / "integrations" / "certify_integrations.py")], cwd=str(HERE.parent / "integrations"))
        if rc != 0: print("\nRELEASE STOPPED at integration certification (rc={}) — see .claude/integrations/certification.json".format(rc)); return rc
        # DURABILITY (Mission 4.1): export durable state, regenerate the tree manifest and refresh durable checksums so Git carries everything
        print("\n══════ DURABILITY ══════")
        for step, args in (("state export", [str(HERE.parent / "runtime" / "state_snapshot.py"), "export"]), ("tree manifest", [str(HERE.parent / "policy" / "tree_manifest.py"), "build", "--write"])):
            rc = subprocess.call([sys.executable] + args, cwd=str(HERE))
            if rc != 0: print(f"\nRELEASE STOPPED at durability step {step} (rc={rc})"); return rc
        for step, args in (("workspace", [str(HERE.parent / "policy" / "validate_workspace.py")]), ("build", [str(HERE / "build_registry.py")]), ("certify", [str(HERE / "certify.py")]),
                           ("validate", [str(HERE / "skill.py"), "validate"]), ("eval", [str(HERE.parent / "tests" / "evals.py")])):
            print(f"\n══════ {step.upper()} ══════")
            rc = subprocess.call([sys.executable] + args, cwd=str(HERE))
            if rc != 0: print(f"\nRELEASE STOPPED at {step} (rc={rc})"); return rc
        # durable checksums LAST: they must describe the tree as it will be committed (registry + certifications are rewritten by certify)
        rc = subprocess.call([sys.executable, str(HERE.parent / "policy" / "tree_manifest.py"), "checksums", "--write"], cwd=str(HERE))
        if rc != 0: print(f"\nRELEASE STOPPED at durability step checksums (rc={rc})"); return rc
        print("\nRELEASE OK — workspace contract satisfied, registry built, per-skill certified, validated, evals green, durable checksums refreshed"); return 0
    print(__doc__); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
