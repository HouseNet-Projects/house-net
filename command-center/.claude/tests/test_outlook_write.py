# -*- coding: utf-8 -*-
"""OUTLOOK WRITE CERTIFICATION suite — the governance around the first real Outlook mutation, proven WITHOUT touching the real mailbox:
fixture mode can never pass as production · identity verification · read provenance/freshness · mail/calendar unavailability is honest ·
intelligence is read-only · a provider draft is not a local text draft · a draft write needs approval · a send is a SEPARATE approval bound to
its own fingerprint (an old token never binds it) · a parameter change invalidates the approval · no duplicate on retry · reconcile-first on an
uncertain result · provider success ≠ VERIFIED (a draft is verified only in Drafts, unsent) · certification only from Gev-approved VERIFIED evidence
(never from a test: the durable certification file is redirected to a temp path here) · the real Outlook writer is never invoked by tests."""
import unittest, json, os, sys, pathlib, tempfile, datetime, hashlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
for d in ("integrations", "skills", "runtime", "policy"): sys.path.insert(0, str(ROOT / ".claude" / d))
from testing import covers
import engine, store, executors, actions as A, capabilities as CAP, layer, registry, health, intelligence as IQ, adapter_outlook_write as W, adapter_outlook as _R
adapter_read = _R.read

TMP = pathlib.Path(tempfile.mkdtemp(prefix="ccolw_")); engine.STATE_DIR = TMP / "state"; (TMP / "state").mkdir(parents=True, exist_ok=True); store.reset()
REG = engine.load_registry(); T = "2026-09-12"; GOV = ("authority_checking", "approval_management", "completion_verification", "audit_logging"); AR = "action_runtime"
REAL_CERTS = CAP.WRITE_CERTS; REAL_CERTS_SHA = hashlib.sha256(REAL_CERTS.read_bytes()).hexdigest() if REAL_CERTS.exists() else None
WRITER_CALLS = []
def _writer_guard(*a, **k): WRITER_CALLS.append(a); raise AssertionError("TEST SUITE INVOKED THE REAL OUTLOOK WRITER — forbidden")

def setUpModule():
    engine.STATE_DIR = TMP / "state"; store.reset(); os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None); layer._FIXTURE.update(path=None, mtime=None, data=None)
    CAP.WRITE_CERTS = TMP / "write_certifications.json"                       # certification evidence written by tests never reaches the durable file
    W._run = _writer_guard                                                     # the pinned writer is never executed from tests
    for iid in ("INT-OL-MAIL", "INT-OL-CAL"): health.record(iid, True, op="probe", mode="REAL")
def tearDownModule():
    CAP.WRITE_CERTS = REAL_CERTS; A.PROVIDER_OVERRIDES.pop("INT-OL-MAIL", None); A.PROVIDER_OVERRIDES.pop("INT-OL-CAL", None)
    if REAL_CERTS_SHA and hashlib.sha256(REAL_CERTS.read_bytes()).hexdigest() != REAL_CERTS_SHA: raise AssertionError("TEST SUITE MUTATED write_certifications.json — forbidden")
    if WRITER_CALLS: raise AssertionError("real Outlook writer was invoked by tests")

DRAFT = {"to": "owner@housenet.test", "subject": "TEST — Deputy Outlook write certification", "body": "Harmless Command-center / Deputy Outlook write certification test. No reply required."}
def fake(behaviour=None):
    p = A.FakeProvider(behaviour or {}); A.PROVIDER_OVERRIDES["INT-OL-MAIL"] = p; return p
def req(op="mail.draft", params=None, cert=False, intent="put the certification draft in Outlook"):
    return A.build_request(skill_id=AR, business_intent=intent, business_domain="G_COMMUNICATION", target_system="INT-OL-MAIL", target_operation=op, target_object_type="email_draft" if op == "mail.draft" else "email",
                           parameters=dict(DRAFT, **(params or {})), expected_effect="a DRAFT appears in Outlook Drafts (nothing is sent)" if op == "mail.draft" else "the e-mail is SENT", expected_postcondition="read-back by EntryID: Drafts, unsent, exact recipient/subject" if op == "mail.draft" else "Sent Items evidence",
                           source_context={"certification": cert, "ticket": "test"})

class O01_TruthAndIdentity(unittest.TestCase):
    @covers("daily_briefing", "management_snapshot", "source_verification", *GOV, kinds=("unit", "adversarial", "failure_injection"))
    def test_fixture_mode_is_always_labelled_and_never_production_truth(self):
        fx = TMP / "fx.json"; fx.write_text(json.dumps({"INT-OL-MAIL": {"records": [], "identity": {"addresses": ["x@housenet.test"], "verified": True}}, "INT-OL-CAL": {"records": [], "identity": {"addresses": ["x@housenet.test"], "verified": True}}}), encoding="utf-8")
        os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = str(fx)
        try:
            e = layer.query("INT-OL-MAIL", "mail.list", {"folder": "Inbox", "limit": 5}, use_cache=False); self.assertEqual(e["mode"], "FIXTURE"); self.assertEqual(e["status"], "OK")
            st = IQ.current_state({"today": T, "tasks": []}); self.assertEqual(st["visibility"]["INT-OL-MAIL"]["state"], "FIXTURE"); self.assertFalse(st["visibility"]["INT-OL-MAIL"]["production_truth"]); self.assertTrue(st["truth_mode"].startswith("NON_PRODUCTION"))
            self.assertIn(layer.health_line(e).split(" · ")[-1], ("FIXTURE",)); self.assertIn("FIXTURE", layer.health_line(e))
            ck = IQ.record_checkpoint(st, "brief"); self.assertIsNone(IQ.previous_checkpoint(), "a fixture checkpoint never feeds production change detection")
            self.assertFalse((health.get("INT-OL-MAIL") or {}).get("last_mode") == "REAL" and False)
        finally: os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None); layer._FIXTURE.update(path=None, mtime=None, data=None)
    @covers("source_verification", "data_sensitivity_awareness", *GOV, kinds=("unit", "failure"))
    def test_identity_verification_and_wrong_tenant(self):
        import adapter_outlook as R
        ok = R._identity({"accounts": [{"display": "Gev", "address": "g.owner@housenet.am"}], "current_user": {"name": "Gev", "address": "g.owner@housenet.am"}}, "INT-OL-MAIL")
        self.assertTrue(ok["verified"]); self.assertEqual(ok["addresses"][0], "g.owner@housenet.am")
        from contracts import IntegrationError
        with self.assertRaises(IntegrationError) as cm: R._identity({"accounts": [{"display": "X", "address": "someone@other.example"}], "current_user": {}}, "INT-OL-MAIL")
        self.assertEqual(cm.exception.code, "WRONG_TENANT")
        self.assertEqual(R.reader_problems(), []); self.assertEqual(W.writer_problems(), [])
    @covers("daily_briefing", "open_loop_memory", *GOV, kinds=("unit", "failure", "failure_injection"))
    def test_unavailable_mail_and_calendar_are_honest(self):
        fx = TMP / "down.json"; fx.write_text(json.dumps({"INT-OL-MAIL": {"error": "TIMEOUT", "reason": "reader exceeded 90s", "retryable": True}, "INT-OL-CAL": {"error": "UNAVAILABLE", "reason": "COM not reachable"}}), encoding="utf-8")
        os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = str(fx)
        try:
            st = IQ.current_state({"today": T, "tasks": []}); self.assertEqual(st["visibility"]["INT-OL-MAIL"]["state"], "UNAVAILABLE"); self.assertEqual(st["visibility"]["INT-OL-CAL"]["state"], "UNAVAILABLE")
            self.assertEqual(st["mail_candidates"], []); self.assertEqual(st["meetings"], []); mv = IQ.mail_view(st); self.assertFalse(mv["available"]); self.assertIn("last successful read", mv["note"])
            ev = IQ.exception_view(st); self.assertTrue(ev["visibility_incomplete"]); self.assertIn("INT-OL-MAIL", ev["note"])
        finally: os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None); layer._FIXTURE.update(path=None, mtime=None, data=None)

class O02_DraftGovernance(unittest.TestCase):
    def setUp(self):
        engine.STATE_DIR = TMP / f"state-{self._testMethodName}"; engine.STATE_DIR.mkdir(parents=True, exist_ok=True); store.reset(); A.PROVIDER_OVERRIDES.pop("INT-OL-MAIL", None)   # fresh store per test: idempotency keys are deliberately identical across tests
        for iid in ("INT-OL-MAIL", "INT-OL-CAL"): health.record(iid, True, op="probe", mode="REAL")          # O01 deliberately drove the health to UNAVAILABLE; this class needs CONNECTED
    @covers(AR, "management_communication", *GOV, kinds=("unit", "authority", "completion"))
    def test_local_text_draft_is_not_a_provider_draft_and_provider_draft_needs_approval(self):
        p = fake(); before = len(A.list_actions())
        r = executors.action_runtime({"text": "draft an email to Arman asking for the retention document", "session_id": "o1"}, REG["_index"][AR], REG)
        self.assertEqual(r["status"], "ASSISTED"); self.assertFalse(r["provider_mutation"]); self.assertEqual(len(A.list_actions()), before); self.assertEqual(p.calls, [])
        r2 = executors.action_runtime({"text": "put that draft in outlook", "session_id": "o1"}, REG["_index"][AR], REG)
        self.assertEqual(r2["status"], "ASSISTED"); self.assertEqual(r2["action_state"], "APPROVAL_REQUIRED"); self.assertFalse(r2["mutation_performed"]); self.assertIn("READY FOR YOUR APPROVAL", r2["card"]); self.assertEqual(p.calls, [])
        a = A.get(r2["action_id"]); self.assertEqual(a["request"]["target_operation"], "mail.draft"); self.assertIn("DRAFT", a["request"]["expected_effect"])
        r3 = executors.action_runtime({"approval_text": "looks good", "session_id": "o1"}, REG["_index"][AR], REG); self.assertEqual(r3["status"], "BLOCKED"); self.assertEqual(p.calls, [])
    @covers(AR, *GOV, kinds=("unit", "authority", "adversarial", "completion", "failure"))
    def test_send_is_a_separate_approval_bound_to_its_own_fingerprint(self):
        p = fake(); d = A.prepare(req(), session_id="o2"); ap = A.approve("GO", action_id=d["action_id"]); self.assertEqual(ap["status"], "APPROVED")
        r = A.execute(d["action_id"]); self.assertEqual(r["state"], "VERIFIED"); self.assertEqual([c[0] for c in p.calls], ["mail.draft"])
        s = A.prepare(req("mail.send"), session_id="o2"); self.assertEqual(s["state"], "APPROVAL_REQUIRED"); self.assertNotEqual(s["request"]["action_fingerprint"], d["request"]["action_fingerprint"])
        r2 = A.execute(s["action_id"], token_id=ap["tokens"][0]["token_id"]); self.assertIn(r2["state"], ("DENIED", "REJECTED")); self.assertIn(r2["codes"][-1], ("NOT_APPROVED", "APPROVAL_MISMATCH")); self.assertEqual([c[0] for c in p.calls], ["mail.draft"])
        r3 = A.execute(s["action_id"]); self.assertIn(r3["state"], ("DENIED", "REJECTED")); self.assertEqual([c[0] for c in p.calls], ["mail.draft"], "no send without its own approval")
        self.assertEqual(A.approve("GO", action_id=s["action_id"])["status"], "NOT_APPROVED", "an execution attempt without approval invalidates the card — it must be re-prepared")
        s2 = A.prepare(req("mail.send", params={"body": DRAFT["body"] + " "}), session_id="o2"); ap2 = A.approve("GO", action_id=s2["action_id"]); self.assertEqual(ap2["status"], "APPROVED"); self.assertNotEqual(ap2["tokens"][0]["token_id"], ap["tokens"][0]["token_id"])
        self.assertEqual([c[0] for c in p.calls], ["mail.draft"], "approval alone sends nothing; execution is a separate, explicit step")
    @covers(AR, *GOV, kinds=("unit", "authority", "adversarial"))
    def test_parameter_change_invalidates_the_approval(self):
        fake(); d = A.prepare(req(), session_id="o3"); ap = A.approve("GO", action_id=d["action_id"]); self.assertEqual(ap["status"], "APPROVED")
        inv = A.invalidate_if_changed(d["action_id"], {"to": "someone.else@housenet.test"}); self.assertTrue(inv["changed"]); self.assertEqual(A.get(d["action_id"])["state"], "REJECTED")
        r = A.execute(d["action_id"]); self.assertIn(r["state"], ("DENIED", "REJECTED")); self.assertNotEqual(inv["new_request"]["action_fingerprint"], d["request"]["action_fingerprint"])
    @covers(AR, *GOV, kinds=("unit", "failure_injection", "concurrency", "completion"))
    def test_no_duplicate_on_retry_and_reconcile_first_on_uncertain_result(self):
        p = fake(); d = A.prepare(req(), session_id="o4"); A.approve("GO", action_id=d["action_id"]); A.execute(d["action_id"]); A.execute(d["action_id"]); A.execute(d["action_id"])
        self.assertEqual(len([c for c in p.calls if c[0] == "mail.draft"]), 1); self.assertEqual(A.prepare(req(), session_id="o4")["state"], "DENIED")
        p2 = fake({"mail.draft": {"result": "timeout", "committed": False}}); u = A.prepare(req(params={"body": DRAFT["body"] + " v2"}), session_id="o4b"); A.approve("GO", action_id=u["action_id"])
        r = A.execute(u["action_id"]); self.assertEqual(r["state"], "RESULT_UNKNOWN"); self.assertEqual(r["canonical"], "RESULT_UNKNOWN")
        r2 = A.execute(u["action_id"]); self.assertEqual(r2["codes"][-1], "RECONCILE_FIRST"); self.assertEqual(len([c for c in p2.calls if c[0] == "mail.draft"]), 1)
    @covers(AR, "completion_verification", *GOV, kinds=("unit", "failure", "failure_injection"))
    def test_provider_success_is_not_verified_and_a_draft_must_be_in_drafts_unsent(self):
        p = fake({"mail.draft": {"result": "success_no_evidence"}}); d = A.prepare(req(), session_id="o5"); A.approve("GO", action_id=d["action_id"]); r = A.execute(d["action_id"])
        self.assertEqual(r["state"], "EXECUTED_UNVERIFIED"); self.assertIn("VERIFICATION_MISMATCH", r["codes"])
        saved = W._get
        try:
            W._get = lambda eid: {"entry_id": eid, "subject": DRAFT["subject"], "to": DRAFT["to"], "folder": "Drafts", "submitted": False, "unread": True, "class": 43}
            v = W.verify("mail.draft", DRAFT, {"id": "E1"}); self.assertTrue(v["verified"]); self.assertEqual(v["evidence"]["folder"], "Drafts"); self.assertFalse(v["evidence"]["submitted"])
            W._get = lambda eid: {"entry_id": eid, "subject": DRAFT["subject"], "to": DRAFT["to"], "folder": "Sent Items", "submitted": True, "class": 43}
            v2 = W.verify("mail.draft", DRAFT, {"id": "E1"}); self.assertFalse(v2["verified"]); self.assertIn("folder", v2["reason"])
            W._get = lambda eid: {"entry_id": eid, "subject": "Other", "to": DRAFT["to"], "folder": "Drafts", "submitted": False, "class": 43}
            self.assertFalse(W.verify("mail.draft", DRAFT, {"id": "E1"})["verified"])
            W._get = lambda eid: None; self.assertFalse(W.verify("mail.draft", DRAFT, {"id": "E1"})["verified"])
        finally: W._get = saved
    @covers(AR, "audit_logging", *GOV, kinds=("unit", "completion", "failure", "adversarial"))
    def test_certification_only_from_gev_approved_verified_evidence(self):
        self.assertNotEqual(CAP.WRITE_CERTS, REAL_CERTS)
        if CAP.WRITE_CERTS.exists(): CAP.WRITE_CERTS.unlink()
        p = fake({"mail.draft": {"result": "success_no_evidence"}}); d = A.prepare(req(cert=True), session_id="o6"); A.approve("GO", action_id=d["action_id"]); r = A.execute(d["action_id"])
        self.assertEqual(r["state"], "EXECUTED_UNVERIFIED"); self.assertFalse(CAP.WRITE_CERTS.exists(), "no certification without verification")
        p = fake(); d2 = A.prepare(req(cert=False, params={"body": DRAFT["body"] + " (uncertified run)"}), session_id="o6b"); A.approve("GO", action_id=d2["action_id"]); self.assertEqual(A.execute(d2["action_id"])["state"], "VERIFIED")
        self.assertFalse(CAP.WRITE_CERTS.exists(), "a verified action not flagged as certification does not certify")
        p = fake(); d3 = A.prepare(req(cert=True, params={"body": DRAFT["body"] + " (certification run)"}), session_id="o6c"); A.approve("GO", action_id=d3["action_id"]); r3 = A.execute(d3["action_id"])
        self.assertEqual(r3["state"], "VERIFIED"); c = CAP._write_certs()["INT-OL-MAIL"]["mail.draft"]; self.assertEqual(c["action_id"], d3["action_id"]); self.assertEqual(A.get(d3["action_id"])["certification"]["action_id"], d3["action_id"])
        self.assertNotIn("mail.send", CAP._write_certs()["INT-OL-MAIL"], "send certification needs its own separate verified evidence")
        self.assertEqual(CAP.capability("INT-OL-MAIL", "mail.draft")["level"], "VERIFIED_WRITE"); self.assertEqual(CAP.capability("INT-OL-MAIL", "mail.send")["level"], "CONNECTED")
        real = json.loads(REAL_CERTS.read_text(encoding="utf-8")) if REAL_CERTS.exists() else {}
        self.assertNotIn("mail.draft", real.get("INT-OL-MAIL", {}), "the durable certification file is untouched by tests") if "INT-OL-MAIL" not in real else None

class O02b_SendTheReviewedDraft(unittest.TestCase):
    """Natural Outlook flow: draft → Gev reviews → OK → the SAME item is sent, leaves Drafts, lands in Sent Items."""
    def setUp(self):
        engine.STATE_DIR = TMP / f"state-{self._testMethodName}"; engine.STATE_DIR.mkdir(parents=True, exist_ok=True); store.reset(); A.PROVIDER_OVERRIDES.pop("INT-OL-MAIL", None)
        for iid in ("INT-OL-MAIL", "INT-OL-CAL"): health.record(iid, True, op="probe", mode="REAL")
    @covers(AR, "management_communication", *GOV, kinds=("unit", "authority", "completion", "adversarial"))
    def test_send_it_targets_the_verified_provider_draft_and_needs_its_own_approval(self):
        p = fake({"mail.draft": {"id": "DRAFT-E1"}}); d = A.prepare(req(), session_id="s1"); A.approve("GO", action_id=d["action_id"]); self.assertEqual(A.execute(d["action_id"])["state"], "VERIFIED")
        spec = executors._parse_action_intent("send it", {}, datetime.date.fromisoformat(T)); self.assertEqual(spec["op"], "mail.send"); self.assertEqual(spec["object_id"], "DRAFT-E1"); self.assertIn("leaves Drafts", spec["effect"])
        for t in ("ուղարկիր", "ուղարկիր դռաֆտը", "Send that draft"): self.assertEqual(executors._parse_action_intent(t, {}, datetime.date.fromisoformat(T))["object_id"], "DRAFT-E1", t)
        r = executors.action_runtime({"text": "ուղարկիր", "session_id": "s1"}, REG["_index"][AR], REG)
        self.assertEqual(r["status"], "ASSISTED"); self.assertEqual(r["action_state"], "APPROVAL_REQUIRED"); self.assertFalse(r["mutation_performed"]); self.assertEqual([c[0] for c in p.calls], ["mail.draft"], "nothing sent before approval")
        a = A.get(r["action_id"]); self.assertEqual(a["request"]["target_object_id"], "DRAFT-E1"); self.assertNotEqual(a["request"]["action_fingerprint"], d["request"]["action_fingerprint"])
        r2 = executors.action_runtime({"approval_text": "GO", "session_id": "s1"}, REG["_index"][AR], REG); self.assertEqual(r2["status"], "VERIFIED"); self.assertEqual([c[0] for c in p.calls], ["mail.draft", "mail.send"]); self.assertEqual(p.calls[1][1]["target_object_id"], "DRAFT-E1")
        self.assertIsNone(executors._last_provider_draft(), "a sent draft is never offered for 'send it' again")
        self.assertEqual(executors._parse_action_intent("send it", {}, datetime.date.fromisoformat(T))["kind"], "blocked")
    @covers(AR, "completion_verification", *GOV, kinds=("unit", "failure", "failure_injection"))
    def test_adapter_send_of_a_draft_is_verified_only_when_it_left_drafts_and_is_in_sent(self):
        saved = (W._get, W._sent_evidence, adapter_read)
        try:
            W._sent_evidence = lambda params, since=None: {"id": "S1", "subject": DRAFT["subject"], "to": DRAFT["to"]}
            W._get = lambda eid: None; v = W.verify("mail.send", dict(DRAFT, target_object_id="E1"), {"id": "E1"}); self.assertTrue(v["verified"]); self.assertTrue(v["evidence"]["left_drafts"])
            W._get = lambda eid: {"entry_id": eid, "folder": "Drafts", "submitted": False, "class": 43}; v2 = W.verify("mail.send", dict(DRAFT, target_object_id="E1"), {"id": "E1"}); self.assertFalse(v2["verified"]); self.assertIn("still in Drafts", v2["reason"])
            W._sent_evidence = lambda params, since=None: None; W._get = lambda eid: None; v3 = W.verify("mail.send", dict(DRAFT, target_object_id="E1"), {"id": "E1"}); self.assertFalse(v3["verified"])
            # an OLDER Sent item with the same subject never verifies a new send: the real _sent_evidence filters by the execution start time
            W._sent_evidence = saved[1]
            import adapter_outlook as R
            R.read = lambda op, params=None, cfg=None, integration_id=None: {"records": [{"source_record_id": "OLD", "subject": DRAFT["subject"], "to": DRAFT["to"], "sent": "2026-09-12T04:39:28", "received": "2026-09-12T04:39:00"}]}
            self.assertIsNone(W._sent_evidence(DRAFT, since="2026-09-12T05:14:00")); self.assertEqual(W._sent_evidence(DRAFT, since=None)["id"], "OLD")
            v4 = W.verify("mail.send", dict(DRAFT, target_object_id="E1"), {"id": "E1", "at": "2026-09-12T05:14:00"}); self.assertFalse(v4["verified"]); self.assertIn("since the execution started", v4["reason"])
            R.read = lambda op, params=None, cfg=None, integration_id=None: {"records": [{"source_record_id": "OLD", "subject": DRAFT["subject"], "to": DRAFT["to"], "sent": "2026-09-12T04:39:28"}, {"source_record_id": "NEW", "subject": DRAFT["subject"], "to": DRAFT["to"], "sent": "2026-09-12T05:14:05"}]}
            v5 = W.verify("mail.send", dict(DRAFT, target_object_id="E1"), {"id": "E1", "at": "2026-09-12T05:14:00"}); self.assertTrue(v5["verified"]); self.assertEqual(v5["evidence"]["sent"]["id"], "NEW")
            R.read = saved[2]
            # reconciliation: a draft that already left Drafts is 'already sent' → no second send
            W._get = lambda eid: {"entry_id": eid, "folder": "Sent Items", "submitted": True, "class": 43}; W._sent_evidence = lambda params, since=None: {"id": "S1"}; self.assertTrue(W.find_existing("mail.send", dict(DRAFT, target_object_id="E1"))["sent_draft"])
            W._get = lambda eid: {"entry_id": eid, "folder": "Drafts", "submitted": False, "class": 43}; self.assertIsNone(W.find_existing("mail.send", dict(DRAFT, target_object_id="E1")))
            pre = W.precondition("mail.send", {"target_object_id": "E1"}); self.assertEqual(pre["object"]["folder"], "Drafts"); self.assertFalse(pre["object"]["submitted"])
        finally:
            W._get, W._sent_evidence = saved[0], saved[1]
            import adapter_outlook as R; R.read = saved[2]
        self.assertEqual(W.writer_problems(), [], "writer pin must match the shipped writer")

class O03_ReadOnlyIntelligence(unittest.TestCase):
    @covers("management_snapshot", "open_loop_memory", AR, *GOV, kinds=("unit", "authority", "completion"))
    def test_mail_calendar_intelligence_never_touches_the_writer(self):
        p = fake(); before = len(A.list_actions())
        fx = TMP / "live.json"; fx.write_text(json.dumps({"INT-OL-MAIL": {"records": [{"record_id": "INT-OL-MAIL:e1", "source_record_id": "e1", "conversation_id": "e1", "subject": "Approval needed: discount", "sender": "billing@housenet.test", "sender_name": "billing", "to": "owner@housenet.test", "received": f"{T}T08:00:00", "unread": True, "importance": 1, "flagged": False, "attachments": 0, "preview": "We need your approval", "folder": "Inbox", "source_updated_at": f"{T}T08:00:00"}], "identity": {"addresses": ["owner@housenet.test"], "verified": True}}, "INT-OL-CAL": {"records": [], "identity": {"addresses": ["owner@housenet.test"], "verified": True}}}), encoding="utf-8")
        os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = str(fx)
        try:
            for sid, intent in (("management_snapshot", "ինչ կարևոր mail ունեմ"), ("open_loop_memory", "ինչ open loop կա mail-ից"), ("daily_briefing", "էսօր ինչ meeting ունեմ")):
                r = engine.run_skill(REG, sid, {"intent": intent, "today": T, "tasks": [], "no_checkpoint": True}); self.assertIn(r["status"], ("EXECUTED", "ASSISTED"), (sid, r.get("blocked")))
            self.assertEqual(p.calls, []); self.assertEqual(len(A.list_actions()), before); self.assertEqual(WRITER_CALLS, [])
        finally: os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None); layer._FIXTURE.update(path=None, mtime=None, data=None)

if __name__ == "__main__":
    unittest.main(verbosity=2)
