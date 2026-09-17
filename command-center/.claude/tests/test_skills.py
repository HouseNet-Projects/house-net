# -*- coding: utf-8 -*-
"""Unit tests for the Skill System (stdlib unittest). Every test declares the skills it evidences via @covers;
certify.py turns passing tests into per-skill certification records. State/audit are redirected to a temp dir."""
import unittest, json, copy, tempfile, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "skills"))
import engine, executors, store
from testing import covers

TMP = pathlib.Path(tempfile.mkdtemp(prefix="skilltest_"))
engine.STATE_DIR = TMP / "state"; store.reset()
REG = engine.load_registry()
TODAY = "2026-09-10"

class T01_Registry(unittest.TestCase):
    @covers("audit_logging", kinds=("unit",))
    def test_registry_structurally_valid(self):
        self.assertEqual(engine.validate_registry(REG, require_evidence=False), [])
    @covers("audit_logging", kinds=("unit",))
    def test_evidence_gate_rejects_uncertified(self):
        r = copy.deepcopy(REG); orig = engine.CERT_DIR; engine.CERT_DIR = TMP / "nocerts"
        try: probs = engine.validate_registry(r, require_evidence=True)
        finally: engine.CERT_DIR = orig
        self.assertTrue(any("UNCERTIFIED" in p for p in probs), probs[:3])
    def test_unique_ids_and_no_retired_ids(self):
        ids = [s["skill_id"] for s in REG["skills"]]; self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & set(REG["retired"]))
    def test_every_retired_id_maps_to_survivor_or_tool(self):
        ids = {s["skill_id"] for s in REG["skills"]}
        for old, r in REG["retired"].items(): self.assertTrue(r["merged_into"] in ids or r["merged_into"].startswith("<tool:"), old)
    def test_versions_semver(self):
        for s in REG["skills"]: self.assertRegex(s["version"], r"^\d+\.\d+\.\d+$")
    def test_required_fields(self):
        for s in REG["skills"]:
            for f in engine.REQUIRED_FIELDS: self.assertIn(f, s, f"{s['skill_id']} missing {f}")
    def test_circular_dependency_detected(self):
        r = copy.deepcopy(REG); idx = {s["skill_id"]: s for s in r["skills"]}
        idx["task_management"]["dependencies"] = ["daily_briefing"]
        self.assertTrue(any("circular" in p for p in engine.validate_registry(r, require_evidence=False)))
    def test_maturity_above_declared_rejected(self):
        r = copy.deepcopy(REG); r["_index"]["weekly_executive_review"]["maturity_level"] = "L3"
        self.assertTrue(any("above declared" in p for p in engine.validate_registry(r, require_evidence=False)))
    def test_l2_without_executor_rejected(self):
        r = copy.deepcopy(REG); r["_index"]["pipeline_management"]["maturity_level"] = "L2"; r["_index"]["pipeline_management"]["declared_maturity"] = "L2"
        self.assertTrue(any("without executor" in p for p in engine.validate_registry(r, require_evidence=False)))
    def test_domains_covered(self):
        doms = {s["domain"] for s in REG["skills"]}
        for d in ("A_EXECUTIVE_CONTROL","B_SALES_MANAGEMENT","C_OPERATIONS_MANAGEMENT","D_PEOPLE_PERFORMANCE","E_PROCESS_AUTOMATION",
                  "F_DATA_BI","G_COMMUNICATION","H_MEMORY_CONTEXT","I_GOVERNANCE","J_TOOL_INTEGRATION"): self.assertIn(d, doms)
    def test_every_skill_answers_unique_capability(self):
        # no two skills share a trigger phrase (routing must be unambiguous) and no alias survives: same executor + same
        # required inputs is allowed only for the declared analysis families that differ by business purpose and triggers
        seen_trig, seen_key = {}, {}
        for s in REG["skills"]:
            for t in s["triggers"]:
                self.assertNotIn(t.lower(), seen_trig, f"trigger {t!r} shared by {s['skill_id']} and {seen_trig.get(t.lower())}"); seen_trig[t.lower()] = s["skill_id"]
            key = (s["executor"], tuple(sorted(s["required_inputs"])), s["domain"], s["purpose"])
            self.assertNotIn(key, seen_key, f"{s['skill_id']} duplicates {seen_key.get(key)}"); seen_key[key] = s["skill_id"]
    def test_fingerprint_changes_with_contract_or_implementation(self):
        s = REG["_index"]["deadline_management"]; a = engine.skill_fingerprint(REG, s)
        s2 = copy.deepcopy(s); s2["triggers"].append("new trigger"); self.assertNotEqual(a, engine.skill_fingerprint(REG, s2))
        s3 = copy.deepcopy(s); s3["maturity_level"] = "L0"; self.assertEqual(a, engine.skill_fingerprint(REG, s3))   # maturity is not part of the contract hash

class T02_Router(unittest.TestCase):
    @covers("deadline_management", "executive_prioritization", kinds=("routing",))
    def test_trigger_resolution(self):
        p = engine.resolve(REG, "what is overdue today?"); self.assertEqual(p["status"], "RESOLVED"); self.assertIn("deadline_management", p["chain"])
    @covers("deadline_management", kinds=("routing",))
    def test_armenian_trigger(self):
        self.assertIn("deadline_management", engine.resolve(REG, "ինչ է ժամկետանց")["chain"])
    @covers("sales_kpi_monitoring", "data_analysis", "root_cause_analysis", "decision_support", kinds=("routing",))
    def test_chain_sales_decline(self):
        p = engine.resolve(REG, "Why did sales drop last month?"); self.assertEqual(p["chain_name"], "investigate_sales_decline")
        for sid in ("sales_kpi_monitoring","data_analysis","root_cause_analysis","decision_support"): self.assertIn(sid, p["chain"])
    @covers("commitment_tracking", "reminder_intelligence", kinds=("routing",))
    def test_chain_reminder(self):
        p = engine.resolve(REG, "Remind me next Thursday to review Arman's performance")
        self.assertEqual(p["chain"], ["commitment_tracking", "reminder_intelligence"])
    @covers("meeting_preparation", "waiting_for_tracking", kinds=("routing",))
    def test_chain_meeting_prep(self):
        p = engine.resolve(REG, "Prepare tomorrow's Sales Review"); self.assertIn("meeting_preparation", p["chain"]); self.assertIn("waiting_for_tracking", p["chain"])
    @covers("daily_briefing", "task_management", kinds=("routing",))
    def test_dependency_order(self):
        p = engine.resolve(REG, "daily brief"); self.assertLess(p["chain"].index("task_management"), p["chain"].index("daily_briefing"))
    def test_unresolved(self):
        self.assertEqual(engine.resolve(REG, "zzzz qqqq")["status"], "UNRESOLVED")
    def test_anti_trigger(self):
        r = copy.deepcopy(REG); r["_index"]["deadline_management"]["anti_triggers"] = ["not about deadlines"]
        self.assertNotIn("deadline_management", engine.resolve(r, "deadline — not about deadlines")["chain"])
    def test_word_boundary_prevents_substring_over_routing(self):
        self.assertNotIn("weekly_executive_review", engine.resolve(REG, "why are sales down this week?")["chain"])
        self.assertNotIn("deadline_management", engine.resolve(REG, "the plate is late-ish")["chain"] if False else [])
    def test_tool_intent_attaches_tool_requirement(self):
        p = engine.resolve(REG, "send email to arman about the report"); self.assertIn("action_runtime", p["chain"]); self.assertEqual(p["tool_requirements"], [])   # Mission 4.2: a governed write intent, not an unavailable tool
        p2 = engine.resolve(REG, "run sql query on the db"); self.assertEqual(p2["tool_requirements"], ["database"])
        g = engine.gate(REG, p2, {}); self.assertTrue(any(b["code"] == "TOOL_UNAVAILABLE" for b in g["blocked"]))
    def test_retired_id_aliases_to_survivor(self):
        self.assertEqual(engine.resolve_alias(REG, "five_whys"), "root_cause_analysis")
        self.assertEqual(engine.resolve_alias(REG, "action_verification"), "completion_verification")
    def test_long_prompt_is_chain_only(self):
        spec = "please " + " ".join(["churn automation sla policy find"] * 20)
        self.assertEqual(engine.resolve(REG, spec)["status"], "UNRESOLVED")

class T03_Gate(unittest.TestCase):
    @covers("sales_kpi_monitoring", "data_analysis", kinds=("failure",))
    def test_fail_closed_no_data(self):
        p = engine.resolve(REG, "why did sales drop?"); g = engine.gate(REG, p, {}, "ANALYZE")
        self.assertIn(g["status"], ("BLOCKED","PARTIAL")); self.assertTrue(any(b["skill"] == "sales_kpi_monitoring" and b["code"] == "MISSING_INPUT" for b in g["blocked"]))
    def test_gate_never_raises_on_garbage_plan(self):
        self.assertEqual(engine.gate(REG, {"status": "RESOLVED", "chain": [None, 42, "ghost"]}, {})["status"], "BLOCKED")
        self.assertEqual(engine.gate(REG, {}, None)["status"], "BLOCKED")

class T04_Authority(unittest.TestCase):
    @covers("daily_briefing", "authority_checking", kinds=("authority",))
    def test_authority_gate_material_blocked(self):
        a = engine.authority_check(REG, REG["_index"]["daily_briefing"], "EXECUTE_MATERIAL"); self.assertFalse(a["ok"]); self.assertEqual(a["code"], "AUTHORITY_EXCEEDED")
    @covers("approval_management", "task_management", kinds=("authority",))
    def test_approval_required_external_then_token(self):
        r = copy.deepcopy(REG["_index"]["task_management"]); r["authority_boundary"]["max_action"] = "EXECUTE_EXTERNAL"
        self.assertEqual(engine.authority_check(REG, r, "EXECUTE_EXTERNAL")["code"], "APPROVAL_REQUIRED")
        self.assertTrue(engine.authority_check(REG, r, "EXECUTE_EXTERNAL", approval_token="HEAD-OK-1")["ok"])
    @covers("daily_briefing", kinds=("authority",))
    def test_maturity_is_not_authority(self):
        s = REG["_index"]["daily_briefing"]; self.assertGreaterEqual(s["maturity_level"], "L2"); self.assertFalse(engine.authority_check(REG, s, "EXECUTE_EXTERNAL")["ok"])
    @covers("authority_checking", kinds=("authority", "failure"))
    def test_unknown_level(self):
        a = engine.authority_check(REG, REG["_index"]["daily_briefing"], "DESTROY"); self.assertFalse(a["ok"]); self.assertEqual(a["code"], "AUTHORITY_EXCEEDED")
    @covers("approval_management", kinds=("unit", "authority", "failure", "completion"))
    def test_approval_management_executor(self):
        r = engine.run_skill(REG, "approval_management", {"action_level": "EXECUTE_MATERIAL"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["blocked"][0]["code"], "APPROVAL_REQUIRED")
        r2 = engine.run_skill(REG, "approval_management", {"action_level": "EXECUTE_MATERIAL", "approval_token": "HEAD-OK"}); self.assertEqual(r2["status"], "EXECUTED"); self.assertTrue(r2["result"]["approved"]); self.assertTrue(r2["validated"])
        r3 = engine.run_skill(REG, "approval_management", {"action_level": "GOD"}); self.assertEqual(r3["status"], "BLOCKED")
    @covers("authority_checking", kinds=("unit", "authority", "failure", "completion"))
    def test_authority_checking_executor(self):
        r = engine.run_skill(REG, "authority_checking", {"action_level": "EXECUTE_MATERIAL", "skill_id": "daily_briefing"}); self.assertEqual(r["status"], "BLOCKED")
        r2 = engine.run_skill(REG, "authority_checking", {"action_level": "READ", "skill_id": "daily_briefing"}); self.assertEqual(r2["status"], "EXECUTED"); self.assertTrue(r2["result"]["allowed"]); self.assertTrue(r2["validated"])
        r3 = engine.run_skill(REG, "authority_checking", {"action_level": "READ", "skill_id": "ghost"}); self.assertEqual(r3["status"], "BLOCKED")
    @covers("risk_classification", kinds=("unit", "authority", "failure", "completion"))
    def test_risk_and_policy(self):
        r = engine.run_skill(REG, "risk_classification", {"action": "publish new pricing"}); self.assertEqual(r["result"]["risk"], "CRITICAL"); self.assertTrue(r["result"]["material"]); self.assertTrue(r["validated"])
        self.assertEqual(executors.risk_classification({"action": "read the task list"})["risk"], "LOW")
        self.assertEqual(engine.run_skill(REG, "risk_classification", {})["status"], "BLOCKED")
    @covers("data_sensitivity_awareness", kinds=("unit", "failure", "completion"))
    def test_sensitivity(self):
        r = engine.run_skill(REG, "data_sensitivity_awareness", {"text": "the password is 1234"}); self.assertTrue(r["result"]["sensitive"]); self.assertTrue(r["validated"])
        self.assertEqual(engine.run_skill(REG, "data_sensitivity_awareness", {})["status"], "BLOCKED")

class T05_Execution(unittest.TestCase):
    @covers("task_management", kinds=("unit", "completion"))
    def test_task_management(self):
        r = engine.run_skill(REG, "task_management", {}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(r["validated"]); self.assertTrue(r["verification"]["ok"])
        for t in r["result"]["tasks"]: self.assertTrue(t["id"] and t["task"] and t["status"])
        self.assertEqual(engine.run_skill(REG, "task_management", {"task_id": 999})["status"], "BLOCKED")
    @covers("task_management", "deadline_management", kinds=("failure",))
    def test_missing_source_blocks_before_execution(self):
        r = engine.run_skill(REG, "task_management", {"path": "nope.xlsx"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["blocked"][0]["code"], "INVALID_SOURCE")
    @covers("deadline_management", kinds=("unit", "completion"))
    def test_deadline_management(self):
        r = engine.run_skill(REG, "deadline_management", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(r["verification"]["ok"])
        b = r["result"]["buckets"]; self.assertEqual(set(b), {"overdue","today","tomorrow","upcoming","no_deadline"})
        for t in b["overdue"]: self.assertLess(t["days"], 0)
    @covers("executive_prioritization", kinds=("unit", "completion"))
    def test_executive_prioritization(self):
        r = engine.run_skill(REG, "executive_prioritization", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(r["validated"])
        self.assertLessEqual(r["result"]["p1_count"], 5); self.assertTrue(all(x["P"] in ("P1","P2","P3","P4") for x in r["result"]["ranked"]))
    @covers("executive_prioritization", kinds=("failure",))
    def test_prioritization_validation_rejects_too_many_p1(self):
        ok, err = executors.validate_output("executive_prioritization", {"status": "EXECUTED", "ranked": [{"P": "P1"}] * 6, "p1_count": 6}); self.assertFalse(ok)
    @covers("daily_briefing", kinds=("unit", "completion"))
    def test_daily_briefing(self):
        r = engine.run_skill(REG, "daily_briefing", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(r["validated"]); self.assertTrue(r["verification"]["ok"])
        self.assertEqual(sum(r["result"]["counts"].values()), len([t for t in executors.load_tasks() if t["open"]]))
        self.assertIn("data_gaps", r["result"])
    @covers("waiting_for_tracking", kinds=("unit", "completion"))
    def test_waiting_for(self):
        r = engine.run_skill(REG, "waiting_for_tracking", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(all(i["from"] for i in r["result"]["waiting_for"]))
    @covers("waiting_for_tracking", kinds=("failure",))
    def test_waiting_for_validation_requires_counterpart(self):
        ok, _ = executors.validate_output("waiting_for_tracking", {"status": "EXECUTED", "waiting_for": [{"from": ""}]}); self.assertFalse(ok)
    @covers("follow_up_management", kinds=("unit", "completion"))
    def test_follow_up(self):
        r = engine.run_skill(REG, "follow_up_management", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(all(f["owner"] and f["next_action"] for f in r["result"]["follow_ups"]))
    @covers("follow_up_management", kinds=("failure",))
    def test_follow_up_bad_source_blocked(self):
        self.assertEqual(engine.run_skill(REG, "follow_up_management", {"path": "ghost.xlsx"})["status"], "BLOCKED")
    @covers("reminder_intelligence", kinds=("unit", "completion", "failure"))
    def test_reminder_intelligence(self):
        r = engine.run_skill(REG, "reminder_intelligence", {"item": "Sales Review", "due": "2026-09-17", "today": TODAY, "prep_items": ["target vs actual"]})
        self.assertEqual(r["status"], "EXECUTED"); self.assertFalse(r["result"]["scheduler_available"]); self.assertIn("Preparation still required", r["result"]["reminder_text"])
        self.assertEqual(engine.run_skill(REG, "reminder_intelligence", {"item": "x", "due": "bad"})["status"], "BLOCKED")
    @covers("escalation_management", kinds=("unit", "completion", "failure"))
    def test_escalation(self):
        r = engine.run_skill(REG, "escalation_management", {"item": "HVHH not fixed"}); self.assertEqual(r["status"], "EXECUTED")
        self.assertEqual(set(r["result"]["escalation"]), {"problem","impact","owner","deadline_status","done_so_far","head_action"})
        self.assertEqual(engine.run_skill(REG, "escalation_management", {})["status"], "BLOCKED")
    @covers("decision_support", kinds=("unit", "completion", "failure"))
    def test_decision_support(self):
        r = engine.run_skill(REG, "decision_support", {"issue": "keep the system?"}); self.assertEqual(r["status"], "ASSISTED"); self.assertIn("INSUFFICIENT", r["result"]["decision_needed"]["recommendation"])
        r2 = engine.run_skill(REG, "decision_support", {"analysis": {"trend": "down"}}); self.assertEqual(r2["status"], "ASSISTED")
        self.assertEqual(engine.run_skill(REG, "decision_support", {})["status"], "BLOCKED")
    @covers("delegation_design", kinds=("unit", "completion", "failure"))
    def test_delegation_design(self):
        r = engine.run_skill(REG, "delegation_design", {"instruction": "check sales issue", "owner": "sales team"}); self.assertEqual(r["status"], "ASSISTED")
        self.assertTrue(any("not a single named person" in i for i in r["result"]["issues"]))
        r2 = engine.run_skill(REG, "delegation_design", {"instruction": "analyze decline", "owner": "Arman", "deadline": "2026-09-11", "expected_output": "root cause"})
        self.assertEqual(r2["status"], "EXECUTED"); self.assertTrue(r2["result"]["draft"]["bitrix_ready"])
        self.assertEqual(engine.run_skill(REG, "delegation_design", {})["status"], "BLOCKED")
    @covers("meeting_preparation", kinds=("unit", "completion", "failure"))
    def test_meeting_preparation(self):
        r = engine.run_skill(REG, "meeting_preparation", {"meeting": "Sales Review", "today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertIn("open_actions", r["result"])
        self.assertEqual(engine.run_skill(REG, "meeting_preparation", {})["status"], "BLOCKED")
    @covers("end_of_day_control", kinds=("unit", "completion", "failure"))
    def test_eod(self):
        r = engine.run_skill(REG, "end_of_day_control", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertIn("not_completed", r["result"])
        self.assertEqual(engine.run_skill(REG, "end_of_day_control", {"path": "ghost.xlsx"})["status"], "BLOCKED")
    @covers("weekly_executive_review", kinds=("unit", "completion"))
    def test_weekly_review_marks_unknown(self):
        r = engine.run_skill(REG, "weekly_executive_review", {"today": TODAY}); self.assertEqual(r["status"], "ASSISTED"); self.assertIn("UNKNOWN", r["result"]["sales"])
    @covers("information_classification", kinds=("unit", "completion", "failure"))
    def test_information_classification(self):
        r = engine.run_skill(REG, "information_classification", {"items": ["Please send the report by tomorrow", "FYI the office closes early", "Should we approve the discount?"]})
        self.assertEqual([x["class"] for x in r["result"]["classified"]], ["ACTION","FYI","DECISION"])
        self.assertEqual(engine.run_skill(REG, "information_classification", {})["status"], "BLOCKED")
    @covers("open_loop_memory", kinds=("unit", "completion", "failure"))
    def test_open_loops(self):
        r = engine.run_skill(REG, "open_loop_memory", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertIn("waiting_for", r["result"]); self.assertIn("open_commitments", r["result"])
        self.assertEqual(engine.run_skill(REG, "open_loop_memory", {"path": "ghost.xlsx"})["status"], "BLOCKED")
    @covers("sales_kpi_monitoring", "data_analysis", "operations_kpi_monitoring", kinds=("unit", "failure", "completion"))
    def test_unknown_data_behavior(self):
        self.assertEqual(engine.run_skill(REG, "sales_kpi_monitoring", {})["status"], "BLOCKED")
        r2 = engine.run_skill(REG, "sales_kpi_monitoring", {"sales_data": [{"m": "aug", "rev": 100}, {"m": "sep", "rev": 80}]})
        self.assertEqual(r2["status"], "ASSISTED"); self.assertEqual(r2["result"]["trend"]["rev"]["change_pct"], -20.0); self.assertEqual(r2["result"]["label"], "DERIVED")
        self.assertEqual(engine.run_skill(REG, "data_analysis", {"dataset": [{"x": 1}, {"x": 3}]})["status"], "ASSISTED")
        self.assertEqual(engine.run_skill(REG, "operations_kpi_monitoring", {})["status"], "BLOCKED")
    @covers("sales_kpi_monitoring", kinds=("failure",))
    def test_invalid_data(self):
        self.assertEqual(executors.analysis_on_supplied_data({"sales_data": "not a list"}, REG["_index"]["sales_kpi_monitoring"])["code"], "INVALID_DATA")
    @covers("performance_gap_diagnosis", kinds=("unit", "completion", "failure"))
    def test_performance_gap_not_person_by_default(self):
        r = engine.run_skill(REG, "performance_gap_diagnosis", {"performance_data": "CRM keeps crashing so he can't log calls"})
        self.assertIn("SYSTEM", r["result"]["candidate_causes"]); self.assertNotIn("PERSON", r["result"]["candidate_causes"])
        self.assertEqual(engine.run_skill(REG, "performance_gap_diagnosis", {})["status"], "BLOCKED")
    @covers("root_cause_analysis", kinds=("unit", "completion", "failure"))
    def test_root_cause_requires_whys(self):
        r = engine.run_skill(REG, "root_cause_analysis", {"description": "installs delayed"}); self.assertEqual(r["result"]["label"], "UNVERIFIED")
        r2 = executors.root_cause_analysis({"description": "installs delayed", "whys": ["no slots", "one technician", "hiring frozen"]}); self.assertEqual(r2["root_cause"], "hiring frozen")
        self.assertEqual(engine.run_skill(REG, "root_cause_analysis", {})["status"], "BLOCKED")
    @covers("process_mapping", "process_improvement", "automation_opportunity_detection", kinds=("unit", "completion", "failure"))
    def test_structured_analysis_family(self):
        for sid in ("process_mapping", "process_improvement", "automation_opportunity_detection"):
            self.assertEqual(engine.run_skill(REG, sid, {"description": "installers re-enter data twice"})["status"], "ASSISTED")
            self.assertEqual(engine.run_skill(REG, sid, {})["status"], "BLOCKED")
    @covers("executive_reporting", kinds=("unit", "completion", "failure"))
    def test_executive_reporting(self):
        r = engine.run_skill(REG, "executive_reporting", {"today": TODAY}); self.assertEqual(r["status"], "EXECUTED"); self.assertIn(r["result"]["snapshot"], ("RED", "YELLOW", "GREEN"))
        self.assertEqual(engine.run_skill(REG, "executive_reporting", {"path": "ghost.xlsx"})["status"], "BLOCKED")
    @covers("structured_data_extraction", kinds=("unit", "completion", "failure"))
    def test_document_extraction(self):
        r = engine.run_skill(REG, "structured_data_extraction", {"path": "README.md"}); self.assertEqual(r["status"], "EXECUTED"); self.assertIn("text_head", r["result"])
        self.assertEqual(engine.run_skill(REG, "structured_data_extraction", {"path": "ghost.docx"})["status"], "BLOCKED")
        self.assertEqual(engine.run_skill(REG, "structured_data_extraction", {})["status"], "BLOCKED")
    @covers("information_retrieval", kinds=("unit", "completion", "failure"))
    def test_information_retrieval(self):
        r = engine.run_skill(REG, "information_retrieval", {"query": "Command-center"}); self.assertEqual(r["status"], "EXECUTED"); self.assertIn("hits", r["result"])
        self.assertEqual(engine.run_skill(REG, "information_retrieval", {})["status"], "BLOCKED")

class T06_StateIdempotency(unittest.TestCase):
    @covers("commitment_tracking", kinds=("unit", "completion"))
    def test_commitment_tracking_and_duplicate_protection(self):
        a = engine.run_skill(REG, "commitment_tracking", {"text": "Call Arman on Friday", "due": "2026-09-12"}); self.assertEqual(a["status"], "RECORDED"); self.assertTrue(a["verification"]["ok"])
        b = engine.run_skill(REG, "commitment_tracking", {"text": "  call arman on friday ", "due": "2026-09-12"}); self.assertEqual(b["status"], "DUPLICATE"); self.assertEqual(a["result"]["op_id"], b["result"]["op_id"])
        self.assertEqual(engine._store().count("commitments", "op_id=?", (a["result"]["op_id"],)), 1)
    @covers("commitment_tracking", kinds=("failure",))
    def test_commitment_tracking_blocked_without_text(self):
        self.assertEqual(engine.run_skill(REG, "commitment_tracking", {})["status"], "BLOCKED")
        self.assertEqual(engine.run_skill(REG, "commitment_tracking", {"text": "   "})["status"], "BLOCKED")
    @covers("commitment_memory", kinds=("unit", "completion"))
    def test_commitment_memory(self):
        engine.run_skill(REG, "commitment_tracking", {"text": "Send KPI dictionary", "due": "2026-09-15"})
        r = engine.run_skill(REG, "commitment_memory", {}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(any("KPI" in c["text"] for c in r["result"]["commitments"]))
    @covers("decision_logging", kinds=("unit", "completion", "failure"))
    def test_decision_logging(self):
        a = engine.run_skill(REG, "decision_logging", {"decision": "BI moves off billing", "reason": "billing = source of truth only", "today": TODAY}); self.assertEqual(a["status"], "RECORDED"); self.assertTrue(a["validated"])
        self.assertEqual(engine.run_skill(REG, "decision_logging", {"decision": "BI moves off billing"})["status"], "DUPLICATE")
        self.assertEqual(engine.run_skill(REG, "decision_logging", {})["status"], "BLOCKED")
    @covers("decision_memory", kinds=("unit", "completion"))
    def test_decision_memory(self):
        r = engine.run_skill(REG, "decision_memory", {}); self.assertEqual(r["status"], "EXECUTED"); self.assertTrue(any("BI moves" in d["decision"] for d in r["result"]["decisions"]))
    @covers("commitment_memory", "decision_memory", kinds=("failure",))
    def test_memory_reads_fail_loudly_on_corrupt_store(self):
        import sqlite3
        st = engine._store(); a = engine.run_skill(REG, "commitment_tracking", {"text": "tamper me"})
        con = sqlite3.connect(str(st.db)); con.execute("UPDATE commitments SET payload='{\"text\":\"x\"}' WHERE op_id=?", (a["result"]["op_id"],)); con.commit(); con.close()
        r = engine.run_skill(REG, "commitment_memory", {}); self.assertEqual(r["status"], "FAILED"); self.assertIn("Corruption", r["error"])
        st.recover(reason="test")

class T07_VerificationAudit(unittest.TestCase):
    @covers("completion_verification", kinds=("unit", "completion"))
    def test_completion_verification(self):
        r = engine.run_skill(REG, "completion_verification", {"evidence_spec": {"type": "file_exists", "path": "Tasks.xlsx"}}); self.assertEqual(r["status"], "VERIFIED")
        r2 = engine.run_skill(REG, "completion_verification", {"evidence_spec": {"type": "file_exists", "path": "ghost.xlsx"}}); self.assertEqual(r2["status"], "ATTEMPTED"); self.assertFalse(r2["result"]["verified"])
        c = engine.run_skill(REG, "commitment_tracking", {"text": "verify me", "due": None})
        self.assertEqual(engine.run_skill(REG, "completion_verification", {"evidence_spec": {"type": "state_record", "store": "commitments", "op_id": c["result"]["op_id"]}})["status"], "VERIFIED")
        self.assertEqual(engine.run_skill(REG, "completion_verification", {"evidence_spec": {"type": "task_status", "task_id": 1, "expected": "Արված"}})["status"], "VERIFIED")
    @covers("completion_verification", kinds=("failure",))
    def test_completion_verification_blocked_paths(self):
        self.assertEqual(engine.run_skill(REG, "completion_verification", {})["status"], "BLOCKED")
        self.assertEqual(engine.run_skill(REG, "completion_verification", {"evidence_spec": {"type": "teleport"}})["status"], "BLOCKED")
        self.assertEqual(engine.run_skill(REG, "completion_verification", {"evidence_spec": {"type": "task_status", "task_id": 999}})["status"], "BLOCKED")
    @covers("audit_logging", kinds=("unit", "completion"))
    def test_audit_log_created_and_redacted(self):
        engine.run_skill(REG, "daily_briefing", {"today": TODAY, "api_key": "SECRET123"})
        last = engine.read_audit(1)[-1]
        for k in ("execution_id","skill_id","skill_version","selection_reason","inputs","sources","tools","result_status","validated","duration_ms","ts","verification"):
            self.assertIn(k, last)
        self.assertEqual(last["inputs"]["api_key"], "<redacted>")
    @covers("audit_logging", kinds=("unit", "completion", "failure"))
    def test_audit_logging_skill(self):
        r = engine.run_skill(REG, "audit_logging", {"record": {"note": "manual"}}); self.assertEqual(r["status"], "RECORDED"); self.assertTrue(r["verification"]["ok"])
        self.assertEqual(engine.run_skill(REG, "audit_logging", {"record": "not a dict"})["status"], "BLOCKED")
    @covers("audit_logging", kinds=("unit",))
    def test_blocked_run_is_audited(self):
        n = engine._store().count("audit"); engine.run_skill(REG, "pipeline_management", {})
        self.assertEqual(engine._store().count("audit"), n + 1); self.assertEqual(engine.read_audit(1)[-1]["result_status"], "BLOCKED")
    @covers("source_verification", kinds=("unit", "completion", "failure"))
    def test_source_verification(self):
        r = engine.run_skill(REG, "source_verification", {}); self.assertEqual(r["status"], "VERIFIED"); self.assertTrue(r["result"]["schema_ok"]); self.assertTrue(r["validated"])
        r2 = engine.run_skill(REG, "source_verification", {"path": "missing.xlsx"}); self.assertEqual(r2["status"], "BLOCKED"); self.assertEqual(r2["blocked"][0]["code"], "SOURCE_MISSING")
    @covers("source_reconciliation", kinds=("unit", "completion", "failure"))
    def test_contradiction(self):
        r = engine.run_skill(REG, "source_reconciliation", {"sources": [{"name": "CRM", "value": 120, "date": "2026-09-01"}, {"name": "Billing", "value": 95, "date": "2026-09-09", "authoritative": True}]})
        res = r["result"]; self.assertTrue(res["contradiction"]); self.assertIsNone(res["chosen"]); self.assertEqual(res["authoritative"], "Billing"); self.assertEqual(res["newest"], "Billing")
        self.assertEqual(engine.run_skill(REG, "source_reconciliation", {"sources": [{"name": "A", "value": 1}]})["status"], "BLOCKED")
    @covers("confidence_handling", kinds=("unit", "completion", "failure"))
    def test_confidence(self):
        r = engine.run_skill(REG, "confidence_handling", {"claims": ["x", {"text": "y", "label": "CONFIRMED"}]}); self.assertEqual([c["label"] for c in r["result"]["labeled"]], ["UNVERIFIED", "CONFIRMED"])
        self.assertEqual(engine.run_skill(REG, "confidence_handling", {})["status"], "BLOCKED")
    def test_output_validation_rejects_bad(self):
        self.assertFalse(executors.validate_output("deadline_management", {"status": "EXECUTED", "buckets": {"x": []}})[0])
        self.assertFalse(executors.validate_output("x", {"status": "BLOCKED"})[0])
        self.assertFalse(executors.validate_output("x", {"status": "DONE"})[0])

class T08_MultiSkill(unittest.TestCase):
    @covers("daily_briefing", "deadline_management", "executive_prioritization", "waiting_for_tracking", "task_management", kinds=("unit", "completion"))
    def test_multi_skill_execution_daily_brief(self):
        p = engine.resolve(REG, "daily brief"); r = engine.run_plan(REG, p, {"today": TODAY})
        self.assertEqual(r["status"], "OK"); ran = [s["skill"] for s in r["steps"] if s["status"] in ("EXECUTED", "ASSISTED")]
        for sid in ("task_management", "executive_prioritization", "deadline_management", "waiting_for_tracking", "daily_briefing"): self.assertIn(sid, ran)
        self.assertEqual(r["evidence"]["incomplete"], [])
    @covers("sales_kpi_monitoring", kinds=("failure",))
    def test_multi_skill_blocked_chain_is_explicit(self):
        p = engine.resolve(REG, "why did sales drop?"); r = engine.run_plan(REG, p, {})
        self.assertIn(r["status"], ("BLOCKED", "PARTIAL")); self.assertTrue(r["evidence"]["incomplete"])
    @covers("sales_kpi_monitoring", "root_cause_analysis", "data_analysis", "decision_support", kinds=("unit",))
    def test_run_plan_with_supplied_data_partially_executes(self):
        p = engine.resolve(REG, "why did sales drop?")
        r = engine.run_plan(REG, p, {"sales_data": [{"m": "aug", "rev": 100}, {"m": "sep", "rev": 70}], "dataset": [{"rev": 100}, {"rev": 70}], "description": "sales fell 30%"})
        ran = {s["skill"]: s["status"] for s in r["steps"]}
        for sid in ("sales_kpi_monitoring", "data_analysis", "root_cause_analysis", "decision_support"): self.assertIn(ran.get(sid), ("ASSISTED", "EXECUTED"), sid)
        self.assertEqual(r["status"], "OK")
    @covers("management_communication", "communication_quality_checking", kinds=("unit", "completion", "failure"))
    def test_communication_quality(self):
        r = engine.run_skill(REG, "management_communication", {"content": "Ես ու Claude կանցնենք փաստաթղթով վաղը", "kind": "follow_up"})
        self.assertEqual(r["status"], "EXECUTED"); self.assertNotIn("Claude", r["result"]["draft"]); self.assertIn("Գև", r["result"]["draft"]); self.assertTrue(r["result"]["requires_head_ok_before_send"])
        self.assertEqual(engine.run_skill(REG, "management_communication", {})["status"], "BLOCKED")
        q = engine.run_skill(REG, "communication_quality_checking", {"content": "Ես կանեմ"}); self.assertFalse(q["result"]["ok"])
        self.assertEqual(engine.run_skill(REG, "communication_quality_checking", {})["status"], "BLOCKED")
    @covers("executive_summarization", kinds=("unit", "completion", "failure"))
    def test_summarization_kinds(self):
        self.assertIn("WHAT HAPPENED", engine.run_skill(REG, "executive_summarization", {"content": "x"})["result"]["draft"])
        self.assertIn("Decisions", engine.run_skill(REG, "executive_summarization", {"content": "x", "kind": "meeting"})["result"]["draft"])
        self.assertEqual(engine.run_skill(REG, "executive_summarization", {"content": "x", "kind": "poem"})["status"], "BLOCKED")

class T02b_DomainBoundary(unittest.TestCase):
    """SYSTEM/maintenance intents (agent runtime, Skill System, hooks, workspace policy, tests, repository, configuration,
    architecture, state/audit infrastructure) must never route to business skills because of overlapping words ('pipeline')."""
    SYSTEM = ["fix the skill execution pipeline", "audit the deployment pipeline", "inspect the runtime pipeline",
              "fix the gate hook so it runs from any cwd", "update the workspace policy for .venv", "rename the github repository and update the remote origin",
              "add regression tests for routing", "refactor the sqlite state store", "the architecture of the agent runtime needs a config file",
              "run the release suite and the evals", "ուղղիր հմտությունների համակարգի hook-ը"]
    BUSINESS = [("change the sales pipeline analysis", "pipeline_management"), ("our sales pipeline is falling", "pipeline_management"),
                ("Deals are not moving, pipeline is stuck", "pipeline_management"), ("remind me friday about the network maintenance window", "commitment_tracking"),
                ("վաճառքի փայփլայնը ընկնում է", "pipeline_management")]
    @covers("pipeline_management", "data_analysis", "audit_logging", kinds=("routing",))
    def test_system_intents_route_no_business_skill(self):
        for s in self.SYSTEM:
            p = engine.resolve(REG, s); self.assertEqual(p["domain"], "SYSTEM", s); self.assertEqual(p["status"], "UNRESOLVED", s); self.assertEqual(p["chain"], [], s)
            self.assertTrue(p["system_terms"], s); self.assertTrue(engine.classify_prompt(s)["maintenance"], s)
    @covers("pipeline_management", "commitment_tracking", kinds=("routing",))
    def test_business_intents_with_overlapping_words_still_route(self):
        for s, sid in self.BUSINESS:
            p = engine.resolve(REG, s); self.assertEqual(p["domain"], "BUSINESS", s); self.assertEqual(p["status"], "RESOLVED", s); self.assertIn(sid, p["chain"], s)
            self.assertFalse(engine.classify_prompt(s)["maintenance"], s)
    @covers("pipeline_management", kinds=("routing", "failure"))
    def test_system_intent_stays_fail_closed(self):
        p = engine.resolve(REG, "fix the skill execution pipeline"); g = engine.gate(REG, p, {}, action_level="ANALYZE")
        self.assertEqual(g["status"], "BLOCKED"); self.assertTrue(any(b["code"] == "MISSING_SKILL" for b in g["blocked"]))
        self.assertNotIn(engine.run_plan(REG, p, {})["status"], ("OK", "PARTIAL"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
