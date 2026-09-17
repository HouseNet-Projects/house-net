# -*- coding: utf-8 -*-
"""FAIL-CLOSED suite — one explicit test per blocked condition. A blocked skill is never represented as executed;
partial execution preserves completed evidence and marks the whole task incomplete."""
import unittest, copy, tempfile, pathlib, sys, os, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "skills"))
import engine, executors, store
from testing import covers

TMP = pathlib.Path(tempfile.mkdtemp(prefix="skillfc_"))
engine.STATE_DIR = TMP / "state"; store.reset()
REG = engine.load_registry(); T = "2026-09-10"
CORE = ("task_management", "deadline_management", "waiting_for_tracking", "daily_briefing", "commitment_tracking",
        "authority_checking", "approval_management", "completion_verification", "audit_logging", "source_verification")

def one(chain, inputs=None, level="ANALYZE", token=None, reg=REG):
    return engine.gate(reg, {"status": "RESOLVED", "chain": list(chain)}, inputs or {}, level, token)

class F01_EveryBlockedCode(unittest.TestCase):
    @covers(*CORE, kinds=("failure",))
    def test_MISSING_SKILL(self):
        g = one(["ghost_skill"]); self.assertEqual(g["status"], "BLOCKED"); self.assertEqual(g["blocked"][0]["code"], "MISSING_SKILL")
        g2 = one(["five_whys"]); self.assertEqual(g2["blocked"][0]["code"], "MISSING_SKILL"); self.assertIn("retired", g2["blocked"][0]["reason"])
        r = engine.run_skill(REG, "ghost_skill", {}); self.assertEqual(r["status"], "BLOCKED")
    @covers(*CORE, kinds=("failure",))
    def test_DISABLED_SKILL(self):
        r = copy.deepcopy(REG); r["_index"]["daily_briefing"]["status"] = "disabled"
        g = one(["daily_briefing"], reg=r); self.assertEqual(g["blocked"][0]["code"], "DISABLED_SKILL")
        self.assertEqual(engine.run_skill(r, "daily_briefing", {"today": T})["status"], "BLOCKED")
    @covers("commitment_tracking", "reminder_intelligence", "completion_verification", kinds=("failure",))
    def test_MISSING_INPUT(self):
        for sid in ("commitment_tracking", "reminder_intelligence", "completion_verification", "escalation_management"):
            g = one([sid]); self.assertEqual(g["blocked"][0]["code"], "MISSING_INPUT", sid); self.assertEqual(engine.run_skill(REG, sid, {})["status"], "BLOCKED", sid)
    @covers("sales_funnel_analysis", "pipeline_management", kinds=("failure",))
    def test_TOOL_UNAVAILABLE(self):
        g = one(["sales_funnel_analysis"], {"sales_data": [{"x": 1}]}); self.assertEqual(g["blocked"][0]["code"], "TOOL_UNAVAILABLE")
        p = engine.resolve(REG, "call the api and post it"); g2 = engine.gate(REG, p, {"content": "hi"}); self.assertTrue(any(b["code"] == "TOOL_UNAVAILABLE" for b in g2["blocked"]))
        self.assertEqual(engine.run_skill(REG, "pipeline_management", {"sales_data": []})["status"], "BLOCKED")
    @covers("pipeline_management", kinds=("failure",))
    def test_NOT_OPERATIONAL(self):
        r = copy.deepcopy(REG); r["_index"]["pipeline_management"]["required_tools"] = []
        g = one(["pipeline_management"], {"sales_data": [{"x": 1}]}, reg=r); self.assertEqual(g["blocked"][0]["code"], "NOT_OPERATIONAL")
        r2 = copy.deepcopy(REG); r2["_index"]["data_analysis"]["executor"] = None
        self.assertEqual(one(["data_analysis"], {"dataset": [{"x": 1}]}, reg=r2)["blocked"][0]["code"], "NOT_OPERATIONAL")
    @covers(*CORE, kinds=("failure", "authority"))
    def test_AUTHORITY_EXCEEDED(self):
        for sid in CORE:
            g = one([sid], {"text": "x", "action_level": "READ", "evidence_spec": {"type": "file_exists", "path": "x"}, "record": {}, "path": "Tasks.xlsx"}, level="EXECUTE_MATERIAL", token="HEAD-OK")
            self.assertEqual(g["blocked"][0]["code"], "AUTHORITY_EXCEEDED", sid)
        self.assertEqual(engine.gate(REG, {"status": "RESOLVED", "chain": ["task_management"]}, {}, "NUKE")["blocked"][0]["code"], "AUTHORITY_EXCEEDED")
    @covers("approval_management", "authority_checking", "task_management", kinds=("failure", "authority"))
    def test_APPROVAL_REQUIRED(self):
        r = copy.deepcopy(REG); r["_index"]["task_management"]["authority_boundary"]["max_action"] = "EXECUTE_EXTERNAL"
        g = one(["task_management"], level="EXECUTE_EXTERNAL", reg=r); self.assertEqual(g["blocked"][0]["code"], "APPROVAL_REQUIRED")
        g2 = one(["task_management"], level="EXECUTE_EXTERNAL", token="HEAD-OK-2026-09-10", reg=r); self.assertEqual(g2["status"], "OK")
        self.assertEqual(engine.run_skill(REG, "approval_management", {"action_level": "EXECUTE_EXTERNAL"})["blocked"][0]["code"], "APPROVAL_REQUIRED")
    @covers("task_management", "deadline_management", "daily_briefing", "waiting_for_tracking", "source_verification", kinds=("failure",))
    def test_INVALID_SOURCE(self):
        g = one(["task_management"], {"path": str(TMP / "missing.xlsx")}); self.assertEqual(g["blocked"][0]["code"], "INVALID_SOURCE")
        bad = TMP / "bad.xlsx"; bad.write_bytes(b"not an xlsx")
        g2 = one(["deadline_management", "task_management"], {"path": str(bad)}); self.assertTrue(all(b["code"] == "INVALID_SOURCE" for b in g2["blocked"])); self.assertEqual(g2["status"], "BLOCKED")
    @covers("task_management", "deadline_management", "daily_briefing", "waiting_for_tracking", "source_verification", kinds=("failure",))
    def test_STALE_SOURCE(self):
        import openpyxl
        p = TMP / "stale.xlsx"; wb = openpyxl.Workbook(); ws = wb.active; ws.title = "ԱՌԱՋԱԴՐԱՆՔՆԵՐ"
        for c, v in zip((2, 3, 6, 7, 11, 12), ("№", "Առաջադրանք", "Կարգավիճակ", "Մեկնաբանությունը", "Ժամկետ", "Պատասխանատու")): ws.cell(row=12, column=c, value=v)
        wb.save(p); old = time.time() - 30 * 24 * 3600; os.utime(p, (old, old))
        g = one(["daily_briefing"], {"path": str(p)}); self.assertEqual(g["blocked"][0]["code"], "STALE_SOURCE")
        self.assertEqual(one(["daily_briefing"], {"path": str(p), "accept_stale": True})["status"], "OK")
    @covers("source_reconciliation", "confidence_handling", "decision_support", "data_analysis", kinds=("failure",))
    def test_CONFLICTING_SOURCE(self):
        srcs = [{"name": "CRM", "value": 120}, {"name": "Billing", "value": 95}]
        g = one(["data_analysis"], {"dataset": [{"x": 1}], "sources": srcs}); self.assertEqual(g["blocked"][0]["code"], "CONFLICTING_SOURCE")
        self.assertEqual(one(["source_reconciliation"], {"sources": srcs})["status"], "OK")
        # chain propagation: reconciliation surfaces a contradiction → downstream consumer is blocked, not fed a silently chosen value
        p = {"status": "RESOLVED", "chain": ["source_reconciliation", "decision_support"], "intent": "x", "reasons": []}
        r = engine.run_plan(REG, p, {"sources": srcs, "issue": "which figure to report"})
        st = {s["skill"]: s for s in r["steps"]}; self.assertEqual(st["source_reconciliation"]["status"], "EXECUTED")
        self.assertEqual(st["decision_support"]["status"], "BLOCKED"); self.assertEqual(st["decision_support"]["blocked"][0]["code"], "CONFLICTING_SOURCE"); self.assertEqual(r["status"], "PARTIAL")
    @covers("deadline_management", "executive_prioritization", "waiting_for_tracking", kinds=("failure",))
    def test_VALIDATION_FAILED(self):
        orig = executors.executive_prioritization
        executors.executive_prioritization = lambda inputs, skill=None, reg=None: {"status": "EXECUTED", "ranked": [{"P": "P9"}], "p1_count": 0}
        try:
            r = engine.run_skill(REG, "executive_prioritization", {"today": T}); self.assertEqual(r["status"], "VALIDATION_FAILED"); self.assertNotIn(r["status"], engine.SUCCESS_STATUSES)
            self.assertEqual(engine.read_audit(1)[-1]["result_status"], "VALIDATION_FAILED")
        finally: executors.executive_prioritization = orig
    @covers("commitment_tracking", "decision_logging", "daily_briefing", "task_management", kinds=("failure",))
    def test_VERIFICATION_FAILED(self):
        orig = executors.task_management
        executors.task_management = lambda inputs, skill=None, reg=None: {"status": "EXECUTED", "count": 999, "open": 0, "tasks": [], "source": "x"}
        try:
            r = engine.run_skill(REG, "task_management", {}); self.assertEqual(r["status"], "VERIFICATION_FAILED"); self.assertFalse(r["verification"]["ok"])
        finally: executors.task_management = orig
        p = {"status": "RESOLVED", "chain": ["completion_verification"], "intent": "x", "reasons": []}
        r = engine.run_plan(REG, p, {"evidence_spec": {"type": "file_exists", "path": "does_not_exist.docx"}})
        self.assertEqual(r["steps"][0]["status"], "ATTEMPTED"); self.assertNotEqual(r["status"], "OK"); self.assertTrue(r["evidence"]["incomplete"])

class F02_NeverMisrepresented(unittest.TestCase):
    @covers(*CORE, kinds=("failure",))
    def test_blocked_never_carries_result_data_as_success(self):
        for sid in CORE:
            r = engine.run_skill(REG, sid, {}, action_level="EXECUTE_MATERIAL")
            self.assertEqual(r["status"], "BLOCKED", sid); self.assertNotIn("result", r); self.assertTrue(r["blocked"])
            self.assertEqual(engine.read_audit(1)[-1]["result_status"], "BLOCKED")
    @covers("daily_briefing", "sales_kpi_monitoring", "data_analysis", "root_cause_analysis", "decision_support", kinds=("failure",))
    def test_partial_preserves_completed_evidence_and_marks_incomplete(self):
        p = engine.resolve(REG, "why did sales drop?")
        r = engine.run_plan(REG, p, {"sales_data": [{"rev": 100}, {"rev": 70}]})
        self.assertEqual(r["status"], "PARTIAL")
        done = {c["skill"] for c in r["evidence"]["completed"]}; inc = {c["skill"]: c["codes"] for c in r["evidence"]["incomplete"]}
        self.assertIn("sales_kpi_monitoring", done); self.assertIn("data_analysis", inc); self.assertEqual(inc["data_analysis"], ["MISSING_INPUT"])
        plan_rec = engine.read_audit(1)[-1]; self.assertEqual(plan_rec["skill_id"], "<plan>"); self.assertEqual(plan_rec["result_status"], "PARTIAL"); self.assertIn("data_analysis", plan_rec["incomplete"])
    def test_all_twelve_codes_are_declared(self):
        self.assertEqual(len(engine.BLOCK_CODES), 12)
        for code in engine.BLOCK_CODES: self.assertTrue(any(code in n for n in dir(F01_EveryBlockedCode)), code)

if __name__ == "__main__":
    unittest.main(verbosity=2)
