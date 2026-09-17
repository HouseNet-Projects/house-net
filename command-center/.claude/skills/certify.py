# -*- coding: utf-8 -*-
"""PER-SKILL evidence-based certification.

Runs every suite (unit · store · fail-closed · hardening · enforcement) and the behavioral evals, collects the
@covers mapping from each PASSING test, and writes ONE machine-verifiable record per skill:
  certifications/<skill_id>.json  {skill_id, skill_version, maturity_level (ACHIEVED), declared_maturity, tests, hardening_cases,
                                   evals, authority_tests, failure_tests, completion_verification, concurrency_tests,
                                   enforcement_tests, routing_evals, certified_at, fingerprint, core_fingerprint, result}
Maturity is COMPUTED from mapped evidence, never declared:
  L1  executor exists                               L2  L1 + ≥1 unit + ≥1 failure(BLOCKED path) + ≥1 completion(run_skill validated+verified)
  L3  L2 + ≥1 authority + (≥1 eval or ≥1 routing)   L4  L3 + ≥1 adversarial + ≥1 failure_injection + ≥1 behavioral eval
A skill with ANY mapped failing test is capped at L1 and its record says FAIL. achieved = min(declared, computed):
insufficient evidence → honest downgrade written into registry.json. engine.validate_registry() rejects records whose
fingerprint (contract ⊕ executor closure ⊕ engine/store) no longer matches — changing code or contract invalidates certification.
"""
import sys, json, io, pathlib, datetime, unittest, importlib
sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
TESTS = HERE.parent / "tests"
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()        # deterministic project interpreter (<root>/.venv)
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(TESTS))
import engine

SUITES = ["test_skills", "test_store", "test_failclosed", "test_hardening", "test_enforcement", "test_workspace", "test_scope", "test_runtime", "test_business", "test_boundary", "test_integrations", "test_portability", "test_actions", "test_live_data", "test_intelligence", "test_outlook_write", "test_channels", "test_operating_layer"]
KIND_FIELD = {"unit": "tests", "failure": "failure_tests", "adversarial": "hardening_cases", "failure_injection": "hardening_cases",
              "authority": "authority_tests", "completion": "completion_verification", "concurrency": "concurrency_tests",
              "enforcement": "enforcement_tests", "routing": "routing_evals"}

def run_suite(name):
    suite = unittest.defaultTestLoader.loadTestsFromName(name); tests = []
    def collect(s):
        for t in s:
            if isinstance(t, unittest.TestSuite): collect(t)
            else: tests.append(t)
    collect(suite)
    buf = io.StringIO(); res = unittest.TextTestRunner(stream=buf, verbosity=1).run(suite)
    failed = {t.id() for t, _ in res.failures + res.errors}
    out = []
    for t in tests:
        fn = getattr(t, t._testMethodName, None)
        out.append({"id": t.id(), "name": t._testMethodName, "suite": name, "passed": t.id() not in failed,
                    "covers": list(getattr(fn, "_covers", ())), "kinds": list(getattr(fn, "_kinds", ()))})
    return out, res, buf.getvalue()

def level_for(ev, has_executor):
    if not has_executor: return "L0"
    if ev["any_failed"]: return "L1"
    l2 = ev["tests"] and ev["failure_tests"] and ev["completion_verification"]
    if not l2: return "L1"
    l3 = ev["authority_tests"] and (ev["evals"] or ev["routing_evals"])
    if not l3: return "L2"
    l4 = ev["adversarial"] and ev["failure_injection"] and ev["evals"]
    return "L4" if l4 else "L3"

def main():
    reg_path = HERE / "registry.json"; reg = json.loads(reg_path.read_text(encoding="utf-8"))
    idx = {s["skill_id"]: s for s in reg["skills"]}; all_ids = set(idx)
    regx = engine.load_registry()
    all_tests, suite_ok = [], True
    for name in SUITES:
        tests, res, log = run_suite(name); all_tests += tests
        n_fail = len(res.failures) + len(res.errors)
        print(f"{name:18} ran={res.testsRun:3} failed={n_fail}")
        if n_fail: suite_ok = False; print(log[-2500:])
    import evals
    ev_res = evals.run_all()
    ev_pass = all(r["pass"] for k in ev_res for r in ev_res[k]); n_ev = sum(len(v) for v in ev_res.values())
    print(f"{'evals':18} ran={n_ev:3} failed={sum(1 for k in ev_res for r in ev_res[k] if not r['pass'])}")
    # per-skill evidence
    evidence = {sid: {f: [] for f in set(KIND_FIELD.values()) | {"evals", "adversarial", "failure_injection"}} | {"any_failed": False, "failed_tests": []} for sid in all_ids}
    for t in all_tests:
        targets = all_ids if "*" in t["covers"] else [c for c in t["covers"] if c in all_ids]
        for sid in targets:
            if not t["passed"]: evidence[sid]["any_failed"] = True; evidence[sid]["failed_tests"].append(t["id"]); continue
            for k in t["kinds"]:
                evidence[sid][KIND_FIELD[k]].append(t["id"])
                if k in ("adversarial", "failure_injection"): evidence[sid][k].append(t["id"])
    for kind in ("scenarios", "routing", "bypass", "boundary", "business", "integration", "hands", "management", "operating"):
        for r in ev_res[kind]:
            for sid in r.get("skills", []):
                if sid not in evidence: continue
                if not r["pass"]: evidence[sid]["any_failed"] = True; evidence[sid]["failed_tests"].append(f"eval:{r['name']}"); continue
                (evidence[sid]["routing_evals"] if kind in ("routing", "boundary") else evidence[sid]["evals"]).append(f"eval:{r['name']}")
    stamp = datetime.datetime.now().isoformat(timespec="seconds"); core = engine.core_fingerprint()
    engine.CERT_DIR.mkdir(exist_ok=True)
    for stale in engine.CERT_DIR.glob("*.json"):
        if stale.stem not in all_ids: stale.unlink()           # retired skills lose their records
    rows, downgraded, failed_skills = [], [], []
    for s in reg["skills"]:
        sid = s["skill_id"]; ev = evidence[sid]
        computed = level_for(ev, bool(s.get("executor"))); declared = s.get("declared_maturity", s["maturity_level"])
        achieved = computed if engine.MATURITY.index(computed) <= engine.MATURITY.index(declared) else declared
        result = "FAIL" if ev["any_failed"] else "PASS"
        if ev["any_failed"]: failed_skills.append(sid)
        if engine.MATURITY.index(achieved) < engine.MATURITY.index(declared): downgraded.append((sid, declared, achieved))
        s["maturity_level"] = achieved; s["last_verified"] = stamp[:10] if s.get("executor") else None
        # fingerprint against the contract as it will be persisted (maturity excluded from the hash)
        fp = engine.skill_fingerprint(regx, {**regx["_index"][sid], **{k: v for k, v in s.items() if k not in ("maturity_level",)}})
        rec = {"skill_id": sid, "skill_version": s["version"], "maturity_level": achieved, "declared_maturity": declared, "computed_maturity": computed,
               "tests": sorted(set(ev["tests"])), "failure_tests": sorted(set(ev["failure_tests"])), "hardening_cases": sorted(set(ev["hardening_cases"])),
               "adversarial": sorted(set(ev["adversarial"])), "failure_injection": sorted(set(ev["failure_injection"])),
               "authority_tests": sorted(set(ev["authority_tests"])), "completion_verification": sorted(set(ev["completion_verification"])),
               "concurrency_tests": sorted(set(ev["concurrency_tests"])), "enforcement_tests": sorted(set(ev["enforcement_tests"])),
               "evals": sorted(set(ev["evals"])), "routing_evals": sorted(set(ev["routing_evals"])), "failed_tests": ev["failed_tests"],
               "certified_at": stamp, "fingerprint": fp, "core_fingerprint": core, "result": result,
               "suites": SUITES, "audit_infrastructure": any("audit" in t for t in ev["tests"] + ev["completion_verification"]) or achieved <= "L1"}
        (engine.CERT_DIR / f"{sid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        s["certification"] = {"maturity_level": achieved, "result": result, "fingerprint": fp, "certified_at": stamp, "record": f"certifications/{sid}.json"}
        s["evidence"] = {k: len(set(ev[k])) for k in ("tests", "failure_tests", "hardening_cases", "authority_tests", "completion_verification", "evals", "routing_evals", "concurrency_tests", "enforcement_tests")}
        rows.append((sid, declared, computed, achieved, result, len(set(ev["tests"])), len(set(ev["hardening_cases"])), len(set(ev["evals"]))))
    from collections import Counter
    dist = Counter(s["maturity_level"] for s in reg["skills"])
    reg["certified"] = {"at": stamp, "suites": SUITES, "tests_run": len(all_tests), "tests_passed": sum(t["passed"] for t in all_tests), "evals_run": n_ev,
                        "evals_passed": sum(1 for k in ev_res for r in ev_res[k] if r["pass"]), "core_fingerprint": core,
                        "distribution": dict(sorted(dist.items())), "downgraded": [{"skill": a, "declared": b, "achieved": c} for a, b, c in downgraded]}
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{'skill':36} {'decl':5} {'comp':5} {'cert':5} {'res':5} unit hard eval"); print("-" * 80)
    for r in rows:
        if r[3] >= "L2" or r[1] >= "L2": print(f"{r[0]:36} {r[1]:5} {r[2]:5} {r[3]:5} {r[4]:5} {r[5]:4} {r[6]:4} {r[7]:4}")
    print("-" * 80); print("distribution:", dict(sorted(dist.items())))
    if downgraded:
        print("HONEST DOWNGRADES (declared target not evidenced):")
        for sid, d, a in downgraded: print(f"  ↓ {sid}: {d} → {a}")
    if failed_skills: print("SKILLS WITH FAILING MAPPED TESTS:", failed_skills)
    ok = suite_ok and ev_pass
    print(f"\ncertification {'OK' if ok else 'FAILED'} — {len(rows)} per-skill records written to certifications/")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
