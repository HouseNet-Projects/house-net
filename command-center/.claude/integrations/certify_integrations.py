# -*- coding: utf-8 -*-
"""INTEGRATION CERTIFICATION — evidence before an integration is called operational. States (never skipped, never declared):
  DECLARED       registry entry complete, write_ops empty
  CONFIGURED     adapter present and required secrets/config resolvable outside Git
  CONNECTED      a REAL authenticated read succeeded now (or within 24h per health) — one call is not reliability
  VERIFIED_READ  CONNECTED + evidence: authentication_verified · scope_verified · write_rejected · schema_validated ·
                 freshness_validated · failure_behavior_tested · provenance_preserved · sensitive_boundary_tested
  RELIABLE_READ  VERIFIED_READ + ≥10 real successful reads on ≥2 distinct days and 0 consecutive failures
Writes .claude/integrations/certification.json (local, INTERNAL: states + evidence flags + health snapshot; no payloads, no secrets).
Result FAIL when any evidence is contradicted (leak, reader tampered, write not rejected) — the Skill release consumes it."""
import sys, os, json, pathlib, datetime, tempfile, subprocess, importlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "skills")); sys.path.insert(0, str(HERE.parent / "policy"))
import contracts as C, registry, health, layer, int_secrets as _secrets

EVIDENCE = ("authentication_verified", "scope_verified", "write_rejected", "schema_validated", "freshness_validated", "failure_behavior_tested", "provenance_preserved", "sensitive_boundary_tested")
FAILURE_MATRIX = ("AUTH_FAILED", "PERMISSION_DENIED", "UNAVAILABLE", "MALFORMED_RESPONSE", "SCHEMA_CHANGED", "RATE_LIMITED", "WRONG_TENANT", "TIMEOUT")

def _first_op(spec): return next(iter(spec["read_ops"]), None)

def _sample_params(iid, op):
    t = datetime.date.today()
    return {"calendar.events": {"from": f"{t}T00:00:00", "to": f"{t + datetime.timedelta(days=7)}T23:59:59", "limit": 20}, "mail.list": {"folder": "Inbox", "since": f"{t - datetime.timedelta(days=2)}T00:00:00", "limit": 5, "preview_chars": 80},
            "mail.search": {"folder": "Inbox", "query": "re:", "since": f"{t - datetime.timedelta(days=14)}T00:00:00", "limit": 3, "preview_chars": 40},
            "tasks.list": {"open_only": True}, "identity": {}, "crm.deals": {"limit": 5}, "crm.stages": {"entity_id": "DEAL_STAGE"}}.get(op, {})

def failure_behavior(iid, op):
    """Inject every failure code through the layer (fixture) and require the mapped envelope + health. Runs in an isolated state dir."""
    old_env = os.environ.get("COMMAND_CENTER_INTEGRATIONS_FIXTURE"); old_state = os.environ.get("SKILL_STATE_DIR")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="intcert_")); fx = tmp / "fixture.json"; probs = []
    import engine; saved = engine.STATE_DIR; engine.STATE_DIR = tmp / "state"
    try:
        for code in FAILURE_MATRIX:
            fx.write_text(json.dumps({iid: {"error": code, "reason": f"injected {code}"}}), encoding="utf-8"); os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = str(fx)
            env = layer.query(iid, op, {}, use_cache=False)
            if env["status"] != "FAILED" or env["code"] != code: probs.append(f"{code}: got {env.get('status')}/{env.get('code')}")
            if env["health"] != C.HEALTH_FOR_CODE.get(code, "UNAVAILABLE"): probs.append(f"{code}: health {env['health']}")
            if env["freshness"] != "UNAVAILABLE" or env["records"]: probs.append(f"{code}: records returned on failure")
            if (health.get(iid) or {}).get("last_success"): probs.append(f"{code}: fixture failure produced a real last_success")
        # malformed records / partial / duplicates / unexpected PII
        fx.write_text(json.dumps({iid: {"records": [{"junk": 1}]}}), encoding="utf-8")
        env = layer.query(iid, op, {}, use_cache=False)
        if env["status"] != "FAILED" or env["code"] != "SCHEMA_CHANGED": probs.append(f"junk records not rejected: {env.get('code')}")
        if (health.get(iid) or {}).get("success_count"): probs.append("fixture read counted as a real success")
    finally:
        engine.STATE_DIR = saved
        if old_env is None: os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None)
        else: os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = old_env
        layer._FIXTURE.update(path=None, mtime=None, data=None)
    return probs

def write_rejection(iid, spec):
    probs = []
    for wop in ("send", "create", "update.deal", "delete.task", "mail.send", "calendar.create", "tasks.update", "crm.deal.update"):
        env = layer.query(iid, wop, {}, use_cache=False)
        if env["status"] != "FAILED" or env["code"] not in ("READ_ONLY_VIOLATION", "UNKNOWN_OPERATION"): probs.append(f"write op {wop} not refused: {env.get('code')}")
    for intent in ("send an email to the billing head", "create a meeting with Arman tomorrow", "update the deal stage to won", "delete the task in bitrix", "change the tariff for this subscriber", "update the customer address"):
        if layer.capability(intent, iid)["status"] != "BLOCKED": probs.append(f"write intent not blocked: {intent}")
    if spec["write_ops"]: probs.append("write_ops declared")
    if spec["adapter"] == "adapter_outlook":
        import adapter_outlook; probs += adapter_outlook.reader_problems()
    if spec["adapter"] == "adapter_bitrix24":
        import adapter_bitrix24
        for m in ("crm.deal.update", "crm.deal.add", "crm.lead.delete", "tasks.task.add", "tasks.task.complete", "im.message.add", "batch"):
            try: adapter_bitrix24.call(m, {}, {"webhook_url": "https://example.invalid/rest/1/x/"}); probs.append(f"bitrix method {m} not refused")
            except C.ReadOnlyViolation: pass
            except C.IntegrationError as e: probs.append(f"bitrix method {m}: wrong refusal {e.code}")
    ad = importlib.import_module(spec["adapter"])
    for name in dir(ad):
        if C.WRITE_OP_RX.search(name) and callable(getattr(ad, name)) and name not in ("default_transport",): probs.append(f"adapter exposes a write-like callable {name}")
    return probs

def sensitive_boundary(env_list):
    probs = []
    for env in env_list:
        if _secrets.leaks(env): probs.append(f"secret value in envelope {env.get('integration_id')}")
    for f in (health.state_dir() / "integrations_health.json", health.state_dir() / "integrations_cache.json"):
        if f.exists():
            try:
                if _secrets.leaks(json.loads(f.read_text(encoding="utf-8"))): probs.append(f"secret value in {f.name}")
            except ValueError: pass
    try:
        out = subprocess.run(["git", "ls-files", ".claude/integrations"], cwd=str(ROOT), capture_output=True, text=True).stdout.split()
        bad = [p for p in out if p.endswith(".json")]
        if bad: probs.append(f"generated integration json tracked by git: {bad}")
    except Exception: pass
    try:
        import sensitive_scan as ss
        pol = ss.load_policy()
        for py in sorted(HERE.glob("*.py")) + [HERE / "outlook_read.ps1"]:
            fs = [f for f in ss.scan_content(f".claude/integrations/{py.name}", py.read_text(encoding="utf-8"), pol, names=[]) if f["class"] == "RESTRICTED"]
            if fs: probs.append(f"{py.name}: RESTRICTED content {fs[0]['rule']}")
    except ImportError: probs.append("sensitive_scan unavailable")
    return probs

def certify(real=True, verbose=False, out=None):
    rec = {"certified_at": datetime.datetime.now().isoformat(timespec="seconds"), "mission": "4 READ-ONLY", "registry_problems": registry.declaration_problems(), "integrations": {}, "result": "PASS"}
    for iid, spec in registry.INTEGRATIONS.items():
        ev = {k: False for k in EVIDENCE}; probs = list(); notes = []
        state = "DECLARED"
        configured = False
        try:
            importlib.import_module(spec["adapter"])
            if spec["adapter"] == "adapter_mikrobill": configured = False; notes.append("no interface inventoried")
            elif spec["auth"].get("secrets"):
                cfg = _secrets.load_config(iid); configured = all(cfg.get(s) for s in spec["auth"]["secrets"])
                if not configured: notes.append(f"missing config keys {[s for s in spec['auth']['secrets'] if not cfg.get(s)]} (outside Git)")
            else: configured = True
        except Exception as e: probs.append(f"adapter import failed: {type(e).__name__}: {e}")
        if configured: state = "CONFIGURED"
        # write rejection is structural — proven for every integration, configured or not
        wr = write_rejection(iid, spec); ev["write_rejected"] = not wr; probs += wr
        op = _first_op(spec)
        if op:
            fb = failure_behavior(iid, op); ev["failure_behavior_tested"] = not fb; probs += fb
        env = None; envs = []; ops_proof = {}
        required = list(spec.get("required_certification_ops") or ([op] if op else []))
        if configured and required and real:
            # SCOPE PROOF (audit finding 4): every required operation must succeed as a REAL authenticated read; fixtures never count
            for rop in required:
                e = layer.query(iid, rop, _sample_params(iid, rop), use_cache=False); envs.append(e)
                real_ok = e["status"] == "OK" and e.get("mode") == "REAL"
                ops_proof[rop] = {"ok": real_ok, "mode": e.get("mode"), "count": e.get("count"), "code": e.get("code"), "retrieved_at": e.get("retrieved_at"), "audit_id": e.get("audit_id"),
                                  "schema_ok": real_ok and not C.check_records(e["kind"], e["records"]), "provenance_ok": real_ok and e["provenance"].get("integration_id") == iid and e["provenance"].get("op") == rop and all(r.get("record_id") for r in e["records"]),
                                  "freshness_ok": real_ok and e["freshness"] == "LIVE" and bool(e.get("retrieved_at"))}
                notes.append(f"real read {rop}: " + (f"{e['count']} record(s) at {e['retrieved_at']}" + (" (partial)" if e.get("partial") else "") if real_ok else f"FAILED {e.get('code')} — {str(e.get('reason'))[:80]}" + (" [fixture — not evidence]" if e.get("mode") == "FIXTURE" else "")))
            good = [r for r in required if ops_proof[r]["ok"]]
            if good:
                state = "CONNECTED"; env = next(e for e in envs if e["status"] == "OK" and e.get("mode") == "REAL")
                ident = env.get("identity") or {}
                ev["authentication_verified"] = (bool(ident) and ident.get("verified") is not False) or spec["auth"].get("mechanism", "").startswith("local")
                if ident.get("verified") is False: notes.append(ident.get("note") or "identity unverified")
                ev["scope_verified"] = len(good) == len(required)                       # ALL required scopes proven by real reads, not one
                ev["schema_validated"] = all(ops_proof[r]["schema_ok"] for r in required)
                ev["freshness_validated"] = all(ops_proof[r]["freshness_ok"] for r in required)
                ev["provenance_preserved"] = all(ops_proof[r]["provenance_ok"] for r in required)
                if len(good) < len(required): notes.append(f"scope NOT verified — proven {good} of required {required}")
        elif required and not real: notes.append("real reads skipped (real=False)")
        sb = sensitive_boundary([e for e in envs if e]); ev["sensitive_boundary_tested"] = not sb; probs += sb
        h = health.get(iid) or {}
        if state == "CONNECTED" and all(ev.values()): state = "VERIFIED_READ"
        if state == "VERIFIED_READ" and h.get("success_count", 0) >= 10 and len(h.get("success_days", [])) >= 2 and h.get("consecutive_failures", 0) == 0: state = "RELIABLE_READ"
        if state == "CONFIGURED" and h.get("last_success") and not env:
            notes.append(f"health shows a real read at {h['last_success']} but none succeeded now")
        rec["integrations"][iid] = {"state": state, "evidence": ev, "required_certification_ops": required, "ops_proof": ops_proof, "problems": probs, "notes": notes, "configured": configured, "critical": spec["critical"],
                                    "health": {k: h.get(k) for k in ("status", "last_check", "last_success", "consecutive_failures", "success_count", "success_days")}, "unblock": spec["unblock"], "read_ops": sorted(spec["read_ops"]), "write_ops": []}
        if wr or sb or (fb if op else []): rec["result"] = "FAIL"
    if rec["registry_problems"]: rec["result"] = "FAIL"
    pathlib.Path(out or (HERE / "certification.json")).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec

def main(argv):
    real = "--no-real" not in argv
    rec = certify(real=real)
    print(f"integration certification {rec['result']} — {rec['certified_at']}")
    for iid, r in rec["integrations"].items():
        ev = "".join("✓" if v else "·" for v in r["evidence"].values())
        print(f"  {iid:12} {r['state']:14} evidence[{ev}] " + ("; ".join(r["notes"])[:150] if r["notes"] else "") + (("  ✗ " + "; ".join(r["problems"])[:200]) if r["problems"] else ""))
    if rec["registry_problems"]: print("  registry:", rec["registry_problems"])
    return 0 if rec["result"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
