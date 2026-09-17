# -*- coding: utf-8 -*-
"""INTEGRATION LAYER suite (Mission 4, READ-ONLY) — registry declarations · structural read-only boundary (allowlists, write intents,
pinned reader, GET-only CRM client) · normalized envelopes with provenance and freshness · failure matrix (invalid/expired
credentials, permission denied, network, malformed, schema change, rate limit, partial, duplicates, conflicting records, wrong
tenant, unexpected PII, tool unavailable) · secret leakage · health · Daily Brief / meeting prep / open loops consuming live
context · reconciliation · certification states · audit without payloads · sensitive boundary.
Live systems are FIXTURES (mode=FIXTURE, never counted as real reads); the task register and the Outlook reader are exercised
for real where present (real Outlook tests skip with a reason when Outlook is not reachable on the machine)."""
import unittest, json, os, sys, pathlib, tempfile, shutil, datetime, subprocess
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "skills")); sys.path.insert(0, str(ROOT / ".claude" / "integrations")); sys.path.insert(0, str(ROOT / ".claude" / "policy"))
from testing import covers
import engine, executors, store
import contracts as C, registry, layer, health, int_secrets as _secrets, reconcile, adapter_outlook, adapter_bitrix24, adapter_tasks, adapter_mikrobill, certify_integrations

TMP = pathlib.Path(tempfile.mkdtemp(prefix="skillint_")); engine.STATE_DIR = TMP / "state"; store.reset()
REG = engine.load_registry()
GOV = ("authority_checking", "approval_management", "completion_verification", "audit_logging")
T = "2026-09-11"

def _mt(title, start, end, parts=("Arman Tester", "Billing Head"), desc="", rid="m1"):
    return {"record_id": f"INT-OL-CAL:{rid}", "source_record_id": rid, "title": title, "start": start, "end": end, "all_day": False, "organizer": "Gev", "participants": [{"name": p, "address": None} for p in parts],
            "participant_count": len(parts), "location": "Office", "online_link": None, "description_preview": desc, "recurring": False, "source_updated_at": "2026-09-10T09:00:00"}
def _msg(subject, sender, preview, rid, conv=None, received="2026-09-10T10:00:00"):
    return {"record_id": f"INT-OL-MAIL:{rid}", "source_record_id": rid, "conversation_id": conv or rid, "subject": subject, "sender": sender, "sender_name": sender.split("@")[0], "to": "gev@example.test", "received": received,
            "unread": True, "importance": 1, "flagged": False, "attachments": 0, "preview": preview, "folder": "Inbox", "source_updated_at": received}
LIVE = {"INT-OL-CAL": {"records": [_mt("Sales Review", f"{T}T10:00:00", f"{T}T11:00:00", desc="Review D2D activations and the telesales plan", rid="m1"), _mt("Budget sync", f"{T}T10:30:00", f"{T}T11:30:00", rid="m2"), _mt("Retention flow design", "2026-09-12T15:00:00", "2026-09-12T16:00:00", rid="m3")], "identity": {"addresses": ["gev@example.test"], "verified": True}},
        "INT-OL-MAIL": {"records": [_msg("Please send the retention flow document by Friday", "maga@example.test", "Can you send me the retention flow document by Friday? We need it for the review.", "e1"),
                                    _msg("Approval needed: corporate discount", "billing@example.test", "We need your approval for the 15% corporate discount before we proceed.", "e2"),
                                    _msg("Password Changed", "noreply@example.test", "Your password was changed.", "e3"),
                                    _msg("FYI: office closed Monday", "hr@example.test", "For your information the office is closed on Monday. No action needed.", "e4"),
                                    _msg("Re: Please send the retention flow document by Friday", "maga@example.test", "Reminder — still waiting for the document.", "e5", conv="e1", received="2026-09-10T15:00:00")],
                        "identity": {"addresses": ["gev@example.test"], "verified": True}}}

class Fixture:
    def __init__(self, data, name="fx"):
        self.p = TMP / f"{name}-{os.getpid()}-{id(self)}.json"; self.p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8"); self.old = None
    def __enter__(self):
        self.old = os.environ.get("COMMAND_CENTER_INTEGRATIONS_FIXTURE"); os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = str(self.p); return self
    def __exit__(self, *a):
        if self.old is None: os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None)
        else: os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = self.old
        layer._FIXTURE.update(path=None, mtime=None, data=None)
    def set(self, data): self.p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def _clear_cache():
    p = layer._cache_path()
    if p.exists(): p.unlink()

class I01_Registry(unittest.TestCase):
    @covers(*GOV, kinds=("unit",))
    def test_declarations_complete_and_read_only(self):
        self.assertEqual(registry.declaration_problems(), [])
        for iid, spec in registry.INTEGRATIONS.items():
            for f in registry.REQUIRED_FIELDS: self.assertIn(f, spec, f"{iid}.{f}")
            self.assertEqual(spec["write_ops"], [], iid); self.assertIn(spec["classification"], ("INTERNAL", "CONFIDENTIAL"))
            self.assertIsInstance(spec["freshness"]["rule"], str); self.assertIn("cache_ttl_seconds", spec["freshness"])
        self.assertEqual(set(registry.INTEGRATIONS), {"INT-TASKS", "INT-OL-CAL", "INT-OL-MAIL", "INT-B24", "INT-MB", "INT-TG", "INT-WA"})
        self.assertEqual(registry.INTEGRATIONS["INT-MB"]["deferred"]["by"], "Gev")       # MikroBILL deferred by the owner: declared, not worked on, not nagged
        self.assertTrue(registry.DEFERRED)      # PBX/Portal/NET/churn deliberately not connected — explicit
        for ft, fa in registry.FACT_AUTHORITY.items():
            self.assertTrue(fa["tiers"] and fa.get("src"), ft)
    @covers(*GOV, "data_sensitivity_awareness", kinds=("unit", "adversarial"))
    def test_outlook_reader_is_pinned_and_has_no_write_member(self):
        self.assertEqual(adapter_outlook.reader_problems(), [])
        self.assertEqual(adapter_outlook.reader_sha256(), registry.OUTLOOK_READER_SHA256)
        txt = adapter_outlook.READER.read_text(encoding="utf-8")
        for bad in (".Send(", ".Save(", ".Move(", ".Delete(", "CreateItem", ".UnRead =", "Set-"): self.assertNotIn(bad, txt)
        # a modified reader is refused before it can run
        tmp = TMP / "reader_copy.ps1"; tmp.write_text(txt + "\n# tampered\n", encoding="utf-8")
        old = adapter_outlook.READER; adapter_outlook.READER = tmp
        try:
            probs = adapter_outlook.reader_problems(); self.assertTrue(any("integrity pin" in p for p in probs))
            with self.assertRaises(C.ReadOnlyViolation): adapter_outlook._run(["-Op", "probe"])
        finally: adapter_outlook.READER = old
    @covers(*GOV, kinds=("unit",))
    def test_no_adapter_exposes_a_write_callable(self):
        for mod in (adapter_outlook, adapter_bitrix24, adapter_tasks, adapter_mikrobill, layer):
            for name in dir(mod):
                if callable(getattr(mod, name)) and not name.startswith("_") and name != "default_transport":
                    self.assertIsNone(C.WRITE_OP_RX.search(name), f"{mod.__name__}.{name}")

class I02_ReadOnlyBoundary(unittest.TestCase):
    @covers(*GOV, "management_communication", kinds=("authority", "adversarial", "routing"))
    def test_write_intents_blocked_structurally_and_at_the_gate(self):
        for intent in ("send an email to Arman about the invoice", "reply to the email from billing", "create a meeting with the billing head tomorrow", "reschedule the meeting to Friday", "update the deal stage to won in bitrix",
                       "delete the task in bitrix", "change the tariff for subscriber 1234", "update the customer address", "mark all as read", "move the message to archive folder", "Ուղարկիր նամակ ղեկավարին", "մեյլը ուղարկի", "նամակին պատասխանիր"):
            c = layer.capability(intent); self.assertEqual((c["status"], c["code"], c["capability"]), ("BLOCKED", "AUTHORITY_EXCEEDED", "WRITE_DISABLED"), intent); self.assertIn(c["write_intent"], C.WRITE_INTENTS)
        for intent in ("what meetings do I have today", "check my email for unanswered requests", "search my mail for the invoice", "Նամակներում ինչ բաց հարց կա", "Այսօրվա հանդիպումները ցույց տուր"):
            self.assertEqual(layer.capability(intent)["status"], "OK", intent)
        for iid, op in (("INT-OL-MAIL", "mail.send"), ("INT-OL-MAIL", "mail.mark_read"), ("INT-OL-CAL", "calendar.create"), ("INT-B24", "crm.deal.update"), ("INT-B24", "tasks.delete"), ("INT-TASKS", "tasks.update"), ("INT-MB", "tariff.change")):
            e = layer.query(iid, op, {}); self.assertEqual(e["status"], "FAILED"); self.assertEqual(e["code"], "READ_ONLY_VIOLATION", f"{iid} {op}"); self.assertEqual(e["records"], [])
        e = layer.query("INT-OL-MAIL", "mail.nonsense", {}); self.assertEqual(e["code"], "UNKNOWN_OPERATION")
        e = layer.query("INT-OL-MAIL", "mail.list", {}, intent="send an email to the billing head"); self.assertEqual(e["code"], "READ_ONLY_VIOLATION"); self.assertEqual(e["capability"]["write_intent"], "SEND_EMAIL")
        # Mission 4.2: every write intent has ONE path — the Action Runtime (prepare → Gev approval → execute → verify); the read layer above still refuses writes
        plan = engine.resolve(REG, "send an email to the billing head about the invoice"); self.assertIn("action_runtime", plan["chain"]); self.assertEqual(plan.get("tool_requirements"), [])
        plan = engine.resolve(REG, "update the deal stage to won in bitrix"); self.assertEqual(plan["chain"], ["action_runtime"])
    @covers(*GOV, kinds=("unit", "adversarial"))
    def test_bitrix_client_refuses_every_non_read_method(self):
        cfg = {"webhook_url": "https://example.invalid/rest/1/abcdefghijkl/"}
        for m in ("crm.deal.update", "crm.deal.add", "crm.lead.delete", "tasks.task.add", "tasks.task.complete", "im.message.add", "batch", "crm.deal.list.update", ""):
            with self.assertRaises(C.ReadOnlyViolation, msg=m): adapter_bitrix24.call(m, {}, cfg, transport=lambda url, timeout=20: (200, '{"result": []}'))
        # the transport is GET-only: a read method builds a GET url and never a body
        seen = {}
        def tr(url, timeout=20): seen["url"] = url; return 200, json.dumps({"result": []})
        adapter_bitrix24.call("crm.deal.list", {"select": ["ID"]}, cfg, transport=tr); self.assertIn("/crm.deal.list.json?", seen["url"])

class I03_Envelope(unittest.TestCase):
    @covers("daily_briefing", "meeting_preparation", *GOV, kinds=("unit",))
    def test_normalized_envelope_provenance_freshness_and_cache(self):
        _clear_cache(); h0 = health.get("INT-OL-CAL") or {}
        with Fixture(LIVE):
            e = layer.query("INT-OL-CAL", "calendar.events", {"from": f"{T}T00:00:00", "to": f"{T}T23:59:59"}, use_cache=True)
            self.assertEqual(e["status"], "OK"); self.assertEqual(e["kind"], "meeting"); self.assertEqual(e["count"], 3); self.assertEqual(e["freshness"], "LIVE"); self.assertEqual(e["mode"], "FIXTURE")
            for k in ("integration_id", "source_system", "retrieved_at", "source_updated_at", "classification", "authority", "confidence", "provenance", "label", "meaning"): self.assertIn(k, e)
            self.assertEqual(C.check_records("meeting", e["records"]), []); self.assertEqual(e["provenance"]["op"], "calendar.events"); self.assertEqual(len(e["provenance"]["record_ids"]), 3)
            self.assertEqual(e["classification"], "CONFIDENTIAL"); self.assertEqual(e["label"], "LIVE_DATA"); self.assertIn("not a confirmed business fact", e["meaning"])
            h = health.get("INT-OL-CAL"); self.assertEqual(h["success_count"], h0.get("success_count", 0)); self.assertEqual(h["last_success"], h0.get("last_success")); self.assertEqual(h["fixture_reads"], h0.get("fixture_reads", 0) + 1)   # fixture ≠ real evidence
            e2 = layer.query("INT-OL-CAL", "calendar.events", {"from": f"{T}T00:00:00", "to": f"{T}T23:59:59"}, use_cache=True)
            self.assertEqual(e2["freshness"], "LIVE"); self.assertFalse(layer._cache_path().exists())          # fixtures are never cached
        if (ROOT / "Tasks.xlsx").exists():                                                                      # real source: second read within ttl is CACHED and says so
            r1 = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True); r2 = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True)
            self.assertEqual((r1["freshness"], r2["freshness"], r2["mode"]), ("LIVE", "CACHED", "REAL")); self.assertIsNotNone(r2["cache_age_seconds"]); self.assertEqual(r1["count"], r2["count"]); self.assertTrue(any("cache" in n for n in r2["notes"]))
        env = layer.query("INT-MB", "anything", {}); self.assertEqual(env["code"], "UNKNOWN_OPERATION")
        env = layer.query("INT-NOPE", "x", {}); self.assertEqual(env["code"], "NOT_REGISTERED")
    @covers("daily_briefing", *GOV, kinds=("failure", "failure_injection"))
    def test_failure_keeps_stale_cache_explicit_never_as_current(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        _clear_cache()
        ok = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True); self.assertEqual((ok["status"], ok["mode"]), ("OK", "REAL"))
        with Fixture({"INT-TASKS": {"error": "UNAVAILABLE", "reason": "register locked"}}):
            bad = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True)
        self.assertEqual((bad["status"], bad["code"], bad["freshness"], bad["records"]), ("FAILED", "UNAVAILABLE", "UNAVAILABLE", []))
        self.assertEqual(len(bad["stale_records"]), ok["count"]); self.assertEqual(bad["stale_retrieved_at"], ok["retrieved_at"]); self.assertIn("last successful read", layer.health_line(bad))
        self.assertNotIn("never", layer.health_line(bad))     # a real read happened before, and the line says when

class I04_FailureMatrix(unittest.TestCase):
    @covers("daily_briefing", "open_loop_memory", *GOV, kinds=("failure", "failure_injection"))
    def test_every_failure_code_maps_to_a_structured_envelope_and_health(self):
        with Fixture({}) as fx:
            for code in ("AUTH_FAILED", "PERMISSION_DENIED", "UNAVAILABLE", "TIMEOUT", "MALFORMED_RESPONSE", "SCHEMA_CHANGED", "RATE_LIMITED", "WRONG_TENANT", "NOT_CONFIGURED"):
                fx.set({"INT-OL-CAL": {"error": code, "reason": f"injected {code}"}})
                e = layer.query("INT-OL-CAL", "calendar.events", {"from": T, "to": T}, use_cache=False)
                self.assertEqual((e["status"], e["code"]), ("FAILED", code)); self.assertEqual(e["health"], C.HEALTH_FOR_CODE.get(code, "UNAVAILABLE")); self.assertEqual(e["records"], [])
                self.assertEqual(health.get("INT-OL-CAL")["status"], e["health"]); self.assertEqual(health.get("INT-OL-CAL")["last_error"]["code"], code)
            fx.set({"INT-OL-CAL": {"exception": "boom"}}); e = layer.query("INT-OL-CAL", "calendar.events", {"from": T, "to": T}, use_cache=False); self.assertEqual(e["code"], "UNAVAILABLE"); self.assertIn("RuntimeError", e["reason"])
            fx.set({"INT-OL-CAL": {"records": [{"junk": 1}]}}); e = layer.query("INT-OL-CAL", "calendar.events", {"from": T, "to": T}, use_cache=False); self.assertEqual(e["code"], "SCHEMA_CHANGED")
            fx.set({"INT-OL-CAL": {"records": [_mt("A", f"{T}T10:00:00", f"{T}T11:00:00", rid="x"), _mt("A", f"{T}T10:00:00", f"{T}T11:00:00", rid="x")], "partial": True, "notes": ["page 1 of 2"]}})
            e = layer.query("INT-OL-CAL", "calendar.events", {"from": T, "to": T}, use_cache=False)
            self.assertEqual(e["count"], 1); self.assertEqual(e["duplicates_removed"], ["x"]); self.assertTrue(e["partial"]); self.assertEqual(health.get("INT-OL-CAL")["status"], "DEGRADED"); self.assertTrue(any("duplicate" in n for n in e["notes"]))
            fx.set({"INT-OL-MAIL": {"records": [_msg("login", "ops@example.test", "subscriber " + "User" + "_" + "123456" + " reports " + "+374" + "91 12 34 56" + " as contact", "p1")]}})
            e = layer.query("INT-OL-MAIL", "mail.list", {}, use_cache=False)
            self.assertEqual(e["status"], "OK"); self.assertIn("subscriber_login_id", e["pii_flags"]); self.assertIn("phone_am_mobile", e["pii_flags"]); self.assertTrue(any("UNEXPECTED_PII" in n for n in e["notes"]))
    @covers("daily_briefing", *GOV, kinds=("failure", "failure_injection"))
    def test_tool_unavailable_when_powershell_missing(self):
        old = os.environ.get("COMMAND_CENTER_PWSH"); os.environ["COMMAND_CENTER_PWSH"] = str(TMP / "no-such-pwsh.exe")
        try:
            e = layer.query("INT-OL-CAL", "calendar.events", {"from": T, "to": T}, use_cache=False)
            self.assertEqual((e["status"], e["code"], e["health"]), ("FAILED", "TOOL_UNAVAILABLE", "UNAVAILABLE"))
        finally:
            if old is None: os.environ.pop("COMMAND_CENTER_PWSH", None)
            else: os.environ["COMMAND_CENTER_PWSH"] = old
    @covers(*GOV, kinds=("failure",))
    def test_bad_params_fail_closed(self):
        for p in ({"from": "yesterday", "to": T}, {"from": T}, {"from": T, "to": T, "limit": 10000}):
            with self.assertRaises(C.IntegrationError) as cm: adapter_outlook.read("calendar.events", p, {}, integration_id="INT-OL-CAL")
            self.assertEqual(cm.exception.code, "BAD_PARAMS")
        with self.assertRaises(C.IntegrationError) as cm: adapter_outlook.read("mail.search", {"query": ""}, {}, integration_id="INT-OL-MAIL")
        self.assertEqual(cm.exception.code, "BAD_PARAMS")

class I05_Bitrix24(unittest.TestCase):
    CFG = {"webhook_url": "https://portal.example.invalid/rest/7/s3cr3tc0d3xyz/", "portal_domain": "portal.example.invalid"}
    def _tr(self, status, body): return lambda url, timeout=20: (status, body if isinstance(body, str) else json.dumps(body))
    @covers("sales_kpi_monitoring", "pipeline_management", *GOV, kinds=("unit",))
    def test_normalized_deals_and_identity(self):
        deals = {"result": [{"ID": "12", "TITLE": "Plus 7000 — Armavir", "STAGE_ID": "NEW", "ASSIGNED_BY_ID": "5", "OPPORTUNITY": "7000", "CURRENCY_ID": "AMD", "DATE_CREATE": "2026-09-01T10:00:00+04:00", "DATE_MODIFY": "2026-09-10T10:00:00+04:00", "CLOSED": "N"}], "total": 1}
        r = adapter_bitrix24.read("crm.deals", {"limit": 10}, self.CFG, transport=self._tr(200, deals))
        self.assertEqual(r["kind"], "deal"); self.assertEqual(C.check_records("deal", r["records"]), []); self.assertEqual(r["records"][0]["stage_id"], "NEW"); self.assertFalse(r["partial"]); self.assertEqual(r["identity"]["portal"], "portal.example.invalid")
        r = adapter_bitrix24.read("identity", {}, self.CFG, transport=self._tr(200, {"result": {"ID": "7", "NAME": "Deputy", "LAST_NAME": "Reader", "ADMIN": False}}))
        self.assertEqual(r["records"][0]["portal"], "portal.example.invalid"); self.assertEqual(r["records"][0]["user_id"], "7")
        r = adapter_bitrix24.read("tasks.list", {}, self.CFG, transport=self._tr(200, {"result": {"tasks": [{"id": "3", "title": "Install", "status": "2", "responsibleId": "5", "deadline": "2026-09-12T18:00:00+04:00"}]}}))
        self.assertEqual(r["records"][0]["responsible_id"], "5")
        r = adapter_bitrix24.read("crm.deals", {"limit": 1}, self.CFG, transport=self._tr(200, {"result": [{"ID": "1"}, {"ID": "2"}], "next": 50, "total": 120}))
        self.assertTrue(r["partial"]); self.assertEqual(len(r["records"]), 1); self.assertTrue(any("paged" in n for n in r["notes"]))
    @covers("sales_kpi_monitoring", *GOV, kinds=("failure", "failure_injection"))
    def test_error_mapping_matrix(self):
        cases = [((200, {"error": "expired_token", "error_description": "The access token provided has expired."}), "AUTH_FAILED"), ((401, {"error": "invalid_token"}), "AUTH_FAILED"), ((200, {"error": "NO_AUTH_FOUND"}), "AUTH_FAILED"),
                 ((403, {"error": "insufficient_scope"}), "PERMISSION_DENIED"), ((200, {"error": "ACCESS_DENIED"}), "PERMISSION_DENIED"), ((503, {"error": "QUERY_LIMIT_EXCEEDED"}), "RATE_LIMITED"), ((429, ""), "RATE_LIMITED"),
                 ((500, "<html>Bad gateway</html>"), "MALFORMED_RESPONSE"), ((200, "not json"), "MALFORMED_RESPONSE"), ((200, {"time": {}}), "SCHEMA_CHANGED"), ((200, {"result": {"no": "list"}}), "SCHEMA_CHANGED"), ((200, {"result": [1, 2]}), "SCHEMA_CHANGED")]
        for (status, body), code in cases:
            with self.assertRaises(C.IntegrationError, msg=str(body)) as cm: adapter_bitrix24.read("crm.deals", {}, self.CFG, transport=self._tr(status, body))
            self.assertEqual(cm.exception.code, code, str(body))
        def down(url, timeout=20): raise C.IntegrationError("UNAVAILABLE", "portal unreachable: <urlopen error timed out>", retryable=True)
        with self.assertRaises(C.IntegrationError) as cm: adapter_bitrix24.read("crm.deals", {}, self.CFG, transport=down)
        self.assertEqual(cm.exception.code, "UNAVAILABLE"); self.assertTrue(cm.exception.retryable)
        with self.assertRaises(C.IntegrationError) as cm: adapter_bitrix24.read("crm.deals", {}, {}, transport=self._tr(200, {"result": []}))
        self.assertEqual(cm.exception.code, "NOT_CONFIGURED")
        with self.assertRaises(C.IntegrationError) as cm: adapter_bitrix24.read("crm.deals", {}, {**self.CFG, "portal_domain": "other.example.invalid"}, transport=self._tr(200, {"result": []}))
        self.assertEqual(cm.exception.code, "WRONG_TENANT")
        with self.assertRaises(C.IntegrationError) as cm: adapter_bitrix24.read("crm.deals", {}, {"webhook_url": "http://insecure.example.invalid/rest/1/x/"}, transport=self._tr(200, {"result": []}))
        self.assertEqual(cm.exception.code, "NOT_CONFIGURED")
        # through the layer: envelope + health, no records, no secret; without config the layer never even calls the transport
        e = layer.query("INT-B24", "crm.deals", {}, use_cache=False, transport=self._tr(200, {"error": "expired_token"})); self.assertEqual(e["code"], "NOT_CONFIGURED")
        os.environ["CC_INT_B24_WEBHOOK_URL"] = self.CFG["webhook_url"]
        try:
            e = layer.query("INT-B24", "crm.deals", {}, use_cache=False, transport=self._tr(200, {"error": "expired_token"}))
            self.assertEqual((e["status"], e["code"], e["health"]), ("FAILED", "AUTH_FAILED", "AUTH_FAILED")); self.assertNotIn("s3cr3t", json.dumps(e))
        finally: os.environ.pop("CC_INT_B24_WEBHOOK_URL", None)

class I06_Secrets(unittest.TestCase):
    @covers("data_sensitivity_awareness", *GOV, kinds=("adversarial", "failure_injection", "unit"))
    def test_secret_never_leaks_into_envelope_health_cache_or_audit(self):
        code = "wh00kS3cretC0deXYZ987"; url = f"https://portal.example.invalid/rest/7/{code}/"
        os.environ["CC_INT_B24_WEBHOOK_URL"] = url; os.environ["CC_INT_B24_PORTAL_DOMAIN"] = "portal.example.invalid"
        try:
            cfg = _secrets.load_config("INT-B24"); self.assertEqual(cfg["webhook_url"], url); self.assertGreaterEqual(_secrets.known_count(), 1)
            self.assertNotIn(code, _secrets.redact(f"error at {url}")); self.assertEqual(_secrets.leaks({"x": "clean"}), []); self.assertTrue(_secrets.leaks({"x": url}))
            def leaky(u, timeout=20): return 200, json.dumps({"error": "invalid_token", "error_description": f"bad token at {u}"})
            e = layer.query("INT-B24", "crm.deals", {}, use_cache=False, transport=leaky)
            self.assertEqual(e["code"], "AUTH_FAILED"); self.assertNotIn(code, json.dumps(e)); self.assertNotIn(code, json.dumps(health.snapshot())); self.assertNotIn(code, json.dumps(engine.read_audit(5), default=str))
            def leaky_ok(u, timeout=20): return 200, json.dumps({"result": [{"ID": "1", "TITLE": f"see {u}", "STAGE_ID": "NEW", "ASSIGNED_BY_ID": "1", "DATE_MODIFY": "2026-09-10T10:00:00"}]})
            e = layer.query("INT-B24", "crm.deals", {}, use_cache=False, transport=leaky_ok)
            self.assertEqual((e["status"], e["code"]), ("FAILED", "LEAK_PREVENTED")); self.assertEqual(e["records"], []); self.assertNotIn(code, json.dumps(e))
            cache = layer._cache_path(); self.assertTrue(not cache.exists() or code not in cache.read_text(encoding="utf-8"))
        finally:
            os.environ.pop("CC_INT_B24_WEBHOOK_URL", None); os.environ.pop("CC_INT_B24_PORTAL_DOMAIN", None)
    @covers("data_sensitivity_awareness", *GOV, kinds=("unit",))
    def test_secrets_live_outside_git_and_repo_carries_none(self):
        self.assertFalse(str(_secrets.home_dir()).startswith(str(ROOT)))
        out = subprocess.run(["git", "ls-files", ".claude/integrations"], cwd=str(ROOT), capture_output=True, text=True).stdout.split()
        self.assertFalse([p for p in out if p.endswith(".json")], out)
        import sensitive_scan as ss; pol = ss.load_policy()
        for py in sorted((ROOT / ".claude" / "integrations").glob("*.py")) + [ROOT / ".claude" / "integrations" / "outlook_read.ps1"]:
            fs = [f for f in ss.scan_content(f".claude/integrations/{py.name}", py.read_text(encoding="utf-8"), pol, names=[]) if f["class"] == "RESTRICTED"]
            self.assertEqual(fs, [], py.name)
        self.assertEqual(ss.classify_path(".claude/integrations/certification.json", pol)[0], "INTERNAL"); self.assertEqual(ss.classify_path(".claude/integrations/cache.json", pol)[0], "CONFIDENTIAL")

class I07_HealthAndTasks(unittest.TestCase):
    @covers("task_management", "deadline_management", *GOV, kinds=("unit", "completion"))
    def test_task_register_real_read_records_real_health(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        _clear_cache(); before = (health.get("INT-TASKS") or {}).get("success_count", 0)
        e = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=False)
        self.assertEqual(e["status"], "OK"); self.assertEqual(e["mode"], "REAL"); self.assertEqual(C.check_records("task", e["records"]), []); self.assertTrue(all(r["open"] for r in e["records"]))
        self.assertEqual(e["count"], len([t for t in executors.load_tasks() if t["open"]]))      # one loader, one truth — no competing task source
        h = health.get("INT-TASKS"); self.assertEqual(h["status"], "AVAILABLE"); self.assertEqual(h["success_count"], before + 1); self.assertTrue(h["last_success"]); self.assertEqual(h["consecutive_failures"], 0)
    @covers("task_management", *GOV, kinds=("failure", "failure_injection"))
    def test_schema_drift_and_missing_file_fail_closed(self):
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = executors.SHEET; ws.cell(row=executors.HDR_ROW, column=executors.COL["id"], value="ID-WRONG"); p = TMP / "Drift.xlsx"; wb.save(p)
        e = layer.query("INT-TASKS", "tasks.list", {"path": str(p)}, use_cache=False); self.assertEqual((e["status"], e["code"], e["health"]), ("FAILED", "SCHEMA_CHANGED", "SCHEMA_CHANGED"))
        e = layer.query("INT-TASKS", "tasks.list", {"path": str(TMP / "missing.xlsx")}, use_cache=False); self.assertEqual(e["code"], "UNAVAILABLE")
        self.assertEqual(health.get("INT-TASKS")["consecutive_failures"], 2)
    @covers(*GOV, kinds=("unit",))
    def test_status_lines_carry_health_certification_and_unblock(self):
        st = {s["integration_id"]: s for s in layer.status()}
        self.assertEqual(set(st), set(registry.INTEGRATIONS)); self.assertTrue(st["INT-B24"]["unblock"]); self.assertEqual(st["INT-B24"]["write_ops"], []); self.assertIn(st["INT-MB"]["certification"], ("DECLARED",))
        ls = layer.live_source_status(("sales", "operations")); self.assertEqual([s["integration_id"] for s in ls["sales"]], ["INT-B24", "INT-MB"]); self.assertIn("INT-TASKS", [s["integration_id"] for s in ls["operations"]])

class I08_DailyBriefLive(unittest.TestCase):
    @covers("daily_briefing", "executive_prioritization", "deadline_management", "waiting_for_tracking", *GOV, kinds=("unit", "completion"))
    def test_brief_consumes_live_calendar_and_mail_without_creating_facts(self):
        _clear_cache(); before = len(engine._store().list("commitments"))
        with Fixture(LIVE):
            r = engine.run_skill(REG, "daily_briefing", {"today": T}, intent="daily brief")
        self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(r["validated"]); self.assertTrue(r["verification"]["ok"]); b = r["result"]
        secs = {s["id"]: s for s in b["sections"]}
        self.assertIn("TODAY", secs); self.assertEqual([i["kind"] for i in secs["TODAY"]["items"]][:2], ["meeting", "meeting"]); self.assertEqual(b["live"]["mode"], "FIXTURE"); self.assertEqual(len(b["live"]["meetings_today"]), 2); self.assertEqual(len(b["live"]["meetings_upcoming"]), 1)
        self.assertTrue(any(x["kind"] == "SCHEDULE_CONFLICT" for x in b["risks"])); self.assertIn("PREPARATION", secs); self.assertTrue(all(s["items"] for s in b["sections"]))
        self.assertTrue(any(i["kind"] == "email" and i["class"] == "ACTION" for i in secs["WAITING_FOR"]["items"])); self.assertTrue(any(i["kind"] == "email" for i in secs["DECISIONS"]["items"]))
        self.assertFalse(any("Password" in i["text"] for s in b["sections"] for i in s["items"]))       # IGNORE class never surfaces
        self.assertNotIn("SALES", secs); self.assertNotIn("OPERATIONS", secs)                              # no verified live sales/ops source → no noisy empty section
        self.assertTrue(any("no VERIFIED live source" in g for g in b["data_gaps"])); self.assertTrue(b["business_context"]["available"] or b["business_context"]["gaps"])
        self.assertEqual(len(engine._store().list("commitments")), before); self.assertTrue(all(m["record_id"].startswith("INT-OL-CAL:") for m in b["live"]["meetings_today"]))
        self.assertEqual(b["live"]["email_candidates_total"], 4); self.assertEqual(len([c for c in b["live"]["email_candidates"] if c["duplicate_of"]]), 0)   # conversation duplicate collapsed
    @covers("daily_briefing", *GOV, kinds=("failure", "failure_injection", "completion"))
    def test_unavailable_critical_integration_is_reported_not_omitted(self):
        _clear_cache()
        with Fixture({"INT-OL-CAL": {"error": "AUTH_FAILED", "reason": "profile locked"}, "INT-OL-MAIL": LIVE["INT-OL-MAIL"]}):
            r = engine.run_skill(REG, "daily_briefing", {"today": T}, intent="daily brief")
        self.assertEqual(r["status"], "EXECUTED"); b = r["result"]
        self.assertEqual(b["live"]["critical_unavailable"], ["INT-OL-CAL"]); risk = next(x for x in b["risks"] if x["kind"] == "INTEGRATION_DOWN")
        self.assertIn("AUTH_FAILED", risk["text"]); self.assertIn("last successful read", risk["text"]); self.assertEqual(b["live"]["meetings_today"], [])
        # a brief that silently drops an unavailable critical integration is INVALID
        bad = dict(b); bad["risks"] = [x for x in b["risks"] if x["kind"] != "INTEGRATION_DOWN"]; self.assertFalse(executors.validate_output("daily_briefing", bad)[0])
    @covers("daily_briefing", *GOV, kinds=("failure",))
    def test_layer_down_is_explicit(self):
        r = executors.daily_briefing({"today": T, "live_context": {"available": False, "reason": "integration layer unavailable: ImportError", "health_lines": [], "unavailable": [], "critical_unavailable": []}})
        self.assertEqual(r["live"]["available"], False); self.assertTrue(any(x["kind"] == "INTEGRATION_LAYER_DOWN" for x in r["risks"])); self.assertTrue(executors.validate_output("daily_briefing", r)[0])

class I09_MeetingPrepAndOpenLoops(unittest.TestCase):
    @covers("meeting_preparation", *GOV, kinds=("unit", "completion"))
    def test_meeting_pack_from_live_calendar_with_related_context(self):
        _clear_cache()
        with Fixture(LIVE):
            r = engine.run_skill(REG, "meeting_preparation", {"today": T, "meeting": "Sales Review", "tasks": [{"id": 1, "task": "Sales Review deck: D2D activations", "status": "Ընթացքում", "owner": "Գև", "due": "2026-09-12"}]}, intent="prepare me for the sales review")
        self.assertEqual(r["status"], "EXECUTED"); res = r["result"]; cal = res["calendar"]
        self.assertTrue(cal["found"]); self.assertEqual(cal["source"], "INT-OL-CAL"); self.assertIn("Arman Tester", res["participants"]); self.assertEqual(res["when"], f"{T}T10:00:00")
        self.assertTrue(cal["related_tasks"]); self.assertTrue(cal["recommended_agenda"]); self.assertIn("D2D", cal["purpose"]); self.assertTrue(cal["context_found"])
        with Fixture(LIVE):
            r2 = engine.run_skill(REG, "meeting_preparation", {"today": T, "meeting": "Budget sync", "tasks": []}, intent="prepare me for the budget sync")
        c2 = r2["result"]["calendar"]; self.assertTrue(c2["found"]); self.assertFalse(c2["context_found"]); self.assertIn("fabricated", c2["note"]); self.assertTrue(c2["missing_preparation"])
        _clear_cache()
        with Fixture({"INT-OL-CAL": {"error": "UNAVAILABLE"}, "INT-OL-MAIL": {"records": []}}):
            r3 = engine.run_skill(REG, "meeting_preparation", {"today": T, "meeting": "Sales Review", "tasks": []}, intent="prepare me")
        self.assertFalse(r3["result"]["calendar"]["found"]); self.assertIn("UNKNOWN", r3["result"]["participants"])
    @covers("open_loop_memory", "commitment_memory", *GOV, kinds=("unit", "completion"))
    def test_open_loops_extract_candidates_not_facts(self):
        _clear_cache(); before = len(engine._store().list("commitments"))
        with Fixture(LIVE):
            r = engine.run_skill(REG, "open_loop_memory", {"today": T}, intent="what's open")
        self.assertEqual(r["status"], "EXECUTED"); res = r["result"]; cands = res["email_candidates"]
        self.assertEqual({c["class"] for c in cands} & {"ACTION", "DECISION"}, {"ACTION", "DECISION"}); self.assertTrue(all(c["kind"] == "CANDIDATE_OPEN_LOOP" and c["permanent"] is False for c in cands))
        self.assertTrue(any(c["duplicate_of"] for c in cands)); self.assertFalse(any("noreply" in c["counterpart_address"] for c in cands)); self.assertEqual(len(engine._store().list("commitments")), before)
        self.assertTrue(all(c["evidence"]["integration_id"] == "INT-OL-MAIL" for c in cands)); self.assertIn("INT-OL-MAIL", res["email_source"])

class I10_Reconciliation(unittest.TestCase):
    @covers("source_reconciliation", "confidence_handling", *GOV, kinds=("unit", "failure"))
    def test_fact_authority_conflict_and_precedence(self):
        same = reconcile.reconcile_fact("meeting_time", [{"source": "INT-OL-CAL", "value": "10:00"}, {"source": "INT-OL-CAL", "value": "11:00"}])
        self.assertEqual(same["status"], "SOURCE_CONFLICT"); self.assertEqual(same["label"], "UNKNOWN"); self.assertEqual(len(same["observations"]), 2)
        diff = reconcile.reconcile_fact("register_task_status", [{"source": "INT-OL-MAIL", "value": "done"}, {"source": "INT-TASKS", "value": "Ընթացքում"}, {"source": "INT-B24", "value": "closed"}])
        self.assertEqual((diff["status"], diff["source"], diff["value"]), ("RESOLVED", "INT-TASKS", "Ընթացքում")); self.assertEqual({o["source"] for o in diff["overridden"]}, {"INT-OL-MAIL"}); self.assertEqual(diff["unconfigured_sources_ignored"], ["INT-B24"]); self.assertEqual(len(diff["observations"]), 3)
        self.assertEqual(reconcile.reconcile_fact("meeting_time", [])["status"], "NO_OBSERVATION"); self.assertEqual(reconcile.reconcile_fact("net_promoter_score", [{"source": "INT-B24", "value": 1}])["status"], "AUTHORITY_UNDEFINED")
        ign = reconcile.reconcile_fact("meeting_time", [{"source": "INT-XX", "value": "9:00"}, {"source": "INT-TASKS", "value": "10:00"}]); self.assertEqual(ign["unconfigured_sources_ignored"], ["INT-XX"]); self.assertEqual(ign["source"], "INT-TASKS")
    @covers("source_reconciliation", *GOV, kinds=("unit",))
    def test_entity_linking_is_conservative(self):
        self.assertEqual(reconcile.link_entities({"name": "A B", "address": "x@example.test"}, {"name": "C D", "address": "X@example.test"})["status"], "MATCH")
        self.assertEqual(reconcile.link_entities({"name": "Arman Petrosyan"}, {"name": "arman  petrosyan"})["status"], "MATCH")
        self.assertEqual(reconcile.link_entities({"name": "Arman Petrosyan"}, {"name": "Arman Sargsyan"})["status"], "ENTITY_MATCH_UNCERTAIN")
        self.assertEqual(reconcile.link_entities({"name": "Arman"}, {"name": "Arman"})["status"], "ENTITY_MATCH_UNCERTAIN")      # single token is never a merge
        self.assertEqual(reconcile.link_entities({"name": "Zorbulak"}, {"name": "Fixturina"})["status"], "NO_MATCH")
    @covers("open_loop_memory", *GOV, kinds=("unit",))
    def test_message_classification_and_candidates(self):
        cl = lambda s, p, f="x@example.test": reconcile.classify_message({"subject": s, "preview": p, "sender": f})["class"]
        self.assertEqual(cl("Password Changed", "x", "noreply@example.test"), "IGNORE"); self.assertEqual(cl("Accepted: Sales Review", "", "a@example.test"), "IGNORE")
        self.assertEqual(cl("Discount", "We need your approval for the discount"), "DECISION"); self.assertEqual(cl("Doc", "Can you send me the file by Friday?"), "ACTION")
        self.assertEqual(cl("Support", "Please assign someone from your team to this"), "DELEGATE"); self.assertEqual(cl("Status", "Work is in progress, will update Monday"), "MONITOR")
        self.assertEqual(cl("Note", "FYI no action needed"), "FYI"); self.assertEqual(cl("Հարց", "Խնդրում եմ ուղարկել փաստաթուղթը մինչև ուրբաթ"), "ACTION")
        own = reconcile.classify_message({"subject": "Re: report", "preview": "I will send the report by Friday", "sender": "gev@example.test"}, head_addresses=["gev@example.test"]); self.assertEqual(own["class"], "MONITOR"); self.assertTrue(own["commitment_candidate"])
        cands = reconcile.open_loop_candidates(LIVE["INT-OL-MAIL"]["records"], tasks=[{"id": 13, "title": "Retention flow tracking document", "owner": "Գև"}], commitments=[], decisions=[], today=T)
        c5 = next(c for c in cands if c["evidence"]["record_id"] == "INT-OL-MAIL:e5"); self.assertEqual(c5["task_match"], "MATCHED"); self.assertEqual(c5["matched_task"]["id"], 13); self.assertEqual(c5["age_days"], 1); self.assertIsNone(c5["duplicate_of"])
        c1 = next(c for c in cands if c["evidence"]["record_id"] == "INT-OL-MAIL:e1"); self.assertEqual(c1["duplicate_of"], c5["candidate_id"])      # older message of the same conversation = duplicate of the latest

class I11_Certification(unittest.TestCase):
    @covers(*GOV, "data_sensitivity_awareness", kinds=("unit", "completion", "failure_injection"))
    def test_states_follow_evidence_and_fixture_reads_never_certify(self):
        _clear_cache(); out = TMP / "cert.json"
        with Fixture(LIVE):
            rec = certify_integrations.certify(real=True, out=out)
        self.assertTrue(out.exists()); ints = rec["integrations"]
        self.assertEqual(ints["INT-MB"]["state"], "DECLARED"); self.assertIn(ints["INT-B24"]["state"], ("DECLARED", "CONFIGURED"))
        for iid in ("INT-OL-CAL", "INT-OL-MAIL"): self.assertEqual(ints[iid]["state"], "CONFIGURED", iid)      # fixture reads are labelled, not evidence
        self.assertIn(ints["INT-TASKS"]["state"], ("VERIFIED_READ", "CONNECTED")); self.assertNotEqual(ints["INT-TASKS"]["state"], "RELIABLE_READ")   # one certification run is not reliability
        for iid, r in ints.items():
            self.assertTrue(r["evidence"]["write_rejected"], iid); self.assertEqual(r["write_ops"], [])
            if r["read_ops"]: self.assertTrue(r["evidence"]["failure_behavior_tested"], iid)
        self.assertEqual(rec["registry_problems"], []); self.assertNotIn("s3cr3t", out.read_text(encoding="utf-8"))
        self.assertEqual(set(C.CERT_STATES), {"DECLARED", "CONFIGURED", "CONNECTED", "VERIFIED_READ", "RELIABLE_READ"})
    @covers(*GOV, kinds=("unit",))
    def test_real_outlook_read_when_available(self):
        try: p = adapter_outlook.probe()
        except C.IntegrationError as e: self.skipTest(f"Outlook not reachable here: {e.code} — {e.reason[:80]}")
        self.assertTrue(p["identity"]["verified"] is not False); _clear_cache()
        e = layer.query("INT-OL-MAIL", "mail.list", {"folder": "Inbox", "limit": 3, "preview_chars": 40}, use_cache=False)
        self.assertEqual(e["status"], "OK"); self.assertEqual(e["mode"], "REAL"); self.assertEqual(C.check_records("message", e["records"]), []); self.assertTrue(all(len(r["preview"]) <= 41 for r in e["records"]))
        self.assertTrue(health.get("INT-OL-MAIL")["last_success"])

class I12_AuditAndPrivacy(unittest.TestCase):
    @covers("audit_logging", *GOV, kinds=("unit", "enforcement"))
    def test_audit_records_what_was_queried_not_the_payload(self):
        _clear_cache()
        with Fixture(LIVE): layer.query("INT-OL-MAIL", "mail.list", {"folder": "Sent", "unread_only": True}, use_cache=False)
        recs = [r for r in engine.read_audit(20) if str(r.get("skill_id", "")).startswith("<integration:INT-OL-MAIL>") and sorted(r.get("param_keys") or []) == ["folder", "unread_only"]]
        self.assertTrue(recs); a = recs[-1]
        self.assertEqual(a["op"], "mail.list"); self.assertEqual(a["count"], 5); self.assertEqual(a["mode"], "FIXTURE")
        self.assertNotIn("retention flow", json.dumps(a, ensure_ascii=False)); self.assertNotIn("maga@", json.dumps(a, ensure_ascii=False))
    @covers("data_sensitivity_awareness", *GOV, kinds=("unit",))
    def test_cache_is_minimal_and_in_state_dir(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        _clear_cache(); layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True)
        p = layer._cache_path(); self.assertTrue(str(p).startswith(str(engine.STATE_DIR))); d = json.loads(p.read_text(encoding="utf-8")); self.assertEqual(len(d), 1)
        self.assertEqual(set(next(iter(d.values()))), {"retrieved_at", "records", "source_updated_at", "identity", "mode", "expires_at"})       # minimal: last result only, hard expiry, no history
        import sensitive_scan as ss; self.assertEqual(ss.classify_path(".claude/state/integrations_cache.json", ss.load_policy())[0], "CONFIDENTIAL")

# ═══════════════════ external audit of c3ffda1 — regression tests per finding ═══════════════════
class A01_ConfidentialCache(unittest.TestCase):
    """Finding 1 — mailbox/calendar payloads never persist; persisted entries carry a hard expiry enforced on load/startup."""
    @covers("daily_briefing", "open_loop_memory", "data_sensitivity_awareness", *GOV, kinds=("unit", "failure_injection", "adversarial"))
    def test_mail_payload_never_written_to_disk_and_expired_entries_are_unrecoverable(self):
        _clear_cache(); layer._MEM.clear()
        for iid in ("INT-OL-MAIL", "INT-OL-CAL"): self.assertFalse(registry.get(iid)["freshness"]["persist"], iid)
        self.assertTrue(registry.get("INT-TASKS")["freshness"]["persist"])
        # a real-mode mail read through the memory path (adapter monkeypatched → no Outlook needed) must not touch the disk cache
        import adapter_outlook
        secret_preview = "CONFIDENTIAL-PREVIEW-" + "zq7"
        def fake_read(op, params=None, cfg=None, integration_id=None):
            return {"records": [_msg("Hello", "x@example.test", secret_preview, "mm1")], "source_updated_at": None, "identity": {"addresses": ["gev@housenet.am"], "verified": True}, "partial": False, "notes": []}
        old = adapter_outlook.read; adapter_outlook.read = fake_read
        try:
            e1 = layer.query("INT-OL-MAIL", "mail.list", {"folder": "Inbox"}, use_cache=True); self.assertEqual((e1["status"], e1["mode"]), ("OK", "REAL"))
            e2 = layer.query("INT-OL-MAIL", "mail.list", {"folder": "Inbox"}, use_cache=True); self.assertEqual(e2["freshness"], "CACHED")   # memory-only hit
        finally: adapter_outlook.read = old
        p = layer._cache_path(); self.assertFalse(p.exists() and secret_preview in p.read_text(encoding="utf-8"))
        self.assertFalse(p.exists(), "mail read created a persistent cache file")
        k = next(iter(layer._MEM)); self.assertIn(secret_preview, json.dumps(layer._MEM[k]))
        layer._MEM[k]["expires_at"] = "2000-01-01T00:00:00"                      # expire it → unrecoverable from normal runtime paths
        self.assertIsNone(layer._cache_get("INT-OL-MAIL", k)); self.assertNotIn(k, layer._MEM)
        self.assertIn(k, layer.prune_cache() + [k])
        # a legacy/foreign persistent entry carrying mail payload is destroyed on the very next load (not only after a later successful query)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"INT-OL-MAIL|mail.list|abc": {"retrieved_at": "2026-09-11T00:00:00", "expires_at": "2999-01-01T00:00:00", "records": [{"preview": secret_preview}], "mode": "REAL"},
                                 "INT-TASKS|tasks.list|old": {"retrieved_at": "2026-09-11T00:00:00", "expires_at": "2000-01-01T00:00:00", "records": [{"title": "expired"}], "mode": "REAL"},
                                 "INT-TASKS|tasks.list|noexp": {"retrieved_at": "2026-09-11T00:00:00", "records": [{"title": "legacy without expiry"}], "mode": "REAL"}}), encoding="utf-8")
        loaded = layer._cache_load(); self.assertEqual(loaded, {})
        self.assertFalse(p.exists() and (secret_preview in p.read_text(encoding="utf-8") or "expired" in p.read_text(encoding="utf-8")))
        e = layer.query("INT-OL-MAIL", "mail.list", {"folder": "Inbox"}, use_cache=True) if False else None   # (no live call needed)
    @covers("task_management", *GOV, kinds=("unit", "failure_injection"))
    def test_persistent_register_cache_has_hard_expiry_on_startup(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        _clear_cache()
        layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True)
        p = layer._cache_path(); d = json.loads(p.read_text(encoding="utf-8")); k = next(iter(d)); self.assertTrue(d[k]["expires_at"] > d[k]["retrieved_at"])
        d[k]["expires_at"] = "2000-01-01T00:00:00"; p.write_text(json.dumps(d), encoding="utf-8")
        dropped = layer.prune_cache(); self.assertIn(k, dropped); self.assertFalse(p.exists())
        e = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True); self.assertEqual(e["freshness"], "LIVE")   # expired entry was never served

class A02_AuditFailClosed(unittest.TestCase):
    """Finding 2 — a CONFIDENTIAL read without persisted, re-readable governed audit evidence is not a successful read."""
    def _with_broken_audit(self, fn, how):
        if how == "raise":
            orig = engine.audit
            def broken(rec): raise RuntimeError("audit store offline")
            engine.audit = broken
        else:
            st = engine._store(); orig = st.get
            st.get = lambda table, key: None if table == "audit" else orig(table, key)
        try: return fn()
        finally:
            if how == "raise": engine.audit = orig
            else: engine._store().get = orig
    @covers("audit_logging", "completion_verification", "task_management", *GOV, kinds=("failure", "failure_injection", "enforcement"))
    def test_real_read_withheld_when_audit_cannot_be_persisted_or_reread(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        _clear_cache(); before = (health.get("INT-TASKS") or {}).get("success_count", 0); before_af = (health.get("INT-TASKS") or {}).get("audit_failures", 0)
        for how in ("raise", "reread"):
            e = self._with_broken_audit(lambda: layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=False), how)
            self.assertEqual((e["status"], e["code"], e["records"], e["health"]), ("FAILED", "AUDIT_UNAVAILABLE", [], "DEGRADED"), how)
            self.assertIn("withheld", e["reason"]); self.assertFalse(e.get("audit_recorded"))
        h = health.get("INT-TASKS"); self.assertEqual(h["success_count"], before); self.assertEqual(h["audit_failures"], before_af + 2)    # no success evidence without audit (health accumulates across tests)
        ok = layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=False)
        self.assertEqual(ok["status"], "OK"); self.assertTrue(ok["audit_id"]); self.assertTrue(engine._store().get("audit", ok["audit_id"]))
        self.assertEqual(health.get("INT-TASKS")["success_count"], before + 1)
    @covers("audit_logging", "daily_briefing", *GOV, kinds=("failure", "failure_injection"))
    def test_fixture_and_cached_reads_also_fail_closed_and_brief_reports_it(self):
        _clear_cache()
        with Fixture(LIVE):
            e = self._with_broken_audit(lambda: layer.query("INT-OL-CAL", "calendar.events", {"from": T, "to": T}, use_cache=False), "raise")
            self.assertEqual((e["status"], e["code"]), ("FAILED", "AUDIT_UNAVAILABLE")); self.assertEqual(e["records"], [])
            r = self._with_broken_audit(lambda: executors.daily_briefing({"today": T}), "raise")
        self.assertEqual(r["live"]["critical_unavailable"], ["INT-OL-CAL"]); self.assertTrue(any("AUDIT_UNAVAILABLE" in x["text"] for x in r["risks"]))
        if (ROOT / "Tasks.xlsx").exists():
            layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True)
            c = self._with_broken_audit(lambda: layer.query("INT-TASKS", "tasks.list", {"open_only": True}, use_cache=True), "raise")
            self.assertEqual((c["status"], c["code"], c["records"]), ("FAILED", "AUDIT_UNAVAILABLE", []))          # even a cache hit needs its audit
    @covers("audit_logging", *GOV, kinds=("unit",))
    def test_audit_helper_is_consistent_with_core_store(self):
        aid = layer._audit({"integration_id": "INT-TASKS", "op": "probe", "result_status": "OK"})
        self.assertTrue(aid); rec = engine._store().get("audit", aid); self.assertTrue(rec)
        self.assertEqual(rec["skill_id"] if "skill_id" in rec else rec.get("payload", {}).get("skill_id"), "<integration:INT-TASKS>")
        with self.assertRaises(layer.AuditUnavailable): self._with_broken_audit(lambda: layer._audit({"integration_id": "INT-TASKS", "op": "x", "result_status": "OK"}), "raise")
        self.assertIsNone(self._with_broken_audit(lambda: layer._audit({"integration_id": "INT-TASKS", "op": "x", "result_status": "FAILED"}, required=False), "raise"))

class A03_TaskAuthorityScope(unittest.TestCase):
    """Finding 3 — register tasks and Bitrix-native tasks are separate scopes; no stale manual status overrides a system of record."""
    @covers("source_reconciliation", "task_management", "confidence_handling", *GOV, kinds=("unit", "failure"))
    def test_scoped_hierarchies(self):
        self.assertNotIn("task_status", registry.FACT_AUTHORITY); self.assertNotIn("task_deadline", registry.FACT_AUTHORITY)
        for ft in ("register_task_status", "register_task_deadline", "crm_task_status", "crm_task_deadline"):
            fa = registry.FACT_AUTHORITY[ft]; self.assertTrue(fa.get("scope") and fa.get("system_of_record"), ft)
        self.assertEqual(registry.FACT_AUTHORITY["crm_task_status"]["tiers"], [["INT-B24"]]); self.assertNotIn("INT-B24", sum(registry.FACT_AUTHORITY["register_task_status"]["tiers"], []))
        obs = [{"source": "INT-TASKS", "value": "Ընթացքում", "record_id": "INT-TASKS:1"}, {"source": "INT-B24", "value": "5", "record_id": "INT-B24:9"}, {"source": "INT-OL-MAIL", "value": "done?"}]
        crm = reconcile.reconcile_fact("crm_task_status", obs)
        self.assertEqual((crm["status"], crm["source"], crm["value"], crm["system_of_record"]), ("RESOLVED", "INT-B24", "5", "INT-B24")); self.assertEqual(set(crm["unconfigured_sources_ignored"]), {"INT-TASKS", "INT-OL-MAIL"}); self.assertEqual(crm["overridden"], [])
        reg = reconcile.reconcile_fact("register_task_status", obs)
        self.assertEqual((reg["status"], reg["source"], reg["value"]), ("RESOLVED", "INT-TASKS", "Ընթացքում")); self.assertIn("INT-B24", reg["unconfigured_sources_ignored"])
        amb = reconcile.reconcile_fact("task_status", obs); self.assertEqual(amb["status"], "AUTHORITY_UNDEFINED"); self.assertIn("scoped", amb["reason"])
    @covers("source_reconciliation", "task_management", *GOV, kinds=("unit", "failure"))
    def test_cross_system_link_keeps_both_statuses_and_flags_divergence(self):
        reg = {"status": "Ընթացքում", "due": "2026-09-12", "record_id": "INT-TASKS:1"}; crm = {"status": "5", "deadline": "2026-09-10T18:00:00", "record_id": "INT-B24:9"}
        link = reconcile.reconcile_task_link(reg, crm, {"status": "MATCH"})
        self.assertEqual((link["status"], link["code"], link["divergent"], link["override"]), ("LINKED", "STATUS_DIVERGENCE", True, None))
        self.assertEqual(link["register"]["status"], "Ընթացքում"); self.assertEqual(link["crm"]["status"], "5"); self.assertEqual(link["label"], "UNKNOWN"); self.assertIn("writes nothing", link["resolution_required"])
        same = reconcile.reconcile_task_link(reg, {**crm, "status": "Ընթացքում"}, {"status": "MATCH"}); self.assertFalse(same["divergent"]); self.assertNotIn("code", same)
        unc = reconcile.reconcile_task_link(reg, crm, {"status": "ENTITY_MATCH_UNCERTAIN"}); self.assertEqual(unc["status"], "ENTITY_MATCH_UNCERTAIN"); self.assertNotIn("code", unc)
        self.assertEqual(reconcile.reconcile_task_link(reg, None, {"status": "NO_MATCH"})["status"], "UNLINKED")
    @covers("source_reconciliation", *GOV, kinds=("unit",))
    def test_business_model_carries_scoped_live_authority(self):
        import business
        m = business.load()
        if not m: self.skipTest("business model not built")
        fa = m["sources"]["live_sources"]["fact_authority"]; self.assertIn("crm_task_status", fa); self.assertNotIn("task_status", fa)

class A04_CertificationScope(unittest.TestCase):
    """Finding 4 — scope_verified only when EVERY required operation succeeded as a REAL read."""
    @covers("completion_verification", *GOV, kinds=("unit", "failure_injection", "completion"))
    def test_required_ops_declared_and_subset_never_verifies(self):
        for iid, spec in registry.INTEGRATIONS.items():
            self.assertIn("required_certification_ops", spec, iid); self.assertTrue(set(spec["required_certification_ops"]) <= set(spec["read_ops"]), iid)
            if spec["read_ops"]: self.assertTrue(spec["required_certification_ops"], iid)
        self.assertEqual(registry.INTEGRATIONS["INT-OL-MAIL"]["required_certification_ops"], ["mail.list", "mail.search"]); self.assertGreaterEqual(len(registry.INTEGRATIONS["INT-B24"]["required_certification_ops"]), 3)
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        _clear_cache(); spec = registry.INTEGRATIONS["INT-TASKS"]; saved = list(spec["required_certification_ops"]); saved_ops = dict(spec["read_ops"])
        spec["read_ops"]["tasks.history"] = {"kind": "task", "params": []}; spec["required_certification_ops"] = ["tasks.list", "tasks.history"]      # second scope exists but cannot be read for real
        out = TMP / "cert_scope.json"
        try: rec = certify_integrations.certify(real=True, out=out)
        finally: spec["required_certification_ops"] = saved; spec["read_ops"] = saved_ops
        r = rec["integrations"]["INT-TASKS"]
        self.assertEqual(r["state"], "CONNECTED"); self.assertFalse(r["evidence"]["scope_verified"]); self.assertTrue(r["ops_proof"]["tasks.list"]["ok"]); self.assertFalse(r["ops_proof"]["tasks.history"]["ok"])
        self.assertTrue(any("scope NOT verified" in n for n in r["notes"]))
        rec2 = certify_integrations.certify(real=True, out=out); self.assertEqual(rec2["integrations"]["INT-TASKS"]["state"], "VERIFIED_READ"); self.assertEqual(list(rec2["integrations"]["INT-TASKS"]["ops_proof"]), ["tasks.list"])
    @covers("completion_verification", *GOV, kinds=("failure_injection",))
    def test_fixture_success_on_every_required_op_is_not_scope_proof(self):
        _clear_cache(); out = TMP / "cert_fixture.json"
        with Fixture({"INT-OL-MAIL": {"mail.list": {"records": LIVE["INT-OL-MAIL"]["records"]}, "mail.search": {"records": LIVE["INT-OL-MAIL"]["records"][:1]}}, "INT-OL-CAL": LIVE["INT-OL-CAL"]}):
            rec = certify_integrations.certify(real=True, out=out)
        for iid in ("INT-OL-MAIL", "INT-OL-CAL"):
            r = rec["integrations"][iid]; self.assertEqual(r["state"], "CONFIGURED", iid); self.assertFalse(r["evidence"]["scope_verified"]); self.assertTrue(all(p["mode"] == "FIXTURE" and not p["ok"] for p in r["ops_proof"].values()))

class A05_Concurrency(unittest.TestCase):
    """Finding 5 — parallel reads never lose health evidence; the persistent cache survives concurrent writers."""
    @covers("audit_logging", "completion_verification", *GOV, kinds=("concurrency", "unit"))
    def test_parallel_threads_and_processes_keep_every_success(self):
        import concurrent.futures
        iid = "INT-CONC-TEST"; base = (health.get(iid) or {}).get("success_count", 0)
        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            list(ex.map(lambda i: health.record(iid, True, op="t", mode="REAL"), range(160)))
        code = ("import sys; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s'); import engine, health; engine.STATE_DIR = __import__('pathlib').Path(r'%s')\n"
                "[health.record('%s', True, op='p', mode='REAL') for _ in range(25)]") % (str(ROOT / ".claude" / "integrations"), str(ROOT / ".claude" / "skills"), str(engine.STATE_DIR), iid)
        procs = [subprocess.Popen([sys.executable, "-c", code]) for _ in range(4)]
        for pr in procs: self.assertEqual(pr.wait(timeout=120), 0)
        h = health.get(iid)
        self.assertEqual(h["success_count"], base + 160 + 100); self.assertEqual(h["consecutive_failures"], 0); self.assertTrue(h["last_success"]); self.assertIn(h["last_success"][:10], h["success_days"])
        self.assertFalse(list(engine.STATE_DIR.glob("integrations_health.json.*.tmp")))
    @covers("task_management", *GOV, kinds=("concurrency",))
    def test_parallel_register_reads_keep_cache_and_health_consistent(self):
        if not (ROOT / "Tasks.xlsx").exists(): self.skipTest("Tasks.xlsx absent")
        import concurrent.futures
        _clear_cache(); base = (health.get("INT-TASKS") or {}).get("success_count", 0)
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            envs = list(ex.map(lambda i: layer.query("INT-TASKS", "tasks.list", {"open_only": True, "owner": str(i % 3)}, use_cache=True), range(24)))
        live = [e for e in envs if e["status"] == "OK" and e["freshness"] == "LIVE"]; self.assertTrue(all(e["status"] == "OK" for e in envs), [e.get("code") for e in envs if e["status"] != "OK"])
        self.assertEqual(health.get("INT-TASKS")["success_count"], base + len(live))
        p = layer._cache_path(); d = json.loads(p.read_text(encoding="utf-8")); self.assertEqual(len(d), 3); self.assertTrue(all(v.get("expires_at") for v in d.values()))

if __name__ == "__main__":
    unittest.main(verbosity=2)
