# -*- coding: utf-8 -*-
"""BUSINESS OPERATING MODEL suite — Core/Overlay separation, provenance & precedence, staleness, schema compatibility,
role → person resolution, knowledge promotion rules, rebuild reproducibility, certification, and Skill System consumption
(business context injected into governed execution; fail-closed gap codes when unknown).
Mechanics run on a SYNTHETIC model (schema 2.0) in a temp dir (COMMAND_CENTER_BUSINESS_DIR/ROOT); the real model in
.claude/business is validated too when present (its overlay is company-internal and never versioned)."""
import unittest, json, os, sys, pathlib, tempfile, copy, importlib, hashlib, shutil
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "skills")); sys.path.insert(0, str(ROOT / ".claude" / "business")); sys.path.insert(0, str(ROOT / ".claude" / "policy"))
from testing import covers
sys.path.insert(0, str(ROOT / '.claude' / 'policy')); import paths as pp   # ONE business-root resolver
def W(rel): return pp.to_repo(rel)
import engine, executors, store, business

TMP = pathlib.Path(tempfile.mkdtemp(prefix="skillbiz_")); engine.STATE_DIR = TMP / "state"; store.reset()
REG = engine.load_registry()
REAL = ROOT / ".claude" / "business"
GOV = ("authority_checking", "approval_management", "completion_verification", "audit_logging")
BQ = "business_model_query"

def _meta(layer="CORE", **kw):
    m = {"model_version": "2026-09-10.test", "schema_version": "2.0", "generated_at": "2026-09-10T00:00:00", "source_snapshot_id": "snap-test", "core_fingerprint": "core-test", "overlay_fingerprint": None, "business_effective_date": "UNKNOWN", "layer": layer}
    m.update(kw); return m

def synthetic(d, overlay=True, schema="2.0", stale_source=False, missing_source=False, certified=True):
    """Minimal valid two-layer model: S01 (Reference, approved) S02/S03 (Active drafts) S09 (Historical); one conflict; one unknown owner.
    Source files are created under d/src so staleness can be exercised."""
    root = d / "src"
    for a in ("02_Reference", "01_Active", "05_Archive"): (root / W(a)).mkdir(parents=True)
    files = {"S01": "02_Reference/X.xlsx", "S02": "01_Active/Y.docx", "S03": "01_Active/Z.docx", "S09": "05_Archive/old.md"}
    for sid, rel in files.items(): (root / W(rel)).write_bytes(f"content {sid}".encode())
    snap = {}
    for sid, rel in files.items():
        p = root / W(rel); st = p.stat(); snap[sid] = {"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size": st.st_size, "mtime": int(st.st_mtime), "currency": "HISTORICAL" if sid == "S09" else "CURRENT", "authority": "HISTORICAL" if sid == "S09" else ("REFERENCE_APPROVED" if sid == "S01" else "ACTIVE_DRAFT")}
    if stale_source: (root / W(files["S01"])).write_bytes(b"CHANGED staffing plan"); os.utime(root / W(files["S01"]), (1, 1))
    if missing_source: (root / W(files["S02"])).unlink()
    S = lambda sid, auth, cur, status, conf: {"source_id": sid, "path": files[sid], "title": sid, "authority": auth, "currency": cur, "status": status, "conflicts": conf, "domain": "T", "effective_date": "UNKNOWN", "date": "2026-09-09", "owner": "Gev", "source_type": "x", "notes": ""}
    sources = {"meta": _meta(schema_version=schema), "authority_rank": {"REFERENCE_APPROVED": 5, "CHARTER": 5, "ACTIVE_REGISTER": 4, "ACTIVE_DRAFT": 3, "PROPOSAL": 3, "EVIDENCE": 2, "HISTORICAL": 1}, "source_snapshot": snap,
               "sources": [S("S01", "REFERENCE_APPROVED", "CURRENT", "APPROVED", ["C01"]), S("S02", "ACTIVE_DRAFT", "CURRENT", "DRAFT", ["C01"]), S("S03", "ACTIVE_DRAFT", "CURRENT", "DRAFT", []), S("S09", "HISTORICAL", "HISTORICAL", "SUPERSEDED", [])]}
    role = lambda code, title, fn: {"code": code, "title": title, "function": fn, "manager": "Head of S&O", "reports": [], "positions": 1, "filled": 1, "vacancy_priority": "-", "compensation": "OVERLAY", "purpose": title, "decision_rights": [], "escalation_path": [], "inputs": [], "outputs": [], "dependencies": [], "work_nature": "office", "kpis": "", "src": ["S01"], "conf": "CONFIRMED"}
    bm = {"meta": _meta(), "company": {"name": {"value": "TestCo", "src": ["S01"], "conf": "CONFIRMED"}}, "functions": [], "systems": [], "sales": {}, "operations": {}, "people_model": {},
          "roles": [role("1.1", "Sales Head", "FN-COM"), role("1.4", "Telesales Senior", "FN-COM"), role("3.3", "Retention Specialist", "FN-CS")],
          "principals": [{"id": "@P1", "org_relation": "approver", "conf": "UNVERIFIED", "src": ["S02"]}],
          "conflicts": [{"id": "C01", "topic": "retention owner", "source_a": "S01 says role 3.3", "source_b": "S02 says role 1.4", "newer": "S02", "apparent_authority": "S01", "business_impact": "x", "resolution_required": "Gev decides", "status": "OPEN"}],
          "critical_unknowns": [{"id": "U01", "item": "what declines 2%", "src": ["S02"]}]}
    proc = lambda pid, name, owner, status, src: {"process_id": pid, "name": name, "purpose": name, "trigger": "t", "inputs": [], "steps": ["TRIGGER t", "VERIFY v"], "accountable_owner": owner, "participants": [], "systems": [], "decision_points": [], "approvals": [], "exceptions": [], "handoffs": [], "output": "", "completion_criteria": "", "kpi": ["K-NEW"], "sla_deadline": "UNKNOWN", "escalation_condition": "", "src": src, "status": status, "conf": "CONFIRMED"}
    processes = {"meta": _meta(), "flow_vocabulary": [], "processes": [proc("P-OPS-01", "New connection installation", "Installation head (2.3)", "DOCUMENTED", ["S01"]), proc("P-SALES-05", "Corporate sales", "OWNER_UNKNOWN", "GAP", ["S02"]), proc("P-RET-01", "Retention calling", "Retention Specialist (3.3)", "PARTIAL", ["S01", "S02"])]}
    ownership = {"meta": _meta(), "statuses": ["ROLE_AND_PERSON", "ROLE_DEFINED_PERSON_UNKNOWN", "ROLE_VACANT_INTERIM", "CONFLICT", "OWNER_UNKNOWN"], "ownership": [
        {"id": "OW-1", "kind": "KPI", "primitive": "sales plan", "owner_role": "Sales Head (1.1)", "owner_person": "UNKNOWN", "status": "ROLE_DEFINED_PERSON_UNKNOWN", "src": ["S01"], "aliases": ["sales"]},
        {"id": "OW-2", "kind": "KPI", "primitive": "churn", "owner_role": "Retention Specialist (3.3) vs Telesales Senior (1.4)", "owner_person": "UNKNOWN", "status": "CONFLICT", "src": ["S01", "S02"], "aliases": ["churn"], "note": "C01"},
        {"id": "OW-3", "kind": "REPORT", "primitive": "corporate report", "owner_role": None, "owner_person": None, "status": "OWNER_UNKNOWN", "src": ["S02"], "aliases": ["corporate report"]},
        {"id": "OW-4", "kind": "PROCESS", "primitive": "retention process", "owner_role": "Retention Specialist (3.3)", "owner_person": "UNKNOWN", "status": "ROLE_DEFINED_PERSON_UNKNOWN", "src": ["S01"], "aliases": ["retention process"]},
        {"id": "OW-5", "kind": "PROCESS", "primitive": "telesales process", "owner_role": "Telesales Senior (1.4)", "owner_person": "UNKNOWN", "status": "ROLE_DEFINED_PERSON_UNKNOWN", "src": ["S01"], "aliases": ["telesales"]}]}
    kpis = {"meta": _meta(), "kinds": ["OUTCOME", "DRIVER", "OPERATIONAL"], "kpis": [
        {"kpi_id": "K-NEW", "name": "New activations", "kind": "OUTCOME", "definition": "activated deals per month", "business_purpose": "growth sales", "formula": "count", "unit": "n", "source": "MB", "owner": "Sales Head (1.1)", "reporting_frequency": "monthly", "target": "UNKNOWN", "target_ref": None, "proposed_targets": [{"id": "TG-P", "value": 55, "unit": "n", "src": ["S03"]}], "thresholds": [], "warning_threshold": "UNKNOWN", "critical_threshold": "UNKNOWN", "drill_down": ["branch"], "driver_kpis": [], "outcome_kpis": [], "action_when_off_target": "PB-01", "src": ["S01"], "conf": "CONFIRMED"},
        {"kpi_id": "K-D2D", "name": "D2D packages", "kind": "DRIVER", "definition": "packages per agent", "business_purpose": "d2d", "formula": "count", "unit": "n", "source": "MB", "owner": "Sales Head (1.1)", "reporting_frequency": "monthly", "target": 10, "target_ref": "TG-A", "proposed_targets": [], "thresholds": [], "warning_threshold": "UNKNOWN", "critical_threshold": "UNKNOWN", "drill_down": [], "driver_kpis": [], "outcome_kpis": [], "action_when_off_target": "", "src": ["S01"], "conf": "CONFIRMED"}],
        "role_kpis": {"1.1": [{"kpi_id": "R-1.1-1", "name": "plan", "weight": 1.0, "direction": "up", "unit": "%", "source": "MB", "target": "UNKNOWN", "kind": "OPERATIONAL", "src": ["S01"], "conf": "CONFIRMED"}]}}
    targets = {"meta": _meta(), "promotion_states": business.PROMOTION_STATES, "promotion_rules": {"max_state_by_authority": {"EVIDENCE": "OBSERVATION", "ACTIVE_REGISTER": "OBSERVATION", "PROPOSAL": "PROPOSED", "ACTIVE_DRAFT": "PROPOSED", "CHARTER": "APPROVED", "REFERENCE_APPROVED": "APPROVED", "HISTORICAL": "SUPERSEDED"}, "promotions": [], "forbidden": []},
               "targets": [{"target_id": "TG-A", "kind": "KPI_TARGET", "ref": "K-D2D", "value": 10, "unit": "n", "effective_date": "UNKNOWN", "approver": "@P1", "src": ["S01"], "scope": "d2d", "status": "APPROVED", "review_date": "UNKNOWN"},
                           {"target_id": "TG-P", "kind": "KPI_TARGET", "ref": "K-NEW", "value": 55, "unit": "n", "effective_date": "NOT_APPROVED", "approver": "pending", "src": ["S03"], "scope": "baseline", "status": "PROPOSED", "review_date": "UNKNOWN"}]}
    playbooks = {"meta": _meta(), "flow": [], "executive_format": "WHAT HAPPENED · WHY · CAUSE · RECOMMENDATION · OWNER · WHEN · GEV", "playbooks": [
        {"playbook_id": "PB-01", "name": "Sales decline", "trigger": "sales down", "chain": "investigate_sales_decline", "required_skills": ["sales_kpi_monitoring"], "required_data": ["activations by branch"], "required_sources": ["S01"], "diagnostic_steps": ["verify"], "questions_to_answer": ["where?"], "business_impact": "x", "authority_boundary": "RECOMMEND", "escalation_threshold": "2 months", "expected_recommendation": "r", "action_format": "f", "owner": "Sales Head (1.1)", "deadline_logic": "2 days", "completion_evidence": "e", "flow": [], "src": ["S01"]}]}
    routines = {"meta": _meta(), "routines": [{"routine_id": "RT-DAILY", "name": "Daily", "cadence": "daily", "owner": "Deputy", "skill_chain": "daily_brief", "sections": ["top"], "data_available_today": [], "data_missing": ["MB feed"], "rule": "no numbers", "src": ["S01"]}]}
    gaps = {"meta": _meta(), "gap_codes": business.GAP_CODES, "gaps": [{"gap_id": "GAP-01", "category": "missing ownership", "gap": "corporate report owner", "impact": "i", "risk": "r", "recommended_resolution": "x", "proposed_owner": "Gev", "priority": "P1", "src": ["S02"]}]}
    for name, obj in (("sources", sources), ("business_model", bm), ("processes", processes), ("ownership", ownership), ("kpis", kpis), ("targets", targets), ("playbooks", playbooks), ("routines", routines), ("gaps", gaps)):
        (d / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    if overlay:
        ov = {"meta": _meta("SENSITIVE_" + "OVERLAY", overlay_fingerprint="ov-test"), "layer": "SENSITIVE_" + "OVERLAY", "classification": "CONFIDENTIAL",
              "persons": [{"id": "@P1", "name": "Fixturina Approver", "aliases": []}, {"id": "@P5", "name": "Fixturo Tele", "aliases": []}],
              "assignments": [{"role": "1.4", "person": "@P5", "conf": "CONFIRMED", "src": ["S01"], "verified_by": "fixture", "date": "2026-09-10"}, {"role": "3.3", "person": "@P5", "conf": "DERIVED", "src": ["S02"], "verified_by": None, "date": "2026-09-10"}],
              "compensation": {"fix_salary_net_amd": {"1.1": 1}, "src": ["S01"]}, "commercials": [], "evidence": [], "source_payloads": {}}
        (d / "overlay.json").write_text(json.dumps(ov, ensure_ascii=False), encoding="utf-8")
    if certified: (d / "certification.json").write_text(json.dumps({"result": "PASS", "core_fingerprint": "core-test", "source_snapshot_id": "snap-test", "model_version": "2026-09-10.test"}), encoding="utf-8")
    return d, root

class B00(unittest.TestCase):
    overlay = True; schema = "2.0"; stale = False; missing = False; certified = True
    def setUp(self):
        self.d, self.root = synthetic(pathlib.Path(tempfile.mkdtemp(prefix="bizmodel_")), overlay=self.overlay, schema=self.schema, stale_source=self.stale, missing_source=self.missing, certified=self.certified)
        os.environ["COMMAND_CENTER_BUSINESS_DIR"] = str(self.d); os.environ["COMMAND_CENTER_BUSINESS_ROOT"] = str(self.root); business.load(force=True)
    def tearDown(self):
        os.environ.pop("COMMAND_CENTER_BUSINESS_DIR", None); os.environ.pop("COMMAND_CENTER_BUSINESS_ROOT", None); business.load(force=True)
    def switch(self, **kw):
        d, root = synthetic(pathlib.Path(tempfile.mkdtemp(prefix="bizalt_")), **kw)
        os.environ["COMMAND_CENTER_BUSINESS_DIR"] = str(d); os.environ["COMMAND_CENTER_BUSINESS_ROOT"] = str(root); business.load(force=True); return d, root

class B01_ProvenanceAndPrecedence(B00):
    @covers(BQ, "source_verification", kinds=("unit",))
    def test_every_fact_has_source_and_confidence_and_source_status_answers(self):
        m = business.load(); ids = {s["source_id"] for s in m["sources"]["sources"]}
        for r in m["business_model"]["roles"] + m["processes"]["processes"] + m["kpis"]["kpis"] + m["targets"]["targets"]:
            self.assertTrue(r["src"] and set(r["src"]) <= ids, r); self.assertIn(r.get("conf", "CONFIRMED"), business.CONF_ORDER)
        s = business.source_status("S01"); self.assertTrue(s["approved"] and s["currency"] == "CURRENT" and not s["changed_since_build"]); self.assertEqual(s["conflicts"], ["C01"])
        self.assertFalse(business.source_status("S09")["approved"]); self.assertFalse(business.source_status("S99")["known"])
    @covers(BQ, kinds=("unit",))
    def test_current_vs_historical_and_archive_never_overrides(self):
        self.assertTrue(business.is_current("S01")); self.assertFalse(business.is_current("S09"))
        self.assertEqual(business.resolve_fact([{"value": "old", "src": ["S09"]}])["status"], "HISTORICAL_ONLY")
        self.assertEqual(business.resolve_fact([{"value": "archived", "src": ["S09"]}, {"value": "current-draft", "src": ["S02"]}])["value"], "current-draft")
    @covers(BQ, "source_reconciliation", kinds=("unit", "failure"))
    def test_conflict_not_silently_chosen_and_reference_precedence(self):
        r = business.resolve_fact([{"value": "A", "src": ["S02"]}, {"value": "B", "src": ["S03"]}]); self.assertEqual(r["status"], "SOURCE_CONFLICT"); self.assertIsNone(r["value"])
        r = business.resolve_fact([{"value": "draft", "src": ["S02"]}, {"value": "approved", "src": ["S01"]}]); self.assertEqual(r["value"], "approved"); self.assertTrue(r.get("overridden"))

class B02_CoreOverlaySeparation(B00):
    @covers(BQ, "data_sensitivity_awareness", kinds=("unit", "adversarial"))
    def test_core_has_no_compensation_or_names_and_overlay_merges_at_runtime(self):
        m = business.load()
        for r in m["business_model"]["roles"]: self.assertNotIn("fix_salary_net_amd", r); self.assertEqual(r["compensation"], "OVERLAY")
        core_blob = " ".join(json.dumps(m[f], ensure_ascii=False) for f in business.CORE_FILES)
        for p in m["_overlay"]["persons"]: self.assertNotIn(p["name"], core_blob)
        self.assertEqual(business.render("approver @P1"), "approver Fixturina Approver")
        self.assertEqual(business.compensation_for("1.1")["fix_salary_net_amd"], 1)
    @covers(BQ, kinds=("unit",))
    def test_role_to_current_person_only_via_confirmed_assignment(self):
        self.assertEqual(business.person_for_role("1.4")["status"], "PERSON_KNOWN"); self.assertEqual(business.person_for_role("1.4")["person"], "Fixturo Tele")
        p = business.person_for_role("3.3"); self.assertEqual(p["status"], "PERSON_UNKNOWN"); self.assertEqual(p["candidates"][0]["conf"], "DERIVED")
        self.assertEqual(business.person_for_role("1.1")["status"], "PERSON_UNKNOWN")
        o = business.find_owner("who owns the telesales process"); self.assertEqual(o["resolution"]["person_status"], "PERSON_KNOWN"); self.assertEqual(o["resolution"]["person"], "Fixturo Tele")
        o = business.find_owner("who owns the retention process"); self.assertEqual(o["resolution"]["person_status"], "PERSON_UNKNOWN")
    @covers(BQ, kinds=("unit", "failure"))
    def test_restricted_data_rejected_from_core_by_schema(self):
        import bm_schema
        bad = json.loads(json.dumps(business.load()["business_model"])); bad["roles"][0]["fix_salary_net_amd"] = 5
        self.assertTrue(any("forbidden key" in x for x in bm_schema.check_shape("business_model", bad)))
        self.assertTrue(any("schema_version" in x for x in bm_schema.check_shape("kpis", {"meta": {"schema_version": "1.0"}, "kpis": [], "role_kpis": {}, "kinds": []})))

class B03_OverlayAbsent(B00):
    overlay = False
    @covers(BQ, kinds=("unit", "failure"))
    def test_unknown_person_behaviour_without_overlay(self):
        self.assertEqual(business.person_for_role("1.4")["status"], "PERSON_UNKNOWN")
        self.assertIn("name withheld", business.render("approver @P1"))
        self.assertEqual(business.compensation_for("1.1")["status"], "CONFIDENTIAL_UNAVAILABLE")
        r = executors.business_query({"query": "who owns the telesales process"}); self.assertEqual(r["status"], "EXECUTED"); self.assertEqual(r["person"], "PERSON_UNKNOWN"); self.assertIn("(1.4)", r["owner_role"])
        self.assertFalse(business.model_id()["overlay_present"])

class B04_SchemaAndStaleness(B00):
    @covers(BQ, kinds=("unit", "failure_injection"))
    def test_incompatible_schema_rejected(self):
        self.switch(schema="1.0")
        self.assertIsNone(business.load(force=True)); self.assertIn("SCHEMA_INCOMPATIBLE", business.last_error())
        r = engine.run_skill(REG, BQ, {"query": "who owns churn"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["blocked"][0]["code"], "BUSINESS_CONTEXT_MISSING")
    @covers(BQ, kinds=("unit", "failure_injection"))
    def test_source_fingerprint_change_makes_model_stale_and_fails_closed(self):
        self.assertEqual(business.model_state()["state"], "CURRENT")
        self.switch(stale_source=True)
        st = business.model_state(); self.assertEqual(st["state"], "STALE_MODEL"); self.assertEqual(st["changed"], ["S01"])
        r = executors.business_query({"query": "who owns the sales plan"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["code"], "STALE_MODEL")
        ctx = business.context_for("sales_kpi_monitoring", "why are sales down", {}, "investigate_sales_decline"); self.assertIn("STALE_MODEL", ctx["gaps"]); self.assertEqual(ctx["model"]["state"], "STALE_MODEL")
    @covers(BQ, kinds=("unit", "failure_injection"))
    def test_missing_source_detected(self):
        self.switch(missing_source=True)
        st = business.model_state(); self.assertEqual(st["state"], "SOURCE_MISSING"); self.assertEqual(st["missing"], ["S02"])
        r = executors.business_query({"query": "who owns churn"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["code"], "SOURCE_MISSING")
    @covers(BQ, kinds=("unit", "failure_injection"))
    def test_uncertified_model_fails_closed(self):
        self.switch(certified=False)
        self.assertEqual(business.model_state()["state"], "UNCERTIFIED")
        r = executors.business_query({"query": "who owns the sales plan"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["code"], "BUSINESS_CONTEXT_MISSING")
    @covers(BQ, kinds=("unit",))
    def test_answers_carry_model_identity(self):
        r = executors.business_query({"query": "who owns the sales plan"}); self.assertEqual(r["model"]["model_version"], "2026-09-10.test"); self.assertEqual(r["model"]["schema_version"], "2.0"); self.assertEqual(r["model"]["core_fingerprint"], "core-test")

class B05_TargetsAndPromotion(B00):
    @covers(BQ, kinds=("unit",))
    def test_targets_controlled_and_unknown_stays_unknown(self):
        r = executors.business_query({"query": "what kpi tells us new activations"}); k = r["kpis"][0]
        self.assertEqual(k["target"], "UNKNOWN"); self.assertEqual(k["proposed_targets"][0]["id"], "TG-P"); self.assertEqual(r["code"], "TARGET_UNKNOWN")
        d2d = business.find_kpis("d2d packages")[0]; self.assertEqual(d2d["target"], 10); self.assertEqual(d2d["target_ref"], "TG-A")
        self.assertEqual(business.targets_for("K-D2D")[0]["status"], "APPROVED")
    @covers(BQ, "decision_logging", kinds=("unit", "authority"))
    def test_promotion_rules_and_observations_never_touch_core(self):
        self.assertTrue(business.promotion_allowed("OBSERVATION", "PROPOSED", "PROPOSAL")[0])
        self.assertFalse(business.promotion_allowed("OBSERVATION", "APPROVED", "REFERENCE_APPROVED")[0])
        self.assertFalse(business.promotion_allowed("PROPOSED", "APPROVED", "EVIDENCE")[0])
        self.assertFalse(business.promotion_allowed("PROPOSED", "CONFIRMED", "EVIDENCE")[0])
        self.assertTrue(business.promotion_allowed("CONFIRMED", "APPROVED", "REFERENCE_APPROVED")[0])
        self.assertTrue(business.promotion_allowed("APPROVED", "SUPERSEDED", "REFERENCE_APPROVED")[0]); self.assertFalse(business.promotion_allowed("APPROVED", "SUPERSEDED", "EVIDENCE")[0])
        before = {f: (self.d / f"{f}.json").read_bytes() for f in business.CORE_FILES}
        rec = business.record_observation("retention owner is now the telesales senior", src=["S08"], subject="OW-4"); self.assertEqual(rec["state"], "OBSERVATION")
        self.assertEqual(business.observations()[-1]["subject"], "OW-4")
        self.assertEqual({f: (self.d / f"{f}.json").read_bytes() for f in business.CORE_FILES}, before)

class B06_Resolution(B00):
    @covers(BQ, kinds=("unit",))
    def test_owner_process_playbook_kpi_resolution_and_codes(self):
        self.assertEqual(business.find_owner("who owns the sales plan")["owner_role"], "Sales Head (1.1)")
        self.assertEqual(business.find_owner("who owns the corporate report")["code"], "OWNER_UNKNOWN"); self.assertEqual(business.find_owner("who owns the moon")["code"], "OWNER_UNKNOWN")
        c = business.find_owner("who owns churn"); self.assertEqual(c["code"], "SOURCE_CONFLICT"); self.assertEqual([x["id"] for x in c["conflicts"]], ["C01"])
        self.assertEqual(business.find_processes("which process handles a failed installation")[0]["process_id"], "P-OPS-01")
        self.assertEqual(business.playbook_for("investigate_sales_decline")["playbook_id"], "PB-01")
        self.assertEqual(executors.business_query({"query": "what kpi tells us quantum flux"})["code"], "KPI_DEFINITION_MISSING")
        self.assertEqual(executors.business_query({"query": "which process handles corporate sales"})["code"], "PROCESS_UNDEFINED")
        r = executors.business_query({"query": "who owns the corporate report"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["code"], "OWNER_UNKNOWN")

class B07_SkillIntegration(B00):
    @covers(BQ, "sales_kpi_monitoring", "decision_support", "daily_briefing", kinds=("unit", "completion"))
    def test_business_context_injected_into_governed_execution(self):
        p = engine.resolve(REG, "why are sales down?"); r = engine.run_plan(REG, p, {})
        step = next(s for s in r["steps"] if s["skill"] == "sales_kpi_monitoring"); bc = step["business_context"]
        self.assertTrue(bc["available"]); self.assertEqual(bc["playbook"], "PB-01"); self.assertIn("K-NEW", bc["kpis"]); self.assertIn("S01", bc["sources"]); self.assertIn("required_data", bc); self.assertEqual(bc["model"]["model_version"], "2026-09-10.test")
        one = engine.run_skill(REG, BQ, {"query": "who owns the sales plan"}); self.assertIn(one["status"], engine.SUCCESS_STATUSES); self.assertTrue(one["validated"]); self.assertTrue(one["verification"]["ok"])
        self.assertEqual(one["result"]["owner_role"], "Sales Head (1.1)"); self.assertEqual(one["result"]["person"], "PERSON_UNKNOWN"); self.assertEqual(one["result"]["sources"], ["S01"])
        aud = engine.audit_for_execution(one["execution_id"]); self.assertTrue(aud and aud[-1].get("business_context", {}).get("model", {}).get("core_fingerprint") == "core-test")
    @covers(BQ, *GOV, kinds=("unit", "failure", "failure_injection"))
    def test_fail_closed_when_business_model_missing(self):
        os.environ["COMMAND_CENTER_BUSINESS_DIR"] = str(pathlib.Path(tempfile.mkdtemp(prefix="nomodel_"))); business.load(force=True)
        self.assertFalse(business.available())
        r = engine.run_skill(REG, BQ, {"query": "who owns churn"}); self.assertEqual(r["status"], "BLOCKED"); self.assertEqual(r["blocked"][0]["code"], "BUSINESS_CONTEXT_MISSING")
        ctx = business.context_for("sales_kpi_monitoring", "why are sales down", {}); self.assertFalse(ctx["available"]); self.assertEqual(ctx["gaps"], ["BUSINESS_CONTEXT_MISSING"])
        rp = engine.run_plan(REG, engine.resolve(REG, "why are sales down?"), {}); self.assertNotIn(rp["status"], ("OK",)); self.assertFalse(rp["steps"][0]["business_context"]["available"])
    @covers(BQ, "authority_checking", kinds=("unit", "authority", "adversarial"))
    def test_conflict_and_approval_rule_unknown_surface_not_guess(self):
        r = engine.run_skill(REG, BQ, {"query": "who owns customer churn"}); self.assertIn(r["status"], engine.SUCCESS_STATUSES)
        self.assertEqual(r["result"]["code"], "SOURCE_CONFLICT"); self.assertEqual(r["result"]["label"], "UNKNOWN"); self.assertEqual(r["result"]["conflicts"][0]["id"], "C01")
        a = engine.authority_check(REG, REG["_index"][BQ], "EXECUTE_MATERIAL"); self.assertFalse(a["ok"])

@unittest.skipUnless((REAL / "sources.json").exists(), "real business model not built on this machine")
class B08_RealModel(unittest.TestCase):
    def setUp(self):
        os.environ.pop("COMMAND_CENTER_BUSINESS_DIR", None); os.environ.pop("COMMAND_CENTER_BUSINESS_ROOT", None); business.load(force=True)
    @covers(BQ, kinds=("unit",))
    def test_real_model_certified_current_and_gaps_present(self):
        st = business.model_state(); self.assertEqual(st["state"], "CURRENT", st); self.assertTrue(st["certified"])
        m = business.load(); self.assertGreaterEqual(len(m["gaps"]["gaps"]), 15); self.assertGreaterEqual(len(m["playbooks"]["playbooks"]), 18); self.assertGreaterEqual(len(m["business_model"]["conflicts"]), 5); self.assertGreaterEqual(len(m["targets"]["targets"]), 20)
        self.assertTrue(any(o["status"] == "OWNER_UNKNOWN" for o in m["ownership"]["ownership"]))
        self.assertTrue(all(k["target"] == "UNKNOWN" for ks in m["kpis"]["role_kpis"].values() for k in ks))
        for r in m["business_model"]["roles"]: self.assertNotIn("fix_salary_net_amd", r)
    @covers(BQ, kinds=("unit",))
    def test_rebuild_is_reproducible(self):
        import build_business_model as bb
        c1, o1, s1, _ = bb.build(); c2, o2, s2, _ = bb.build()
        self.assertEqual(c1["sources"]["meta"]["core_fingerprint"], c2["sources"]["meta"]["core_fingerprint"]); self.assertEqual(c1["sources"]["meta"]["source_snapshot_id"], c2["sources"]["meta"]["source_snapshot_id"])
        self.assertEqual(c1["sources"]["meta"]["core_fingerprint"], business.load()["sources"]["meta"]["core_fingerprint"])
        if o1: self.assertEqual(o1["meta"]["overlay_fingerprint"], o2["meta"]["overlay_fingerprint"])
    @covers(BQ, kinds=("unit", "failure"))
    def test_missing_source_fails_build_explicitly(self):
        import build_business_model as bb
        with self.assertRaises(bb.BuildError) as cm: bb.check_sources(pathlib.Path(tempfile.mkdtemp(prefix="bizsrc_")))
        self.assertEqual(cm.exception.stage, "SOURCE_MISSING"); self.assertIn("S01", cm.exception.problems)
    @covers(BQ, kinds=("unit",))
    def test_certification_gate_passes_and_covers_all_checks(self):
        import certify_business as cb
        core, ov = cb.load_built(); rec = cb.certify(core, ov)
        self.assertEqual(rec["result"], "PASS", {k: v for k, v in rec["checks"].items() if not v["pass"]})
        for name in ("schema_valid", "provenance_complete", "sensitive_boundary_clean", "no_history_contamination", "ownership_constraints", "conflicts_explicit", "unknowns_explicit", "playbook_references", "kpi_references", "process_references", "source_fingerprints_current", "no_restricted_in_core", "core_uses_person_tokens", "versioned_core_clean", "git_boundary_hooks_installed"):
            self.assertIn(name, rec["checks"]); self.assertTrue(rec["checks"][name]["pass"], name)
        self.assertEqual(rec["core_fingerprint"], business.load()["sources"]["meta"]["core_fingerprint"])
    @covers(BQ, "source_verification", kinds=("unit", "failure", "failure_injection"))
    def test_extraction_invariants_green_and_tamper_detected(self):
        import build_business_model as bb, bm_sources
        self.assertEqual(bb.invariant_checks(ROOT), [])
        self.assertEqual(set(bm_sources.EXTRACTION_INVARIANTS) & {s["source_id"] for s in bm_sources.SOURCES if s["currency"] == "CURRENT"}, {s["source_id"] for s in bm_sources.SOURCES if s["currency"] == "CURRENT"} - {"S12", "S13"})
        # tampered copy of the workspace: strategy doc replaced by an empty docx, task register truncated → invariants must fail, fingerprint alone would not
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="biztamper_"))
        for s in bm_sources.SOURCES:
            rel = W(s["path"]); src = ROOT / rel
            if src.exists(): (tmp / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src, tmp / rel)
        import docx; d = docx.Document(); d.add_paragraph("empty"); d.save(tmp / W("01_Active/Sales/Sales-strategy-2026-09-09.docx"))
        (tmp / W("01_Active/Operations/Open-questions.md")).write_text("# nothing\n", encoding="utf-8")
        probs = bb.invariant_checks(tmp)
        self.assertTrue(any(x.startswith("S03") for x in probs), probs); self.assertTrue(any(x.startswith("S10") for x in probs), probs)
        with self.assertRaises(bb.BuildError) as cm: bb.build(root=tmp)
        self.assertEqual(cm.exception.stage, "EXTRACTION_MISMATCH")
        # model missing an expected primitive → fail
        inv = {"S01": {"model_has": ["K-DOES-NOT-EXIST"]}}
        self.assertTrue(any("K-DOES-NOT-EXIST" in x for x in bb.invariant_checks(ROOT, inv)))
    @covers(BQ, "data_sensitivity_awareness", "completion_verification", kinds=("unit", "failure", "failure_injection", "completion"))
    def test_overlay_backup_encrypts_verifies_restores_and_fails_on_wrong_key(self):
        import overlay_backup as ob
        if not (shutil.which("gpg") or shutil.which("gpg2")): self.skipTest("gpg not available")
        if not ob.OVERLAY_JSON.exists(): self.skipTest("overlay absent")
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="ovbk_test_")); key = tmp / "k" / "test.key"; out = tmp / "backups"
        old = {k: os.environ.get(k) for k in ("COMMAND_CENTER_BACKUP_KEY", "COMMAND_CENTER_BACKUP_DIR")}
        os.environ["COMMAND_CENTER_BACKUP_KEY"] = str(key); os.environ["COMMAND_CENTER_BACKUP_DIR"] = str(out); importlib.reload(ob)
        try:
            arc, side, man = ob.backup()
            self.assertTrue(arc.exists() and arc.suffix == ".gpg"); self.assertNotIn(b"OVERLAY_DATA", arc.read_bytes()); self.assertNotIn(b"PERSONS", arc.read_bytes())   # ciphertext, not plaintext
            self.assertEqual(man["overlay_fingerprint"], business.load()["_overlay"]["meta"]["overlay_fingerprint"]); self.assertIn("overlay/ov_people.py", man["files"]); self.assertIn("overlay.json", man["files"])
            self.assertFalse(str(arc).startswith(str(ROOT))); self.assertFalse(str(key).startswith(str(ROOT)))          # outside the repository
            self.assertEqual(ob.verify(arc)["manifest_sha256"], man["manifest_sha256"])
            rep = ob.drill(arc); self.assertEqual(rep["result"], "PASS", rep); self.assertTrue(rep["plaintext_removed"]); self.assertTrue(rep.get("fingerprint_matches_production"))
            key.write_bytes(b"wrong-key-wrong-key-wrong-key-wrong-key\n")
            with self.assertRaises(ob.BackupError) as cm: ob.verify(arc)
            self.assertIn("decryption FAILED", str(cm.exception))
            key.unlink()
            with self.assertRaises(ob.BackupError) as cm: ob.verify(arc)
            self.assertIn("key missing", str(cm.exception))
            with self.assertRaises(ob.BackupError): ob.restore(arc, ROOT / ".claude" / "business" / "overlay")           # never into the repo without --force
        finally:
            for k, v in old.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v
            importlib.reload(ob); business.load(force=True); shutil.rmtree(tmp, ignore_errors=True)
    @covers(BQ, "churn_analysis", "backlog_management", kinds=("unit", "routing"))
    def test_real_queries(self):
        self.assertEqual(executors.business_query({"query": "Which process handles a failed installation?"})["process_id"], "P-OPS-01")
        self.assertEqual(executors.business_query({"query": "What do we do if backlog doubles?"})["playbook_id"], "PB-07")
        r = executors.business_query({"query": "Who owns customer churn?"}); self.assertEqual(r["code"], "SOURCE_CONFLICT"); self.assertEqual(r["person"], "PERSON_UNKNOWN")
        self.assertEqual(executors.business_query({"query": "Who owns the corporate monthly report?"})["code"], "OWNER_UNKNOWN")
        self.assertEqual(executors.business_query({"query": "Who should approve this discount?"})["code"], "APPROVAL_RULE_UNKNOWN")
        ctx = business.context_for("churn_analysis", "churn is up", {}, "churn_increase"); self.assertEqual(ctx["playbook"], "PB-05"); self.assertIn("SOURCE_CONFLICT", ctx["gaps"]); self.assertEqual(ctx["model"]["state"], "CURRENT")

if __name__ == "__main__":
    unittest.main(verbosity=2)
