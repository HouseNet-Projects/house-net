# -*- coding: utf-8 -*-
"""BUSINESS MODEL CERTIFICATION GATE — proves the built model is trustworthy; the Skill release consumes certification.json.

    python .claude/business/certify_business.py            → re-certifies the files in .claude/business (exit 1 on FAIL)

Checks (all must PASS): schema_valid · provenance_complete · sensitive_boundary_clean · no_history_contamination ·
ownership_constraints · conflicts_explicit · unknowns_explicit · playbook_references · kpi_references · process_references ·
source_fingerprints_current · no_restricted_in_core · versioned_core_clean (git index carries no overlay/generated files) ·
git_boundary_hooks_installed. Result carries model/schema versions, core/overlay fingerprints and the source snapshot id."""
import sys, json, pathlib, datetime, re, subprocess
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "policy"))
import bm_schema

def load_built(d=HERE):
    core = {}
    for n in bm_schema.CORE_FILES:
        p = d / f"{n}.json"
        if not p.exists(): return None, None
        core[n] = json.loads(p.read_text(encoding="utf-8"))
    ov = json.loads((d / "overlay.json").read_text(encoding="utf-8")) if (d / "overlay.json").exists() else None
    return core, ov

def certify(core, overlay, root=ROOT, d=HERE, registry=None, check_git=True):
    import build_business_model as bb
    checks = {}
    def ok(name, probs): checks[name] = {"pass": not probs, "problems": list(probs)[:12]}
    # 1 schema
    sp = []
    for n in bm_schema.CORE_FILES: sp += bm_schema.check_shape(n, core[n])
    if overlay: sp += bm_schema.check_shape("overlay", overlay)
    ok("schema_valid", sp)
    # 2–3 provenance / history / duplicates / references (builder validation, overlay names included)
    reg = registry
    if reg is None:
        rp = root / ".claude" / "skills" / "registry.json"
        reg = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else None
    vp = bb.validate(core, overlay, reg)
    ok("provenance_complete", [x for x in vp if "source ids" in x or "confidence" in x])
    ok("no_history_contamination", [x for x in vp if "historical source" in x])
    ok("ownership_constraints", [x for x in vp if x.startswith("ownership")])
    ok("playbook_references", [x for x in vp if x.startswith("playbook") or x.startswith("routine")])
    ok("kpi_references", [x for x in vp if "KPI" in x and ("process" in x or "weights" in x)])
    ok("process_references", [x for x in vp if x.startswith("target") or "duplicate" in x])
    ok("sensitive_boundary_clean", [x for x in vp if x.startswith("core boundary") or "sensitive_scan" in x])
    other = [x for x in vp if not any(k in x for k in ("source ids", "confidence", "historical source", "ownership", "playbook", "routine", "KPI", "target", "duplicate", "core boundary", "sensitive_scan"))]
    ok("other_validation", other)
    # conflicts / unknowns explicit
    cids = {c["id"] for c in core["business_model"]["conflicts"]}
    ok("conflicts_explicit", [f"conflict {c} never cited by a source or ownership entry" for c in cids if not any(c in s["conflicts"] for s in core["sources"]["sources"]) and not any(c in str(o.get("note", "")) for o in core["ownership"]["ownership"])])
    ok("unknowns_explicit", ([] if core["business_model"]["critical_unknowns"] else ["no critical unknowns recorded"]) + [f"unknown {u['id']} without source" for u in core["business_model"]["critical_unknowns"] if not u.get("src")])
    # fingerprints current
    snap = core["sources"]["source_snapshot"]; fp = []
    cur = bb.snapshot(root)
    for sid, s in snap.items():
        if s["currency"] != "CURRENT": continue
        c = cur.get(sid, {})
        if c.get("sha256") is None: fp.append(f"{sid} SOURCE_MISSING")
        elif c["sha256"] != s["sha256"]: fp.append(f"{sid} SOURCE_CHANGED")
    ok("source_fingerprints_current", fp)
    try: ok("extraction_invariants", bb.invariant_checks(root) if not fp else ["skipped: sources changed/missing"])
    except Exception as e: ok("extraction_invariants", [f"{type(e).__name__}: {e}"])
    # live registers: a STRUCTURE-scoped source is a LIVE OPERATIONAL SOURCE — it must be declared LIVE_REGISTER and bound to the
    # live integration its facts are read through (provenance/freshness live in the read layer, never in a snapshot); nothing else may use STRUCTURE scope
    lp = []
    for s in core["sources"]["sources"]:
        sc, kd = s.get("fingerprint_scope", "CONTENT"), s.get("source_kind", "EXTRACTED")
        if sc == "STRUCTURE" or kd == "LIVE_REGISTER":
            if sc != "STRUCTURE" or kd != "LIVE_REGISTER": lp.append(f"{s['source_id']}: LIVE_REGISTER ⇔ STRUCTURE scope (got kind={kd}, scope={sc})")
            li = s.get("live_integration")
            if not li: lp.append(f"{s['source_id']}: live register without live_integration"); continue
            try:
                sys.path.insert(0, str(HERE.parent / "integrations")); import registry as ir
                spec = ir.INTEGRATIONS.get(li)
                if not spec: lp.append(f"{s['source_id']}: live_integration {li} not in the integration registry")
                elif (spec.get("authority") or {}).get("business_source") != s["source_id"]: lp.append(f"{s['source_id']}: {li} does not declare business_source {s['source_id']}")
                elif not spec.get("read_ops"): lp.append(f"{s['source_id']}: {li} has no read operation — live facts unreadable")
            except Exception as e: lp.append(f"{s['source_id']}: integration registry unavailable: {type(e).__name__}: {e}")
            se = snap.get(s["source_id"], {})
            if se and se.get("scope") != "STRUCTURE": lp.append(f"{s['source_id']}: snapshot scope {se.get('scope')} ≠ STRUCTURE (rebuild the model)")
    ok("live_registers_bound", lp)
    cf = bb.fingerprint(core)
    ok("core_fingerprint_matches", [] if cf == core["sources"]["meta"]["core_fingerprint"] else [f"core fingerprint {cf} ≠ stamped {core['sources']['meta']['core_fingerprint']}"])
    if overlay:
        of = bb.fingerprint({"overlay": overlay}); ok("overlay_fingerprint_matches", [] if of == overlay["meta"]["overlay_fingerprint"] else ["overlay fingerprint drift"])
    # restricted content in core (scanner content rules)
    rp_ = []
    try:
        import sensitive_scan
        pol = sensitive_scan.load_policy()
        for n in bm_schema.CORE_FILES:
            rp_ += [f"{n}.json:{f['line']} {f['rule']} [{f['class']}]" for f in sensitive_scan.scan_content(f".claude/business/{n}.json", json.dumps(core[n], ensure_ascii=False, indent=1), pol, names=[p["name"] for p in (overlay or {}).get("persons", []) if p["id"] != "@P0"])]
        for py in sorted(d.glob("bm_*.py")) + [x for x in (d / "build_business_model.py", d / "certify_business.py", HERE / "build_business_model.py", HERE / "certify_business.py") if x.exists()]:   # authoring code lives in HERE; d may be a temp model dir
            rp_ += [f"{py.name}:{f['line']} {f['rule']} [{f['class']}]" for f in sensitive_scan.scan_content(f".claude/business/{py.name}", py.read_text(encoding='utf-8'), pol, names=[p["name"] for p in (overlay or {}).get("persons", []) if p["id"] != "@P0"])]
    except ImportError: rp_.append("sensitive_scan unavailable")
    bc = set()
    try: bc = sensitive_scan.blocking_classes(pol)
    except Exception: bc = {"RESTRICTED"}
    ok("no_restricted_in_core", [x for x in rp_ if any(f"[{c}]" in x for c in bc)])
    ok("core_uses_person_tokens", [x for x in rp_ if "person_name_from_overlay" in x])
    # git boundary: index must not carry overlay/generated files; hooks installed
    gp, hp = [], []
    if check_git and (root / ".git").exists():
        try:
            import sensitive_scan
            out = subprocess.run(["git", "ls-files", ".claude/business"], cwd=str(root), capture_output=True, text=True).stdout.split()
            pol = sensitive_scan.load_policy()
            for rel in out:
                cls, why = sensitive_scan.classify_path(rel, pol)
                if cls in sensitive_scan.blocking_classes(pol): gp.append(f"{rel} is tracked but classified {cls} (credential material)")
            if not sensitive_scan.hooks_installed(root): hp.append("pre-commit/pre-push boundary hooks not installed (run sensitive_scan.py --install-hooks)")
        except Exception as e: gp.append(f"git check failed: {e}")
    ok("versioned_core_clean", gp); ok("git_boundary_hooks_installed", hp)
    result = "PASS" if all(c["pass"] for c in checks.values()) else "FAIL"
    m = core["sources"]["meta"]
    rec = {"result": result, "certified_at": datetime.datetime.now().isoformat(timespec="seconds"), "model_version": m["model_version"], "schema_version": m["schema_version"],
           "core_fingerprint": m["core_fingerprint"], "overlay_fingerprint": (overlay or {}).get("meta", {}).get("overlay_fingerprint"), "overlay_present": bool(overlay),
           "source_snapshot_id": m["source_snapshot_id"], "business_effective_date": m["business_effective_date"], "checks": checks,
           "counts": {"sources": len(core["sources"]["sources"]), "roles": len(core["business_model"]["roles"]), "processes": len(core["processes"]["processes"]), "ownership": len(core["ownership"]["ownership"]),
                      "kpis": len(core["kpis"]["kpis"]), "targets": len(core["targets"]["targets"]), "playbooks": len(core["playbooks"]["playbooks"]), "conflicts": len(core["business_model"]["conflicts"]), "gaps": len(core["gaps"]["gaps"])}}
    return rec

def main(argv):
    core, ov = load_built()
    if core is None: print("⛔ BUSINESS MODEL NOT BUILT — run build_business_model.py (BUSINESS_CONTEXT_MISSING)"); return 2
    try:
        import sensitive_scan; sensitive_scan.install_hooks()
    except Exception: pass
    rec = certify(core, ov)
    (HERE / "certification.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"business model certification {rec['result']} — model {rec['model_version']} · schema {rec['schema_version']} · core {rec['core_fingerprint']} · overlay {rec['overlay_fingerprint'] or 'ABSENT'} · snapshot {rec['source_snapshot_id']}")
    for n, c in rec["checks"].items():
        print(f"  {'✓' if c['pass'] else '✗'} {n}" + ("" if c["pass"] else ": " + "; ".join(c["problems"][:4])))
    return 0 if rec["result"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
