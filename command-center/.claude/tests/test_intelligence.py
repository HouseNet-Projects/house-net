# -*- coding: utf-8 -*-
"""MISSION 5 suite — LIVE SALES & OPERATIONS INTELLIGENCE. Truthfulness (unavailable ≠ no problem · stale ≠ live · cached labelled · conflicts surfaced ·
unknown never invented) · task intelligence (overdue / due today / completed / changed / Gev-owned vs Gev-required / provenance) · change detection
(NEW / CHANGED / RESOLVED / WORSENED, noise suppressed) · cause discipline · impact & priority ranking · recommendation structure · Gev filtering ·
mail/calendar extraction, unavailable behaviour, evidence-only linkage · sales/ops frameworks on fixtures and honest production refusal ·
governance (intelligence never mutates; execution routes to the Action Runtime; approval law untouched) · durability (checkpoint persists,
loops survive restart, resolved loop closes, no shadow truth). Every scenario runs on supplied rows / fixtures; the canonical Tasks.xlsx is never written."""
import unittest, json, os, sys, pathlib, tempfile, shutil, hashlib, datetime, copy
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
for d in ("integrations", "skills", "runtime", "policy"): sys.path.insert(0, str(ROOT / ".claude" / d))
from testing import covers
import engine, store, executors, intelligence as IQ, layer, state_snapshot as ssn
sys.path.insert(0, str(ROOT / '.claude' / 'policy')); import paths as pp   # ONE business-root resolver

TMP = pathlib.Path(tempfile.mkdtemp(prefix="cciq_")); engine.STATE_DIR = TMP / "state"; (TMP / "state").mkdir(parents=True, exist_ok=True); store.reset()
REG = engine.load_registry(); T = "2026-09-12"
REAL = pp.tasks(ROOT); REAL_SHA = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else None
GUARD = TMP / "Tasks-copy.xlsx"; shutil.copy(REAL, GUARD) if REAL.exists() else None
os.environ["COMMAND_CENTER_TASKS_XLSX"] = str(GUARD)                                    # HARD GUARD: the write adapter can only ever touch the temp copy
def setUpModule():
    """Isolation: other suites imported in the same process may have run against this module's import-time store; start from a fresh one."""
    engine.STATE_DIR = TMP / "state-iso"; (TMP / "state-iso").mkdir(parents=True, exist_ok=True); store.reset()
    p = TMP / "state-iso" / "integrations_health.json"
    if p.exists(): p.unlink()
    os.environ["COMMAND_CENTER_TASKS_XLSX"] = str(GUARD)                                # re-applied at run time: another suite imported later may have pointed the guard elsewhere
    os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None); layer._FIXTURE.update(path=None, mtime=None, data=None)
def tearDownModule():
    os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None); layer._FIXTURE.update(path=None, mtime=None, data=None)
    if REAL_SHA and hashlib.sha256(REAL.read_bytes()).hexdigest() != REAL_SHA: raise AssertionError("TEST SUITE MUTATED THE REAL Tasks.xlsx — forbidden")
GOV = ("authority_checking", "approval_management", "completion_verification", "audit_logging")
MS, ER, CR, DQ, DB, OL = "management_snapshot", "exception_review", "change_review", "decision_queue", "daily_briefing", "open_loop_memory"

def tasks():
    return [{"id": 1, "task": "Send the retention flow document", "status": "Ընթացքում", "owner": "Արման", "due": "2026-09-07", "comment": ""},
            {"id": 2, "task": "Approve corporate discount policy", "status": "Չսկսված", "owner": "Գև", "due": T, "comment": ""},
            {"id": 3, "task": "Billing spec from the vendor", "status": "Սպասում", "owner": "Մագա → Գև", "due": "2026-09-09", "comment": ""},
            {"id": 4, "task": "Inspectors do not use the system", "status": "Չսկսված", "owner": "", "due": "2026-09-15", "comment": ""},
            {"id": 5, "task": "Keep or replace the current system", "status": "Ընթացքում", "owner": "ԳԵՎ", "due": "2026-09-14", "comment": ""},
            {"id": 6, "task": "Retention tracking mechanism", "status": "Պարզ չէ", "owner": "Անահիտ", "due": "2026-09-20", "comment": ""},
            {"id": 7, "task": "ԿՐԻՏԻԿԱԿԱՆ — 2% monthly decline question", "status": "Ընթացքում", "owner": "Մագա → Գև", "due": None, "comment": ""},
            {"id": 8, "task": "Delivery schedule sent", "status": "Արված", "owner": "Գև", "due": T, "comment": "done"},
            {"id": 9, "task": "Prepare the weekly review", "status": "Չսկսված", "owner": "Գև", "due": "2026-09-14", "comment": ""}]

def _mt(title, start, end, rid, desc="", parts=("Arman Tester", "Billing Head"), all_day=False):
    return {"record_id": f"INT-OL-CAL:{rid}", "source_record_id": rid, "title": title, "start": start, "end": end, "all_day": all_day, "organizer": "Gev", "participants": [{"name": p, "address": None} for p in parts], "participant_count": len(parts), "location": "Office", "online_link": None, "description_preview": desc, "recurring": False, "source_updated_at": "2026-09-10T09:00:00"}
def _msg(subject, sender, preview, rid, received, conv=None, flagged=False):
    return {"record_id": f"INT-OL-MAIL:{rid}", "source_record_id": rid, "conversation_id": conv or rid, "subject": subject, "sender": sender, "sender_name": sender.split("@")[0], "to": "gev@example.test", "received": received, "unread": True, "importance": 1, "flagged": flagged, "attachments": 0, "preview": preview, "folder": "Inbox", "source_updated_at": received}
LIVE = {"INT-OL-CAL": {"records": [_mt("Discount approval review", f"{T}T10:00:00", f"{T}T11:00:00", "m1", desc="Decide on the corporate discount policy"), _mt("Budget sync", f"{T}T10:30:00", f"{T}T11:30:00", "m2"), _mt("Retention flow status", "2026-09-14T15:00:00", "2026-09-14T16:00:00", "m3", desc="status of the retention flow document")], "identity": {"addresses": ["gev@example.test"], "verified": True}},
        "INT-OL-MAIL": {"records": [_msg("Please send the retention flow document by Friday", "maga@example.test", "Can you send me the retention flow document by Friday? We need it for the review.", "e1", "2026-09-09T10:00:00"),
                                    _msg("Approval needed: corporate discount", "billing@example.test", "We need your approval for the 15% corporate discount before we proceed.", "e2", f"{T}T08:00:00"),
                                    _msg("Password Changed", "noreply@example.test", "Your password was changed.", "e3", f"{T}T07:00:00"),
                                    _msg("FYI: office closed Monday", "hr@example.test", "For your information the office is closed on Monday. No action needed.", "e4", f"{T}T06:00:00")], "identity": {"addresses": ["gev@example.test"], "verified": True}}}
DOWN = {"INT-OL-CAL": {"error": "UNAVAILABLE", "reason": "Outlook desktop not reachable (COM)"}, "INT-OL-MAIL": {"error": "TIMEOUT", "reason": "reader exceeded 90s", "retryable": True}}

class Fixture:
    def __init__(self, data, name="fx"):
        self.p = TMP / f"{name}-{id(self)}.json"; self.p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8"); self.old = None
    def __enter__(self): self.old = os.environ.get("COMMAND_CENTER_INTEGRATIONS_FIXTURE"); os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = str(self.p); return self
    def __exit__(self, *a):
        if self.old is None: os.environ.pop("COMMAND_CENTER_INTEGRATIONS_FIXTURE", None)
        else: os.environ["COMMAND_CENTER_INTEGRATIONS_FIXTURE"] = self.old
        layer._FIXTURE.update(path=None, mtime=None, data=None)

def state(fx=LIVE, rows=None, **extra):
    with Fixture(fx): return IQ.current_state({"today": T, "tasks": rows if rows is not None else tasks(), **extra})

class Q01_Truthfulness(unittest.TestCase):
    @covers(MS, ER, DB, *GOV, kinds=("unit", "failure", "failure_injection"))
    def test_unavailable_is_not_no_problem_and_is_named(self):
        st = state(DOWN); self.assertEqual(st["visibility"]["INT-OL-CAL"]["state"], "UNAVAILABLE"); self.assertEqual(st["visibility"]["INT-OL-MAIL"]["state"], "UNAVAILABLE")
        self.assertIn("INT-OL-CAL", st["unavailable"]); self.assertIn("INT-OL-CAL", st["critical_unavailable"]); self.assertIn("INT-B24", st["unavailable"]); self.assertEqual(st["visibility"]["INT-B24"]["state"], "NOT_CONFIGURED")
        v = IQ.exception_view(st); self.assertTrue(v["visibility_incomplete"]); self.assertIn("INT-OL-CAL", v["note"]); self.assertNotIn("fine", v["verdict"].lower())
        self.assertEqual(IQ.calendar_view(st)["available"], False); self.assertIn("UNKNOWN", IQ.calendar_view(st)["note"]); self.assertEqual(IQ.mail_view(st)["available"], False)
        st2 = state(DOWN, rows=[]); v2 = IQ.exception_view(st2); self.assertEqual(v2["count"], 0); self.assertTrue(v2["visibility_incomplete"]); self.assertIn("INT-B24", v2["note"]); self.assertIn("INT-OL-CAL", v2["note"])    # no exception ≠ everything fine: half the systems are dark
    @covers(MS, DB, *GOV, kinds=("unit", "failure"))
    def test_fixture_and_supplied_data_are_never_production_truth(self):
        st = state(); self.assertTrue(st["truth_mode"].startswith("NON_PRODUCTION")); self.assertEqual(st["visibility"]["INT-OL-CAL"]["state"], "FIXTURE"); self.assertEqual(st["visibility"]["INT-TASKS"]["state"], "SUPPLIED")
        self.assertFalse(st["visibility"]["INT-OL-CAL"]["production_truth"]); self.assertTrue(st["visibility"]["INT-OL-CAL"]["usable"])
        ck = IQ.record_checkpoint(st, "brief"); self.assertEqual(ck["status"], "RECORDED"); self.assertIsNone(IQ.previous_checkpoint())      # non-production checkpoints never feed change detection
    @covers(MS, *GOV, kinds=("unit", "failure_injection"))
    def test_stale_is_not_live_and_cached_is_labelled(self):
        import contracts as C
        cal_ok = C.envelope("INT-OL-CAL", "Outlook", "calendar.events", "meeting", LIVE["INT-OL-CAL"]["records"], authority={"name": "LIVE_SYSTEM"}, classification="CONFIDENTIAL", retrieved_at="2026-09-12T08:00:00", freshness="CACHED", cache_age_seconds=120)
        mail_stale = C.envelope("INT-OL-MAIL", "Outlook", "mail.list", "message", LIVE["INT-OL-MAIL"]["records"], authority={"name": "EVIDENCE"}, classification="CONFIDENTIAL", retrieved_at="2026-09-01T08:00:00", freshness="STALE")
        st = IQ.current_state({"today": T, "tasks": tasks(), "live_context": {"calendar": cal_ok, "mail": mail_stale}})
        self.assertEqual(st["visibility"]["INT-OL-CAL"]["state"], "CACHED"); self.assertEqual(st["visibility"]["INT-OL-CAL"]["cache_age_seconds"], 120); self.assertTrue(st["visibility"]["INT-OL-CAL"]["usable"])
        self.assertEqual(st["visibility"]["INT-OL-MAIL"]["state"], "STALE"); self.assertFalse(st["visibility"]["INT-OL-MAIL"]["usable"]); self.assertIn("INT-OL-MAIL", st["unavailable"])
        self.assertEqual(st["mail_candidates"], [], "stale mail must not feed candidates as current truth")
        self.assertTrue(any("CACHED" in l for l in IQ.visibility_lines(st)))
    @covers(ER, MS, "source_reconciliation", *GOV, kinds=("unit",))
    def test_conflicting_evidence_surfaced_and_unknowns_stay_unknown(self):
        bc = {"available": True, "conflicts": [{"id": "C02", "topic": "retention owner", "resolution_required": "Gev decides"}], "gaps": ["SOURCE_CONFLICT"]}
        st = state(business_context=bc); exc = IQ.exceptions(st)
        sc = [e for e in exc if e["kind"] == "SOURCE_CONFLICT"]; self.assertEqual(len(sc), 1); self.assertEqual(sc[0]["gev"]["category"], "MISSING BUSINESS TRUTH"); self.assertEqual(sc[0]["recommendation"]["deadline"], "UNKNOWN")
        own = next(e for e in exc if e["kind"] == "OWNERLESS_TASK"); self.assertEqual(own["subject"]["owner"], "UNKNOWN"); self.assertIn("OWNER NEEDED", own["recommendation"]["owner"]); self.assertEqual(own["cause"]["kind"], "CONFIRMED CAUSE")
        late = next(e for e in exc if e["kind"] == "OVERDUE_TASK" and e["subject"]["id"] == 1); self.assertEqual(late["cause"]["kind"], "UNKNOWN"); self.assertIn("do not assume", late["cause"]["text"])
        crit = next(e for e in exc if e["kind"] == "CRITICAL_NO_DEADLINE"); self.assertEqual(crit["subject"]["due"], "UNKNOWN")
        for e in exc: self.assertIn(e["cause"]["kind"], IQ.CAUSE_KINDS); self.assertIn(e["severity"], IQ.SEVERITY); self.assertIn(e["impact"]["level"], ("HIGH", "MEDIUM", "LOW"))

class Q02_TaskIntelligence(unittest.TestCase):
    @covers(MS, DB, "deadline_management", "task_management", *GOV, kinds=("unit", "completion"))
    def test_overdue_due_today_blocked_ownerless_and_provenance(self):
        st = state(); tv = IQ.task_view(st)
        self.assertTrue(all(e["id"].startswith("EXC-") for e in tv["overdue"]))
        ids_over = {e["WHAT_HAPPENED"].split()[1] for e in tv["overdue"]}; self.assertEqual(ids_over, {"1", "3"})
        self.assertEqual([t["id"] for t in tv["due_today"]], [2]); self.assertEqual({e["WHAT_HAPPENED"].split()[1] for e in tv["blocked"]}, {"3", "6"}); self.assertEqual([t["id"] for t in tv["no_deadline"]], [7])
        self.assertEqual(len(tv["ownerless"]), 1); self.assertEqual(sorted(t["id"] for t in tv["gev_owned"]), [2, 9]); self.assertEqual([t["id"] for t in tv["waiting_for_gev"]], [5]); self.assertEqual(sorted(t["id"] for t in tv["team_commitments"]), [1, 3, 5, 6, 7])   # ball with someone else (an ALL-CAPS owner = decision holder, register convention); ownerless is not a commitment
        self.assertEqual(tv["provenance"]["integration_id"], "INT-TASKS"); self.assertEqual(tv["provenance"]["business_source"], "S09"); self.assertTrue(tv["provenance"]["retrieved_at"])
        for e in tv["overdue"]: self.assertEqual(e["provenance"]["integration_id"], "INT-TASKS"); self.assertTrue(e["provenance"]["record_id"])
        self.assertEqual(tv["counts"], {"open": 8, "overdue": 2, "due_today": 1, "blocked": 2, "ownerless": 1})
    @covers(DQ, MS, *GOV, kinds=("unit", "authority"))
    def test_gev_owned_is_not_the_same_as_gev_required(self):
        st = state(); exc = IQ.exceptions(st); q = IQ.gev_queue(st, exc); refs = {x["ref"]: x["category"] for x in q}
        self.assertIn("task:4", refs); self.assertEqual(refs["task:4"], "OWNER NEEDED"); self.assertIn("task:5", refs); self.assertEqual(refs["task:5"], "DECISION"); self.assertIn("task:6", refs); self.assertEqual(refs["task:6"], "MISSING BUSINESS TRUTH")
        self.assertNotIn("task:1", refs, "an overdue task owned by a team member (5 days) is team work, not Gev's queue")
        self.assertNotIn("task:9", refs, "a Gev-owned task that is not overdue/decision is not in the queue")
        rows = tasks(); rows[0]["due"] = "2026-09-01"; st2 = state(rows=rows); refs2 = {x["ref"]: x["category"] for x in IQ.gev_queue(st2)}
        self.assertEqual(refs2.get("task:1"), "ESCALATION", "≥7 days overdue with the ball at a team member → escalation is Gev's call")
        for x in q: self.assertIn(x["category"], IQ.GEV_CATEGORIES); self.assertTrue(x["why_gev"] and x["required"] and x["consequence"])
    @covers(CR, DB, *GOV, kinds=("unit", "completion"))
    def test_completed_since_last_check_and_field_changes(self):
        st0 = state(); exc0 = IQ.exceptions(st0); sig0 = IQ.signature(st0, exc0)
        rows = tasks(); rows[0]["status"] = "Արված"; rows[1]["owner"] = "Ռիչ"; rows[3]["due"] = "2026-09-25"; rows[5]["task"] = "Retention tracking mechanism (renamed)"; rows[5]["comment"] = "noise"; rows[8]["status"] = "Սպասում"
        rows.append({"id": 10, "task": "Brand new ask", "status": "Չսկսված", "owner": "Հայկ", "due": "2026-09-13", "comment": ""}); rows[7]["status"] = "Ընթացքում"
        st1 = state(rows=rows); ch = IQ.changes({"signature": sig0, "at": st0["at"], "kind": "test"}, IQ.signature(st1))
        self.assertTrue(ch["available"]); refs = lambda g: {x["ref"] for x in ch[g]}
        self.assertIn("task:1", refs("RESOLVED")); self.assertIn("task:10", refs("NEW")); self.assertIn("task:2", refs("CHANGED")); self.assertIn("task:4", refs("WORSENED"))   # postponed
        self.assertIn("task:9", refs("WORSENED")); self.assertIn("task:8", refs("WORSENED"))                                                                                # blocked, reopened
        self.assertNotIn("task:6", refs("CHANGED") | refs("WORSENED") | refs("NEW"), "title/comment edits are noise")
        self.assertTrue(any(r["kind"] == "owner" for r in ch["CHANGED"])); self.assertTrue(any(r["kind"] == "reopened" for r in ch["WORSENED"]))

class Q03_ChangeDetectionDurable(unittest.TestCase):
    @covers(CR, DB, "audit_logging", *GOV, kinds=("unit", "completion", "failure"))
    def test_no_checkpoint_is_honest_and_production_checkpoints_persist(self):
        st = state(); v = IQ.change_view(st, record=False); self.assertFalse(v["changes"]["available"]); self.assertIn("no previous", v["changes"]["reason"]); self.assertEqual(set(v["groups"]), {"NEW", "CHANGED", "RESOLVED", "WORSENED", "NEEDS_GEV"})
        st["truth_mode"] = "PRODUCTION"; st["at"] = "2026-09-12T09:00:00"; ck = IQ.record_checkpoint(st, "brief"); self.assertEqual(ck["status"], "RECORDED"); self.assertIsNotNone(engine._store().get("checkpoints", ck["op_id"]))
        self.assertEqual(IQ.record_checkpoint(st, "brief")["status"], "DUPLICATE", "identical observation at the same time is not recorded twice")
        prev = IQ.previous_checkpoint(before_at="2999-01-01T00:00:00"); self.assertEqual(prev["op_id"] if prev else None, ck["op_id"])
        st2 = state(rows=[dict(t, status="Արված") if t["id"] == 1 else t for t in tasks()]); st2["at"] = "2999-01-01T00:00:00"; v2 = IQ.change_view(st2, record=False)
        self.assertTrue(v2["changes"]["available"]); self.assertIn("task:1", {x["ref"] for x in v2["groups"]["RESOLVED"]})
    @covers(OL, CR, "commitment_memory", *GOV, kinds=("unit", "completion", "failure_injection"))
    def test_open_loops_persist_survive_restart_and_close_on_evidence_only(self):
        st = state(); loops = IQ.open_loops(st); ids = {l["id"]: l for l in loops["open"]}
        over = next(l for l in ids.values() if l["kind"] == "TASK_OVERDUE" and l["ref"] == "task:1"); self.assertEqual(over["state"], "OPEN"); self.assertIsNotNone(engine._store().get("loops", over["id"]))
        mail = [l for l in ids.values() if l["kind"].startswith("MAIL_")]; self.assertTrue(mail); self.assertTrue(any(l.get("linked_task") == 1 for l in mail), "mail about the retention document links to task 1 by evidence")
        # restart: export → fresh store → import → loop still OPEN with its original opened_at
        root2 = TMP / "restart"; (root2 / ".claude" / "state").mkdir(parents=True); ssn.export(root2, log=lambda *a: None)
        saved = engine.STATE_DIR; engine.STATE_DIR = root2 / ".claude" / "state"; store.reset()
        try:
            ssn.import_(root2, log=lambda *a: None); again = engine._store().get("loops", over["id"]); self.assertEqual(again["state"], "OPEN"); self.assertEqual(again["opened_at"], over["opened_at"])
            # evidence of resolution: task 1 closed → TASK_OVERDUE loop and the linked mail loop close; task 3 still overdue → stays open
            rows = [dict(t, status="Արված") if t["id"] == 1 else t for t in tasks()]; st2 = state(rows=rows); l2 = IQ.open_loops(st2)
            closed = {l["ref"]: l for l in l2["closed_now"]}; self.assertIn("task:1", closed); self.assertIn("closed", closed["task:1"]["close_evidence"])
            self.assertTrue(any(l["kind"].startswith("MAIL_") and l.get("linked_task") == 1 for l in l2["closed_now"]))
            self.assertTrue(any(l["ref"] == "task:3" and l["state"] == "OPEN" for l in l2["open"]))
            # a mail loop whose mail merely left the window is NOT closed
            fx = copy.deepcopy(LIVE); fx["INT-OL-MAIL"]["records"] = [r for r in fx["INT-OL-MAIL"]["records"] if r["source_record_id"] != "e2"]
            l3 = state(fx, rows=rows); l3 = IQ.open_loops(l3); self.assertTrue(any("not proof" in (u.get("note") or "") for u in l3["unobserved"]))
        finally: engine.STATE_DIR = saved; store.reset()

class Q04_IntelligenceDiscipline(unittest.TestCase):
    @covers(ER, MS, "root_cause_analysis", *GOV, kinds=("unit",))
    def test_cause_kinds_with_evidence(self):
        st = state(); exc = {e["subject"]["ref"] + ":" + e["kind"]: e for e in IQ.exceptions(st)}
        self.assertEqual(exc["task:3:BLOCKED_TASK"]["cause"]["kind"], "SUPPORTED HYPOTHESIS"); self.assertTrue(exc["task:3:BLOCKED_TASK"]["cause"]["evidence"])
        self.assertEqual(exc["task:4:OWNERLESS_TASK"]["cause"]["kind"], "CONFIRMED CAUSE"); self.assertEqual(exc["task:1:OVERDUE_TASK"]["cause"]["kind"], "UNKNOWN")
        for e in exc.values():
            a = IQ.management_answer(e); self.assertTrue(a["WHAT_CAUSED_IT"].startswith(e["cause"]["kind"])); self.assertNotIn("poor management", a["WHAT_CAUSED_IT"].lower())
    @covers(ER, "executive_prioritization", *GOV, kinds=("unit",))
    def test_impact_and_priority_ranking(self):
        rows = tasks(); rows[0]["due"] = "2026-09-01"                                        # 11 days overdue → HIGH
        st = state(rows=rows); exc = IQ.exceptions(st)
        self.assertEqual(exc[0]["severity"], "HIGH"); sev = [IQ.SEVERITY.index(e["severity"]) for e in exc]; self.assertEqual(sev, sorted(sev))
        high = [e for e in exc if e["severity"] == "HIGH"]; self.assertTrue(any(e["subject"].get("id") == 1 and e["impact"]["level"] == "HIGH" for e in high))
        crit = next(e for e in exc if e["kind"] == "CRITICAL_NO_DEADLINE"); self.assertEqual(crit["impact"]["level"], "MEDIUM")
        ranked = IQ.rank([{"id": "b", "severity": "LOW", "urgency": "LATER", "impact": {"level": "LOW"}, "deadline": None}, {"id": "a", "severity": "HIGH", "urgency": "TODAY", "impact": {"level": "LOW"}, "deadline": None}, {"id": "c", "severity": "HIGH", "urgency": "NOW", "impact": {"level": "HIGH"}, "deadline": None}])
        self.assertEqual([r["id"] for r in ranked], ["c", "a", "b"])
    @covers(MS, "decision_support", "delegation_design", *GOV, kinds=("unit",))
    def test_recommendation_structure_and_no_invented_owner_or_date(self):
        st = state()
        for e in IQ.exceptions(st):
            r = e["recommendation"]; self.assertTrue(r["action"] and r["owner"] and r["deadline"] and r["verify"]); line = IQ.action_line(e); self.assertEqual(line.count(" → "), 3)
        own = next(e for e in IQ.exceptions(st) if e["kind"] == "OWNERLESS_TASK"); self.assertIn("OWNER NEEDED", own["recommendation"]["owner"])

class Q05_MailCalendar(unittest.TestCase):
    @covers(DB, OL, "meeting_preparation", *GOV, kinds=("unit", "completion"))
    def test_calendar_kinds_conflicts_and_preparation(self):
        st = state(); cv = IQ.calendar_view(st); self.assertTrue(cv["available"]); self.assertEqual(len(cv["today"]), 2); self.assertEqual(len(cv["conflicts"]), 1)
        self.assertIn("Discount approval review", cv["by_kind"]["DECISION"]); self.assertIn("Retention flow status", cv["by_kind"]["FOLLOW_UP"])
        linked = cv["linked_tasks"]; self.assertIn("Retention flow status", linked); self.assertEqual(linked["Retention flow status"], [1])
        self.assertTrue(any(n["title"] == "Budget sync" and "purpose/agenda not in the invitation" in n["missing"] for n in cv["needs_preparation"]))
        conf = [e for e in IQ.exceptions(st) if e["kind"] == "SCHEDULE_CONFLICT"]; self.assertEqual(len(conf), 1); self.assertEqual(conf[0]["gev"]["category"], "PRIORITY CONFLICT")
    @covers(OL, MS, "information_classification", *GOV, kinds=("unit", "failure"))
    def test_mail_meaningful_items_only_and_evidence_linkage(self):
        st = state(); mv = IQ.mail_view(st); self.assertTrue(mv["available"])
        self.assertEqual([x["subject"] for x in mv["decision_requests"]], ["Approval needed: corporate discount"]); self.assertEqual(len(mv["action_requests"]), 1)
        self.assertFalse(any("noreply" in str(x.get("counterpart_address")) for x in st["mail_candidates"])); self.assertFalse(any(x["class"] == "IGNORE" for x in st["mail_candidates"]))
        act = mv["action_requests"][0]; self.assertEqual(act["task_match"], "MATCHED"); self.assertEqual(act["matched_task"]["id"], 1)
        self.assertTrue(all(x["provenance"]["integration_id"] == "INT-OL-MAIL" and x["provenance"]["record_id"] for x in st["mail_candidates"]))
        exc = IQ.exceptions(st); md = [e for e in exc if e["kind"] == "MAIL_DECISION"]; self.assertEqual(len(md), 1); self.assertTrue(md[0]["gev"]["required"])
        ma = [e for e in exc if e["kind"] == "MAIL_ACTION"]; self.assertEqual(len(ma), 1); self.assertEqual(ma[0]["dependency"], "task 1")
        self.assertEqual(len(engine._store().list("commitments")), 0, "mail never becomes a permanent commitment")

class Q06_SalesOps(unittest.TestCase):
    @covers("sales_kpi_monitoring", "pipeline_management", MS, *GOV, kinds=("unit", "failure"))
    def test_sales_framework_on_fixture_and_honest_production_refusal(self):
        st = state(); s = IQ.sales_intelligence(st)
        self.assertEqual(s["available"], []); self.assertTrue(s["verdict"].startswith("UNAVAILABLE")); self.assertTrue(all(v["value"] == "UNKNOWN" for v in s["dimensions"].values()))
        self.assertTrue(any("INT-B24" in m for m in s["dimensions"]["pipeline_health"]["missing"])); self.assertTrue(any("INT-MB" in m for m in s["dimensions"]["target_vs_actual"]["missing"]))
        st2 = copy.deepcopy(st); st2["visibility"]["INT-B24"] = {**st2["visibility"]["INT-B24"], "usable": True, "state": "FIXTURE", "production_truth": False}
        deals = [{"record_id": "INT-B24:d1", "source_record_id": "1", "title": "HouseNet corp A", "stage_id": "NEW", "owner_id": "3", "opportunity": 120000, "currency": "AMD", "date_create": "2026-08-01", "date_modify": "2026-08-10", "closed": False, "source_updated_at": "2026-08-10"},
                 {"record_id": "INT-B24:d2", "source_record_id": "2", "title": "Corp B", "stage_id": "PREPARATION", "owner_id": "3", "opportunity": None, "currency": "AMD", "date_create": "2026-09-01", "date_modify": "2026-09-11", "closed": False, "source_updated_at": "2026-09-11"},
                 {"record_id": "INT-B24:d3", "source_record_id": "3", "title": "Corp C", "stage_id": "LOSE", "owner_id": "4", "opportunity": 5000, "currency": "AMD", "date_create": "2026-08-01", "date_modify": "2026-09-05", "closed": True, "source_updated_at": "2026-09-05"}]
        env = {"INT-B24": {"status": "OK", "kind": "deal", "records": deals, "retrieved_at": f"{T}T09:00:00", "freshness": "LIVE", "mode": "FIXTURE"}, "INT-B24-activities": {"status": "OK", "records": [{"deadline": "2026-09-01", "completed": False}, {"deadline": "2026-09-30", "completed": False}]}}
        s2 = IQ.sales_intelligence(st2, env); d = s2["dimensions"]
        self.assertEqual(d["pipeline_health"]["value"]["open_deals"], 2); self.assertEqual(d["stagnant_opportunities"]["value"]["stagnant_14d"], 1); self.assertEqual(d["lost_opportunities"]["value"]["lost"], 1); self.assertEqual(d["follow_up_failures"]["value"]["overdue_activities"], 1)
        self.assertEqual(d["pipeline_health"]["provenance"]["mode"], "FIXTURE"); self.assertEqual(d["target_vs_actual"]["status"], "UNAVAILABLE / NOT CONNECTED")
    @covers("backlog_management", "operations_kpi_monitoring", "bottleneck_detection", MS, *GOV, kinds=("unit",))
    def test_operations_framework_partial_and_honest(self):
        rows = tasks() + [{"id": 11, "task": "x", "status": "Ընթացքում", "owner": "Արման", "due": "2026-09-01", "comment": ""}, {"id": 12, "task": "y", "status": "Ընթացքում", "owner": "Արման", "due": "2026-09-02", "comment": ""}]
        st = state(rows=rows); o = IQ.operations_intelligence(st); d = o["dimensions"]
        self.assertEqual(d["overdue_work"]["value"]["overdue"], 4); self.assertEqual(d["people_bottlenecks"]["value"]["bottlenecks"], {"Արման": 3}); self.assertEqual(d["sla_risks"]["status"], "UNAVAILABLE / NOT CONNECTED")
        self.assertIn("UNAVAILABLE", d["operational_backlog"]["value"]["field_backlog"]); self.assertTrue(any("INT-B24" in m for m in d["failed_rework"]["missing"]))
        self.assertIn("sla_risks", o["unavailable"]); self.assertIn("overdue_work", o["available"]); self.assertEqual(d["cross_functional_blockers"]["value"]["blocked_waiting"][0]["id"], 3)

class Q07_Governance(unittest.TestCase):
    def setUp(self):
        import health; health.record("INT-TASKS", True, op="tasks.list", mode="REAL")          # the register is readable in this environment (capability CONNECTED); writes can only hit the temp copy (env guard)
    def _run(self, intent, **extra):
        with Fixture(LIVE):
            plan = engine.resolve(REG, intent); r = engine.run_plan(REG, plan, {"today": T, "tasks": tasks(), "no_checkpoint": True, **extra}); return plan, r
    @covers(MS, ER, CR, DQ, "action_runtime", *GOV, kinds=("authority", "completion", "adversarial", "unit"))
    def test_intelligence_never_mutates_and_execution_routes_to_the_action_runtime(self):
        before_actions = len(engine._store().list("actions")); before_commit = len(engine._store().list("commitments"))
        for intent, sid in (("ինչ action ես առաջարկում", MS), ("what's wrong right now?", ER), ("ինչ փոխվեց երեկվանից", CR), ("ինձնից ինչ ա սպասում", DQ)):
            plan, r = self._run(intent); self.assertIn(sid, plan["chain"], intent); self.assertNotIn("action_runtime", plan["chain"], intent)
            st = next(s for s in r["steps"] if s["skill"] == sid); self.assertIn(st["status"], ("EXECUTED", "ASSISTED"), (intent, st)); self.assertTrue(st["validated"]); self.assertTrue(st["verification"]["ok"]); self.assertFalse(st["result"].get("mutation_performed"))
        self.assertEqual(len(engine._store().list("actions")), before_actions); self.assertEqual(len(engine._store().list("commitments")), before_commit)
        plan, r = self._run("Create a task for Arman to send the weekly report by Friday.")
        self.assertIn("action_runtime", plan["chain"]); st = next(s for s in r["steps"] if s["skill"] == "action_runtime"); self.assertEqual(st["status"], "ASSISTED"); self.assertEqual(st["result"]["action_state"], "APPROVAL_REQUIRED"); self.assertFalse(st["result"]["mutation_performed"]); self.assertIn("READY FOR YOUR APPROVAL", st["result"]["card"])
        self.assertEqual(len(engine._store().list("actions")), before_actions + 1)
        law = json.loads((ROOT / ".claude" / "policy" / "approval_rule.json").read_text(encoding="utf-8")); self.assertEqual(law["autonomous_external_write_authority"], "NONE"); self.assertEqual(law["version"], "1.0")
    @covers(DB, "end_of_day_control", "weekly_executive_review", OL, *GOV, kinds=("completion", "unit"))
    def test_brief_eod_weekly_and_open_loops_carry_the_management_block(self):
        plan, r = self._run("Good morning — daily brief"); st = next(s for s in r["steps"] if s["skill"] == DB); self.assertIn(st["status"], ("EXECUTED", "ASSISTED"))   # ASSISTED only while a transient certification downgrade is on disk
        m = st["result"]["management"]; self.assertEqual(m["status"], "EXECUTED")
        for k in ("TOP_LINE", "CHANGES", "SALES", "OPERATIONS", "TASKS", "CALENDAR", "MAIL", "RISKS", "ACTIONS", "GEV_ACTION"): self.assertIn(k, m)
        self.assertTrue(m["TOP_LINE"]["needs_gev"] >= 1); self.assertIn("INT-B24", m["TOP_LINE"]["visibility_gaps"]); self.assertTrue(st["result"]["management_text"].startswith("DEPUTY DAILY BRIEF")); self.assertNotIn("checkpoint", m)
        plan, r = self._run("end of day"); e = next(s for s in r["steps"] if s["skill"] == "end_of_day_control")["result"]["management"]; self.assertEqual(e["status"], "EXECUTED")
        self.assertTrue(any(t["id"] == 8 for t in e["completed"])); self.assertTrue(any(t["id"] == 2 for t in e["slipped"])); self.assertEqual(e["unverified"], []); self.assertIn("no external mutation", e["note"])
        plan, r = self._run("weekly review"); w = next(s for s in r["steps"] if s["skill"] == "weekly_executive_review")["result"]["management"]; self.assertIn(w["status"], ("EXECUTED", "ASSISTED")); self.assertTrue(w["missed_commitments"]); self.assertTrue(w["sales_movement"].startswith("UNAVAILABLE"))
        plan, r = self._run("what's open — anything pending?"); o = next(s for s in r["steps"] if s["skill"] == OL)["result"]["management"]; self.assertEqual(o["status"], "EXECUTED"); self.assertTrue(o["loops"]["count_open"] >= 3)

class Q07b_FailClosed(unittest.TestCase):
    @covers(MS, ER, CR, DQ, "source_verification", *GOV, kinds=("failure", "unit"))
    def test_intelligence_skills_fail_closed_on_an_invalid_register(self):
        for sid in (MS, ER, CR, DQ):
            r = engine.run_skill(REG, sid, {"path": str(TMP / "does-not-exist.xlsx"), "today": T, "no_live": True})
            self.assertEqual(r["status"], "BLOCKED", sid); self.assertEqual(r["blocked"][0]["code"], "INVALID_SOURCE", sid)
        st = IQ.current_state({"today": T, "tasks": [], "no_live": True}); v = IQ.exception_view(st)
        self.assertEqual(v["count"], 0); self.assertTrue(v["visibility_incomplete"]); self.assertIn("INT-OL-CAL", st["unavailable"]); self.assertIn("INT-OL-MAIL", st["unavailable"])
        q = IQ.gev_queue(st); self.assertTrue(all(x["category"] == "APPROVAL" for x in q), "with an empty register only a pending Action-Runtime approval may remain in Gev's queue"); ch = IQ.changes(None, IQ.signature(st)); self.assertFalse(ch["available"])

class Q08_ProductionGuards(unittest.TestCase):
    @covers(MS, "task_management", *GOV, kinds=("unit",))
    def test_real_register_read_is_provenanced_and_untouched(self):
        st = IQ.current_state({"today": T, "no_live": True}); v = st["visibility"]["INT-TASKS"]; self.assertIn(v["state"], ("LIVE", "CACHED")); self.assertTrue(v["production_truth"] or v["state"] == "CACHED"); self.assertTrue(st["task_provenance"]["retrieved_at"])
        self.assertEqual(st["visibility"]["INT-OL-CAL"]["state"], "UNAVAILABLE"); self.assertIn("INT-OL-CAL", st["unavailable"])
        if REAL_SHA: self.assertEqual(hashlib.sha256(REAL.read_bytes()).hexdigest(), REAL_SHA)

if __name__ == "__main__":
    unittest.main(verbosity=2)
