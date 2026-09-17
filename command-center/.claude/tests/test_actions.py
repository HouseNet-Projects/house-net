# -*- coding: utf-8 -*-
"""CONTROLLED HANDS suite (Mission 4.2) — the ONE Action Runtime: governance (no approval → no execution; approval bound to the exact
fingerprint; single-use; expiry; batch exactness; R1/R3 never bypass), idempotency + failure (duplicates, timeout → RESULT_UNKNOWN →
reconcile first, blind retry prohibited, crash after remote success, stale conflict, provider offline/credentials/permission, audit
unavailable, verification mismatch, concurrency, partial batch, restart), verification (HTTP-200 ≠ complete), and the real Tasks.xlsx
write adapter on a TEMP COPY of the register (a local technical operation — no business system is touched by this suite)."""
import unittest, json, os, sys, pathlib, tempfile, shutil, datetime, threading
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "skills")); sys.path.insert(0, str(ROOT / ".claude" / "integrations")); sys.path.insert(0, str(ROOT / ".claude" / "policy"))
from testing import covers
import engine, executors, store, actions as A, capabilities as CAP

TMP = pathlib.Path(tempfile.mkdtemp(prefix="cchands_")); engine.STATE_DIR = TMP / "state"; store.reset()
# HARD GUARD: this suite must never touch the real register — every Tasks.xlsx write is redirected to a temp copy, and the suite verifies
# at the end that the canonical file is byte-identical to what it was at import time.
import hashlib as _hl
_REAL = ROOT / "Tasks.xlsx"; _REAL_SHA = _hl.sha256(_REAL.read_bytes()).hexdigest() if _REAL.exists() else None
_GUARD = TMP / "Tasks-guard.xlsx"
if _REAL.exists(): shutil.copy(_REAL, _GUARD)
os.environ["COMMAND_CENTER_TASKS_XLSX"] = str(_GUARD)
def tearDownModule():
    import registry; registry.INTEGRATIONS.pop("INT-FAKE", None); CAP.WRITE_OPS.pop("INT-FAKE", None); A.PROVIDER_OVERRIDES.pop("INT-FAKE", None)   # never leak the fake integration into other suites
    if _REAL_SHA and _hl.sha256(_REAL.read_bytes()).hexdigest() != _REAL_SHA: raise AssertionError("TEST SUITE MUTATED THE REAL Tasks.xlsx — forbidden")
REG = engine.load_registry()
GOV = ("authority_checking", "approval_management", "completion_verification", "audit_logging")
AR = "action_runtime"
T = datetime.date.today().isoformat()

def _req(op="tasks.create", system="INT-FAKE", params=None, oid=None, intent="create task for Arman: weekly report", effect="task exists", risk=None):
    r = A.build_request(skill_id=AR, business_intent=intent, business_domain="A_EXECUTIVE_CONTROL", target_system=system, target_operation=op, target_object_type="task", target_object_id=oid,
                        parameters=params or {"title": "Send weekly sales report", "owner": "Arman", "due": "2026-09-18", "status": "Չսկսված"}, expected_effect=effect, expected_postcondition="row read back", verification_method="read-back")
    if risk: r["risk_class"] = risk; r["authority_scope"] = A.RISK_LEVEL[risk]; r["action_fingerprint"] = A.fingerprint(r)
    return r

class FakeCap:
    """INT-FAKE capability: implemented + configured + connected so the runtime path is exercised end-to-end with a FakeProvider."""
    @staticmethod
    def install():
        CAP.WRITE_OPS["INT-FAKE"] = {op: {"risk_class": "R1", "authority_required": "EXECUTE_EXTERNAL", "idempotency_method": "key", "verification_method": "read-back", "adapter": "fake", "retry_safe_when_absent": True} for op in ("tasks.create", "tasks.update", "mail.send", "calendar.create", "calendar.update")}
        CAP.WRITE_OPS["INT-FAKE"]["billing.change"] = {"risk_class": "R3", "authority_required": "EXECUTE_MATERIAL", "idempotency_method": "key", "verification_method": "read-back", "adapter": "fake", "retry_safe_when_absent": False}
        import registry
        registry.INTEGRATIONS.setdefault("INT-FAKE", {**registry.INTEGRATIONS["INT-TASKS"], "integration_id": "INT-FAKE", "system": "Fake provider (tests)", "read_ops": {}, "required_certification_ops": [], "auth": {"mechanism": "none", "secrets": []}, "adapter": "adapter_tasks", "machine_dependency": None})
        import health; health.record("INT-FAKE", True, op="probe", mode="REAL")
def setUpModule(): FakeCap.install()      # installed only while THIS module runs (never leaks into other suites' registry checks)

def fresh(behaviour=None):
    p = A.FakeProvider(behaviour); A.PROVIDER_OVERRIDES["INT-FAKE"] = p; return p

class H01_Governance(unittest.TestCase):
    @covers(AR, *GOV, kinds=("authority", "failure", "unit"))
    def test_no_approval_no_execution_and_reads_stay_free(self):
        p = fresh(); a = A.prepare(_req(), session_id="s1")
        self.assertEqual(a["state"], "APPROVAL_REQUIRED"); self.assertIn("Nothing has been changed yet", a["card"]); self.assertEqual(p.calls, [])
        r = A.execute(a["action_id"]); self.assertEqual((r["state"], r["canonical"]), ("DENIED", "BLOCKED")); self.assertIn("NOT_APPROVED", r["codes"]); self.assertEqual(p.calls, []); self.assertFalse(r["mutation_performed"])
        # reads / local analysis remain free
        import layer; e = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=False); self.assertEqual(e["status"], "OK")
        self.assertEqual(executors.action_runtime({"text": "draft an email to Arman asking why the report is late", "session_id": "s1"}, REG["_index"][AR], REG)["provider_mutation"], False)
    @covers(AR, *GOV, kinds=("authority", "adversarial", "unit"))
    def test_approval_text_recognition(self):
        for t in ("OK", "ok", "GO", "Go.", "Արա", "Հաստատում եմ", "yes", "approved", "այո", "օք", "Օք", "գո", "օկ", "գօ", "օք."): self.assertEqual(A.classify_approval(t), "APPROVAL", t)   # Armenian-letter OK/GO added by Gev 2026-09-12
        for t in ("looks good", "sounds fine", "maybe", "ok?", "what do you think", "", "OK, what's overdue?", "I like it", "օք?", "օք լավ է", "գո ինչ կա"): self.assertNotEqual(A.classify_approval(t), "APPROVAL", t)
        for t in ("no", "cancel", "stop", "ոչ", "մի արա"): self.assertEqual(A.classify_approval(t), "REJECTION", t)
        self.assertEqual(A.classify_approval("GO, but change the deadline to Monday"), "MODIFIED"); self.assertEqual(A.classify_approval("օք, բայց ժամկետը փոխիր"), "MODIFIED")
        p = fresh(); a = A.prepare(_req(), session_id="s2")
        for t in ("looks good", "maybe", "ok?"):
            self.assertEqual(A.approve(t, session_id="s2")["status"], "NOT_APPROVED"); self.assertEqual(A.get(a["action_id"])["state"], "APPROVAL_REQUIRED")
        self.assertEqual(p.calls, [])
    @covers(AR, *GOV, kinds=("authority", "adversarial", "failure_injection"))
    def test_approval_binds_to_exact_action_and_parameter_change_invalidates(self):
        p = fresh(); a = A.prepare(_req(), session_id="s3"); b = A.prepare(_req(params={"title": "Other task", "owner": "Maga", "due": "2026-09-20"}, system="INT-FAKE"), session_id="s3b")
        ap = A.approve("GO", action_id=a["action_id"]); self.assertEqual(ap["status"], "APPROVED"); tok = ap["tokens"][0]
        r = A.execute(b["action_id"], token_id=tok["token_id"]); self.assertEqual(r["state"], "DENIED"); self.assertIn("NOT_APPROVED", r["codes"]); self.assertEqual(p.calls, [])   # A's approval cannot execute B
        # changed recipient / deadline / content / participants / owner → fingerprint differs → approval invalidated
        for change in ({"owner": "Sales Team"}, {"due": "2026-09-21"}, {"title": "Send monthly report"}, {"participants": ["Finance"]}, {"to": "sales@example.test"}):
            inv = A.invalidate_if_changed(a["action_id"], change) if A.get(a["action_id"])["state"] == "APPROVED" else {"changed": True}
            self.assertTrue(inv["changed"], change)
            self.assertNotEqual(A.fingerprint({**a["request"], "parameters": {**a["request"]["parameters"], **change}}), a["request"]["action_fingerprint"])
        self.assertEqual(A.get(a["action_id"])["state"], "REJECTED"); self.assertIn("CHANGED", A.get(a["action_id"])["codes"])
        r = A.execute(a["action_id"], token_id=tok["token_id"]); self.assertNotEqual(r["state"], "VERIFIED"); self.assertEqual(p.calls, [])
        # tampering with the stored request breaks the binding
        c = A.prepare(_req(intent="x"), session_id="s3c"); A.approve("OK", action_id=c["action_id"]); rec = A.get(c["action_id"]); rec["request"]["parameters"]["owner"] = "Somebody"; A._save(rec)
        r = A.execute(c["action_id"]); self.assertEqual(r["state"], "REJECTED"); self.assertIn("APPROVAL_MISMATCH", r["codes"]); self.assertEqual(p.calls, [])
    @covers(AR, *GOV, kinds=("authority", "failure_injection", "completion"))
    def test_replay_expiry_rejection_and_risk_classes(self):
        p = fresh(); a = A.prepare(_req(), session_id="s4"); A.approve("GO", action_id=a["action_id"])
        r = A.execute(a["action_id"]); self.assertEqual((r["state"], r["canonical"]), ("VERIFIED", "DONE")); self.assertEqual(len(p.calls), 1); self.assertTrue(A.get(a["action_id"])["approval"]["consumed"])
        r2 = A.execute(a["action_id"]); self.assertEqual(r2["state"], "VERIFIED"); self.assertEqual(len(p.calls), 1)                    # replay of a consumed approval never writes again
        e = A.prepare(_req(params={"title": "Expiring", "owner": "Arman"}), session_id="s4e"); A.approve("OK", action_id=e["action_id"]); rec = A.get(e["action_id"]); rec["approval"]["expires_at"] = "2000-01-01T00:00:00"; A._save(rec)
        r = A.execute(e["action_id"]); self.assertEqual(r["state"], "REJECTED"); self.assertIn("APPROVAL_EXPIRED", r["codes"]); self.assertEqual(len(p.calls), 1)
        j = A.prepare(_req(params={"title": "Rejected one", "owner": "Arman"}), session_id="s4j"); A.reject(j["action_id"]); r = A.execute(j["action_id"]); self.assertEqual(r["state"], "DENIED"); self.assertEqual(len(p.calls), 1)
        for risk in ("R1", "R3"):
            x = A.prepare(_req(op="billing.change" if risk == "R3" else "tasks.create", params={"title": f"risk {risk}", "owner": "Arman"}, risk=risk), session_id="s4r")
            self.assertEqual(x["state"], "APPROVAL_REQUIRED"); self.assertEqual(x["request"]["risk_class"], risk); r = A.execute(x["action_id"]); self.assertEqual(r["state"], "DENIED")     # risk never bypasses approval
        self.assertEqual(len(p.calls), 1)
    @covers(AR, *GOV, kinds=("authority", "completion", "failure"))
    def test_batch_approval_is_exact_and_partial_is_honest(self):
        p = fresh({"mail.send": {"result": "error", "reason": "smtp refused"}})
        reqs = [_req(params={"title": "Batch task", "owner": "Arman", "due": "2026-09-18"}), _req(op="calendar.create", params={"subject": "Review", "start": f"{T}T16:00:00", "end": f"{T}T17:00:00", "participants": ["Arman"]}), _req(op="mail.send", params={"to": "arman@example.test", "subject": "Report", "body": "Please send it"})]
        b = A.prepare_batch(reqs, session_id="s5"); self.assertTrue(b["all_preparable"]); self.assertIn("Step 3/3", b["card"])
        ap = A.approve("GO", batch_id=b["batch_id"]); self.assertEqual(len(ap["tokens"]), 3)
        extra = A.prepare(_req(params={"title": "Discovered while executing", "owner": "Arman"}), session_id="s5")      # a discovered write is NOT covered by the batch approval
        res = A.execute_batch(b["batch_id"]); self.assertEqual(res["state"], "PARTIAL"); self.assertEqual(res["verified"], 2); self.assertEqual([s["state"] for s in res["steps"]], ["VERIFIED", "VERIFIED", "FAILED"]); self.assertTrue(res["user_decision_required"]); self.assertIn("rollback", res)
        self.assertEqual(A.get(extra["action_id"])["state"], "APPROVAL_REQUIRED"); self.assertEqual(len([c for c in p.calls if c[0] == "tasks.create"]), 1)
    @covers(AR, *GOV, kinds=("authority", "unit"))
    def test_ambiguous_pending_target_fails_closed(self):
        fresh(); A.prepare(_req(params={"title": "A", "owner": "Arman"}), session_id="s6"); A.prepare(_req(params={"title": "B", "owner": "Arman"}), session_id="s6")
        ap = A.approve("GO", session_id="s6"); self.assertEqual(ap["status"], "NOT_APPROVED"); self.assertIn("ambiguous", ap["reason"])

class H02_IdempotencyAndFailure(unittest.TestCase):
    @covers(AR, *GOV, kinds=("failure_injection", "unit", "completion"))
    def test_duplicate_requests_never_duplicate_writes(self):
        p = fresh(); a = A.prepare(_req(params={"title": "Dup", "owner": "Arman"}), session_id="s7"); A.approve("GO", action_id=a["action_id"]); A.execute(a["action_id"])
        d = A.prepare(_req(params={"title": "Dup", "owner": "Arman"}), session_id="s7"); self.assertEqual(d["state"], "DENIED"); self.assertTrue({"DUPLICATE", "ALREADY_EXISTS"} & set(d["codes"])); self.assertEqual(len(p.calls), 1)
        m = A.prepare(_req(op="mail.send", params={"to": "a@example.test", "subject": "S", "body": "B"}), session_id="s7m"); A.approve("GO", action_id=m["action_id"]); A.execute(m["action_id"])
        m2 = A.prepare(_req(op="mail.send", params={"to": "a@example.test", "subject": "S", "body": "B"}), session_id="s7m"); self.assertEqual(m2["state"], "DENIED"); self.assertEqual(len([c for c in p.calls if c[0] == "mail.send"]), 1)
        c = A.prepare(_req(op="calendar.create", params={"subject": "Ev", "start": f"{T}T10:00:00", "end": f"{T}T11:00:00"}), session_id="s7c"); A.approve("GO", action_id=c["action_id"]); A.execute(c["action_id"])
        c2 = A.prepare(_req(op="calendar.create", params={"subject": "Ev", "start": f"{T}T10:00:00", "end": f"{T}T11:00:00"}), session_id="s7c"); self.assertEqual(c2["state"], "DENIED")
    @covers(AR, *GOV, kinds=("failure_injection", "failure", "completion"))
    def test_timeout_reconcile_first_and_blind_retry_prohibited(self):
        p = fresh({"tasks.create": {"result": "timeout", "committed": False}}); a = A.prepare(_req(params={"title": "Timeout", "owner": "Arman"}), session_id="s8"); A.approve("GO", action_id=a["action_id"])
        r = A.execute(a["action_id"]); self.assertEqual((r["state"], r["canonical"]), ("RESULT_UNKNOWN", "RESULT_UNKNOWN")); self.assertEqual(r["reconciliation"]["outcome"], "ABSENT"); self.assertTrue(r["reconciliation"]["retry_safe"])
        r2 = A.execute(a["action_id"]); self.assertEqual(r2["state"], "RESULT_UNKNOWN"); self.assertIn("RECONCILE_FIRST", r2["codes"]); self.assertEqual(len(p.calls), 1)     # no blind retry
        p.behaviour["tasks.create"] = {"result": "ok"}; r3 = A.execute(a["action_id"], retry=True); self.assertEqual(r3["state"], "VERIFIED"); self.assertEqual(len(p.calls), 2)   # explicit retry under the still-valid token, only after reconciliation proved absence
        # remote success before local persistence (crash after write): reconciliation FINDS it → VERIFIED without a second write
        p = fresh({"tasks.create": {"result": "timeout", "committed": True, "id": "remote-9"}}); b = A.prepare(_req(params={"title": "Crash", "owner": "Arman"}), session_id="s8b"); A.approve("GO", action_id=b["action_id"])
        r = A.execute(b["action_id"]); self.assertEqual(r["state"], "VERIFIED"); self.assertEqual(r["reconciliation"]["outcome"], "FOUND"); self.assertEqual(len(p.calls), 1)
        # undeterminable → stays RESULT_UNKNOWN, retry prohibited
        p = fresh({"tasks.create": {"result": "timeout"}}); c = A.prepare(_req(params={"title": "Unknown", "owner": "Arman"}), session_id="s8c"); A.approve("GO", action_id=c["action_id"])
        orig = p.find_existing; p.find_existing = lambda op, params: (_ for _ in ()).throw(RuntimeError("provider unreachable")); r = A.execute(c["action_id"]); self.assertEqual(r["state"], "RESULT_UNKNOWN"); self.assertEqual(r["reconciliation"]["outcome"], "UNDETERMINED"); self.assertFalse(r["reconciliation"]["retry_safe"])
    @covers(AR, *GOV, kinds=("failure_injection", "failure"))
    def test_stale_state_provider_failures_and_audit_unavailable(self):
        p = fresh(); p.remote["t1"] = {"op": "tasks.update", "status": "Ընթացքում", "due": "2026-09-19"}
        a = A.prepare(_req(op="tasks.update", oid="t1", params={"due": "2026-09-22"}), session_id="s9"); self.assertEqual(a["diff"], {"due": ("2026-09-19", "2026-09-22")}); A.approve("GO", action_id=a["action_id"])
        p.remote["t1"]["due"] = "2026-09-17"                                                   # another actor changed it after Gev saw the card
        r = A.execute(a["action_id"]); self.assertEqual((r["state"], r["canonical"]), ("REJECTED", "BLOCKED")); self.assertIn("STALE_CONFLICT", r["codes"]); self.assertEqual(p.calls, [])
        for beh, code in ((("error", "provider offline"), "PROVIDER_ERROR"), (("error", "credentials absent"), "PROVIDER_ERROR"), (("error", "permission denied"), "PROVIDER_ERROR")):
            p = fresh({"tasks.create": {"result": beh[0], "reason": beh[1]}}); x = A.prepare(_req(params={"title": beh[1], "owner": "Arman"}), session_id="s9x"); A.approve("GO", action_id=x["action_id"])
            r = A.execute(x["action_id"]); self.assertEqual(r["state"], "FAILED"); self.assertIn(code, r["codes"]); self.assertFalse(r["mutation_performed"])
        # audit unavailable → the material action is withheld BEFORE the provider is called
        p = fresh(); y = A.prepare(_req(params={"title": "Audit down", "owner": "Arman"}), session_id="s9y"); A.approve("GO", action_id=y["action_id"])
        orig = engine.audit; engine.audit = lambda rec: (_ for _ in ()).throw(RuntimeError("audit store offline"))
        try: r = A.execute(y["action_id"])
        finally: engine.audit = orig
        self.assertEqual(r["state"], "DENIED"); self.assertIn("AUDIT_UNAVAILABLE", r["codes"]); self.assertEqual(p.calls, [])
    @covers(AR, *GOV, kinds=("concurrency", "failure_injection"))
    def test_concurrent_execution_writes_once_and_restart_keeps_idempotency(self):
        p = fresh(); a = A.prepare(_req(params={"title": "Race", "owner": "Arman"}), session_id="s10"); A.approve("GO", action_id=a["action_id"])
        results = []; ths = [threading.Thread(target=lambda: results.append(A.execute(a["action_id"]))) for _ in range(6)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(len([c for c in p.calls if c[0] == "tasks.create"]), 1); self.assertTrue(any(r["state"] == "VERIFIED" for r in results))
        # "restart": a fresh store loaded from the durable export still knows the action → the same business action is a DUPLICATE
        import state_snapshot as ssn
        ssn.export(TMP, log=lambda *a: None); root2 = TMP / "restart"; (root2 / ".claude" / "state").mkdir(parents=True); shutil.copytree(ssn.durable_dir(TMP), root2 / ".claude" / "state" / "durable")
        saved = engine.STATE_DIR; engine.STATE_DIR = root2 / ".claude" / "state"; store.reset()
        try:
            ssn.import_(root2, log=lambda *a: None); self.assertEqual(A.get(a["action_id"])["state"], "VERIFIED")
            d = A.prepare(_req(params={"title": "Race", "owner": "Arman"}), session_id="s10"); self.assertEqual(d["state"], "DENIED"); self.assertIn("DUPLICATE", d["codes"])
        finally: engine.STATE_DIR = saved; store.reset()

class H03_Verification(unittest.TestCase):
    @covers(AR, "completion_verification", *GOV, kinds=("failure_injection", "completion", "failure"))
    def test_provider_success_is_never_completion(self):
        p = fresh({"tasks.create": {"result": "success_no_evidence"}}); a = A.prepare(_req(params={"title": "Ghost", "owner": "Arman"}), session_id="s11"); A.approve("GO", action_id=a["action_id"])
        r = A.execute(a["action_id"]); self.assertEqual((r["state"], r["canonical"]), ("EXECUTED_UNVERIFIED", "NOT DONE")); self.assertIn("VERIFICATION_MISMATCH", r["codes"]); self.assertIn("not found", r["verification"])
        p = fresh({"tasks.create": {"result": "wrong_value", "wrong": {"owner": "Maga"}}}); b = A.prepare(_req(params={"title": "Wrong owner", "owner": "Arman"}), session_id="s11b"); A.approve("GO", action_id=b["action_id"])
        r = A.execute(b["action_id"]); self.assertEqual(r["state"], "EXECUTED_UNVERIFIED"); self.assertIn("owner", r["verification"])
        p = fresh({"calendar.create": {"result": "wrong_value", "wrong": {"start": f"{T}T11:00:00"}}}); c = A.prepare(_req(op="calendar.create", params={"subject": "TZ", "start": f"{T}T15:00:00", "end": f"{T}T16:00:00"}), session_id="s11c"); A.approve("GO", action_id=c["action_id"])
        r = A.execute(c["action_id"]); self.assertEqual(r["state"], "EXECUTED_UNVERIFIED"); self.assertIn("start", r["verification"])
        p = fresh({"mail.send": {"result": "success_no_evidence"}}); m = A.prepare(_req(op="mail.send", params={"to": "x@example.test", "subject": "S", "body": "B"}), session_id="s11m"); A.approve("GO", action_id=m["action_id"])
        r = A.execute(m["action_id"]); self.assertEqual(r["state"], "EXECUTED_UNVERIFIED")
        p = fresh({"tasks.update": {"result": "wrong_value", "wrong": {"stage": "OLD"}}}); p.remote["d1"] = {"op": "tasks.update", "stage": "OLD"}; u = A.prepare(_req(op="tasks.update", oid="d1", params={"stage": "WON"}), session_id="s11u"); A.approve("GO", action_id=u["action_id"])
        r = A.execute(u["action_id"]); self.assertEqual(r["state"], "EXECUTED_UNVERIFIED")
    @covers(AR, "audit_logging", *GOV, kinds=("unit", "enforcement"))
    def test_audit_chain_is_complete_and_secretless(self):
        p = fresh(); a = A.prepare(_req(params={"title": "Audited", "owner": "Arman"}), session_id="s12"); A.approve("GO", action_id=a["action_id"]); A.execute(a["action_id"])
        recs = [r for r in engine.read_audit(200) if r.get("execution_id") == a["action_id"]]; st = [r.get("result_status") for r in recs]
        for s in ("APPROVAL_REQUIRED", "APPROVED", "EXECUTING", "EXECUTED_UNVERIFIED", "VERIFIED"): self.assertIn(s, st, st)
        self.assertTrue(any(r.get("fingerprint") for r in recs)); self.assertTrue(any(r.get("token") for r in recs)); self.assertTrue(any(r.get("approved_by") == "Gev" for r in recs))
        self.assertNotIn("recovery", json.dumps(recs).lower())

class H04_TasksWriteAdapter(unittest.TestCase):
    """The real Tasks.xlsx write path on a TEMP COPY of the register."""
    def setUp(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        self.xlsx = TMP / f"Tasks-{self._testMethodName}.xlsx"; shutil.copy(ROOT / "Tasks.xlsx", self.xlsx); A.PROVIDER_OVERRIDES.pop("INT-TASKS", None)
    def _r(self, op, params, oid=None): return A.build_request(skill_id=AR, business_intent=f"{op} test", business_domain="A_EXECUTIVE_CONTROL", target_system="INT-TASKS", target_operation=op, target_object_type="task", target_object_id=oid, parameters={**params, "register_path": str(self.xlsx)}, expected_effect="row", expected_postcondition="read-back")
    @covers(AR, "task_management", "deadline_management", *GOV, kinds=("unit", "completion", "failure"))
    def test_create_assign_close_reopen_with_readback(self):
        n0 = len(executors.load_tasks(self.xlsx))
        a = A.prepare(self._r("tasks.create", {"title": "TEST — hands certification", "owner": "Գև", "due": "2026-09-13", "status": "Չսկսված"}), session_id="x1"); self.assertEqual(a["state"], "APPROVAL_REQUIRED")
        self.assertEqual(len(executors.load_tasks(self.xlsx)), n0)                                     # prepare never writes
        A.approve("GO", action_id=a["action_id"]); r = A.execute(a["action_id"]); self.assertEqual(r["state"], "VERIFIED", r); tid = r["evidence"]["id"]
        rows = executors.load_tasks(self.xlsx); self.assertEqual(len(rows), n0 + 1); t = next(x for x in rows if x["id"] == tid); self.assertEqual((t["task"], t["owner"], t["due"].isoformat(), t["status"]), ("TEST — hands certification", "Գև", "2026-09-13", "Չսկսված"))
        self.assertTrue(r["open_loop"] and r["open_loop"].get("waiting_for"))
        d = A.prepare(self._r("tasks.create", {"title": "TEST — hands certification", "owner": "Գև", "due": "2026-09-13"}), session_id="x1"); self.assertEqual(d["state"], "DENIED"); self.assertTrue({"ALREADY_EXISTS", "DUPLICATE"} & set(d["codes"]))
        b = A.prepare(self._r("tasks.assign", {"owner": "Arman"}, oid=tid), session_id="x2"); self.assertEqual(b["diff"], {"owner": ("Գև", "Arman")}); A.approve("Արա", action_id=b["action_id"]); self.assertEqual(A.execute(b["action_id"])["state"], "VERIFIED")
        c = A.prepare(self._r("tasks.close", {"evidence": "report delivered"}, oid=tid), session_id="x3"); A.approve("OK", action_id=c["action_id"]); r = A.execute(c["action_id"]); self.assertEqual(r["state"], "VERIFIED"); self.assertEqual(next(x for x in executors.load_tasks(self.xlsx) if x["id"] == tid)["status"], "Արված")
        e = A.prepare(self._r("tasks.reopen", {}, oid=tid), session_id="x4"); A.approve("GO", action_id=e["action_id"]); self.assertEqual(A.execute(e["action_id"])["state"], "VERIFIED")
        for bad in ({"title": "No owner", "owner": ""}, {"title": "Team owner", "owner": "sales team"}):
            x = A.prepare(self._r("tasks.create", bad), session_id="x5"); A.approve("GO", action_id=x["action_id"]); r = A.execute(x["action_id"]); self.assertEqual(r["state"], "FAILED"); self.assertIn("owner", str(r["result"]))
    @covers(AR, "task_management", *GOV, kinds=("failure_injection", "failure"))
    def test_stale_row_and_locked_workbook(self):
        rows = executors.load_tasks(self.xlsx); t0 = rows[0]
        a = A.prepare(self._r("tasks.update", {"due": "2026-12-31"}, oid=t0["id"]), session_id="y1"); A.approve("GO", action_id=a["action_id"])
        import openpyxl; wb = openpyxl.load_workbook(self.xlsx); ws = wb[executors.SHEET]; ws.cell(row=t0["row"], column=executors.COL["status"], value="Սպասում"); wb.save(self.xlsx)    # another actor edits meanwhile
        r = A.execute(a["action_id"]); self.assertEqual(r["state"], "REJECTED"); self.assertIn("STALE_CONFLICT", r["codes"])
        b = A.prepare(self._r("tasks.create", {"title": "Locked", "owner": "Գև"}), session_id="y2"); A.approve("GO", action_id=b["action_id"])
        import adapter_tasks_write as W; orig = W.execute
        def locked(op, params): raise A.ProviderError("workbook locked by another program: [Errno 13]")
        W.execute = locked
        try: r = A.execute(b["action_id"])
        finally: W.execute = orig
        self.assertEqual(r["state"], "FAILED"); self.assertIn("locked", str(r["result"]))

class H05_CapabilityAndSkill(unittest.TestCase):
    @covers(AR, *GOV, kinds=("unit",))
    def test_capability_registry_is_honest(self):
        rows = {(r["integration_id"], r["operation"]): r for r in CAP.table()}
        self.assertEqual(rows[("INT-MB", "tariff.change")]["level"], "DEFERRED"); self.assertEqual(rows[("INT-MB", "tariff.change")]["risk_class"], "R3")      # deferred by Gev: still no hands, honestly labelled
        self.assertIn(rows[("INT-B24", "crm.deal.update")]["level"], ("IMPLEMENTED", "DECLARED")); self.assertTrue(all(r["gev_approval_required"] for r in rows.values() if r["read_or_write"] == "write"))
        certs = CAP._write_certs()
        for k, r in rows.items():
            if r["read_or_write"] != "write": continue
            c = certs.get(k[0], {}).get(k[1])
            if r["level"] == "VERIFIED_WRITE":                      # only a durable, Gev-approved, VERIFIED live write may certify — never a test or a code path
                self.assertIsNotNone(c, f"{k}: VERIFIED_WRITE without durable certification evidence"); self.assertTrue(c.get("action_id", "").startswith("ACT-"), k); self.assertEqual(c["evidence"].get("approved_by"), "Gev", k)
            else: self.assertFalse(c and r["runtime_available"], f"{k}: certification recorded and runtime available, yet level is {r['level']}")   # (in this suite health lives in a temp state dir → not connected)
        import adapter_outlook_write as W; self.assertEqual(W.writer_problems(), [])
    @covers(AR, *GOV, kinds=("routing", "unit"))
    def test_routing_and_executor_boundaries(self):
        for intent in ("Create a task for Arman to send the weekly report by Friday.", "Move tomorrow's Sales Review to 15:00.", "Email the sales team that the meeting moved.", "Send it.", "Close the task.", "Change the customer's tariff.", "Update this Bitrix deal.", "Cancel tomorrow's meeting."):
            self.assertIn(AR, engine.resolve(REG, intent)["chain"], intent)
        for intent in ("GO", "OK", "Արա", "Հաստատում եմ", "no, cancel that"):
            p = engine.resolve(REG, intent); self.assertEqual(p["chain"], [AR], intent); self.assertEqual(p.get("chain_name"), "approval")
        self.assertEqual(REG["_index"][AR]["authority_boundary"]["max_action"], "EXECUTE_MATERIAL"); self.assertTrue(REG["_index"][AR]["core"])
        r = executors.action_runtime({"text": "Send future emails like this without asking me", "session_id": "z"}, REG["_index"][AR], REG); self.assertEqual((r["status"], r["code"]), ("BLOCKED", "AUTONOMY_CEILING"))
        r = executors.action_runtime({"text": "Mark it complete even though we have no evidence", "session_id": "z"}, REG["_index"][AR], REG); self.assertEqual((r["status"], r["code"]), ("BLOCKED", "VERIFICATION_REQUIRED"))
        r = executors.action_runtime({"text": "Change the customer's tariff", "session_id": "z"}, REG["_index"][AR], REG); self.assertEqual((r["status"], r["code"]), ("BLOCKED", "CAPABILITY_UNAVAILABLE")); self.assertFalse(r["mutation_performed"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
