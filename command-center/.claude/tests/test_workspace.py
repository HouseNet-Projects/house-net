# -*- coding: utf-8 -*-
"""Workspace contract tests — drive the REAL validator (.claude/policy/validate_workspace.py) and the REAL guard hook
(.claude/hooks/workspace_guard.py) against synthetic trees built from the canonical policy. Nothing touches the live workspace."""
import unittest, json, pathlib, tempfile, shutil, subprocess, sys, os, copy
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
POLICY_DIR = ROOT / ".claude" / "policy"
sys.path.insert(0, str(POLICY_DIR)); sys.path.insert(0, str(HERE))
import validate_workspace as vw, paths
from testing import covers

POLICY = json.loads((POLICY_DIR / "workspace_policy.json").read_text(encoding="utf-8"))
GUARD = ROOT / ".claude" / "hooks" / "workspace_guard.py"

def contract_line(pol=None):
    """Everything a mirrored file must state to satisfy the policy — identity tokens AND the interaction contract.
    Derived from the policy, never hard-coded, so a new mandated mention cannot silently bypass the synthetic trees."""
    pol = pol or POLICY
    toks = {t for ts in pol["identity_enforcement"]["must_mention"].values() for t in ts}
    toks |= {t for ts in (pol.get("interaction", {}).get("enforcement", {}).get("mirror_files") or {}).values() for t in ts}
    toks |= {t for ts in (pol.get("scope_lock", {}).get("mirror_files") or {}).values() for t in ts}
    return " ".join(sorted(toks)) + "\n"

def readme_body(pol=None):
    """Everything README.md must mention: the required roots AND Gev's business areas and registers."""
    pol = pol or POLICY; br = pol["business_root"]; wc = pol["directories"][br]
    return "\n".join(pol["root"]["required_dirs"] + pol["root"]["required_files"] +
                      [f"{br}/{x}" for x in wc.get("fixed_subdirs", []) + wc.get("allowed_files", [])]) + "\n"


def W(rel):
    """Repository-relative path of a business-relative one (WORKSPACE/... )."""
    return paths.to_repo(rel, POLICY)


def clean_tree():
    """Minimal tree that satisfies the contract (files are empty placeholders)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="ws_")); pol = POLICY
    ident_line = contract_line(pol)
    for f in pol["root"]["required_files"]: (d / f).write_text("# x\n" + ident_line, encoding="utf-8")
    (d / "README.md").write_text(readme_body(pol) + ident_line, encoding="utf-8")
    for dd in pol["root"]["required_dirs"]: (d / dd).mkdir(parents=True, exist_ok=True)
    for area, dc in pol["directories"].items():
        base = d / area; base.mkdir(parents=True, exist_ok=True)
        for sub in dc.get("fixed_subdirs", []): (base / sub).mkdir(exist_ok=True)
        for rf in dc.get("required_files", []): (base / rf).write_text(ident_line if rf.endswith(".md") else "", encoding="utf-8")
    (d / W("00_Inbox/Input.md")).parent.mkdir(parents=True, exist_ok=True)
    (d / W("00_Inbox/Input.md")).write_text("# inbox\n", encoding="utf-8")
    for reg in POLICY["directories"][POLICY["business_root"]].get("allowed_files", []):
        f = d / W(reg)
        if not f.exists(): f.write_bytes(b"")
    # Mission 4.1: the policy-derived tree manifest is part of the contract — every required path must physically exist
    import tree_manifest as tm
    for e in tm.build(pol)["entries"]:
        if not e["required"] or e["path"] == ".git": continue
        tp = d / e["path"]
        if e["kind"] == "directory": tp.mkdir(parents=True, exist_ok=True)
        elif not tp.exists():
            tp.parent.mkdir(parents=True, exist_ok=True)
            tp.write_text("{}" if tp.suffix == ".json" else (ident_line if tp.suffix == ".md" else ""), encoding="utf-8")
    (d / ".claude" / "policy" / "workspace_tree_manifest.json").write_text(json.dumps(tm.build(pol)), encoding="utf-8")
    (d / ".claude" / "audit").mkdir(parents=True, exist_ok=True); (d / ".claude" / "audit" / "skill_audit.jsonl").write_text("", encoding="utf-8")
    return d

def problems(d): return vw.validate_tree(d, POLICY)

class W01_Tree(unittest.TestCase):
    @covers("source_verification", kinds=("unit",))
    def test_valid_clean_tree_passes(self):
        d = clean_tree(); self.assertEqual(problems(d), [])
        (d / W("01_Active/Sales/Sales-strategy-v1.1-2026-09-10.docx")).write_bytes(b""); (d / W("02_Reference/People/Staffing-plan-2026-09-07.xlsx")).write_bytes(b"")
        (d / W("04_Sources/Whatsapp/Principal-2026-09-09")).mkdir(); (d / W("04_Sources/Whatsapp/Principal-2026-09-09/chat.txt")).write_text("", encoding="utf-8")
        (d / W("05_Archive/Drafts-2026-09-09")).mkdir(); (d / W("05_Archive/Drafts-2026-09-09/run.py")).write_text("", encoding="utf-8")
        self.assertEqual(problems(d), [])
    def test_unknown_root_file_fails(self):
        d = clean_tree(); (d / "Notes.md").write_text("", encoding="utf-8"); self.assertTrue(any("unknown top-level file" in p for p in problems(d)))
    def test_unknown_root_folder_fails(self):
        d = clean_tree(); (d / "06_Misc").mkdir(); self.assertTrue(any("unknown top-level directory" in p for p in problems(d)))
    def test_armenian_business_filename_fails(self):
        d = clean_tree(); (d / W("01_Active/Sales/Ռազմավարություն-2026-09-10.docx")).write_bytes(b""); self.assertTrue(any("forbidden pattern" in p for p in problems(d)))
    def test_spaces_fail(self):
        d = clean_tree(); (d / W("01_Active/Sales/Sales strategy.docx")).write_bytes(b""); self.assertTrue(any("Sales strategy.docx" in p for p in problems(d)))
    def test_parenthesized_duplicate_fails(self):
        d = clean_tree(); (d / W("01_Active/Sales/Save-list (2).xlsx")).write_bytes(b""); self.assertTrue(any("(2)" in p or "forbidden pattern" in p for p in problems(d)))
    def test_final2_fails(self):
        d = clean_tree(); (d / W("01_Active/Sales/Sales-strategy-final2.docx")).write_bytes(b""); self.assertTrue(any("forbidden word" in p for p in problems(d)))
    def test_wrong_date_format_fails(self):
        d = clean_tree(); (d / W("01_Active/Sales/Sales-strategy-10.09.2026.docx")).write_bytes(b""); self.assertTrue(any("Sales-strategy-10.09.2026" in p for p in problems(d)))
        (d / W("01_Active/Sales/Sales-strategy-2026_09_10.docx")).write_bytes(b""); self.assertTrue(any("2026_09_10" in p for p in problems(d)))
    def test_wrong_version_format_fails(self):
        d = clean_tree(); (d / W("01_Active/Systems/Billing-roadmap-v2.0.1-2026-09-07.docx")).write_bytes(b""); self.assertTrue(any("v2.0.1" in p for p in problems(d)))
        (d / W("01_Active/Systems/Billing-roadmap-2026-09-07-v2.docx")).write_bytes(b""); self.assertTrue(any("version must come before date" in p for p in problems(d)))
    def test_wrong_extension_placement_fails(self):
        d = clean_tree(); (d / W("01_Active/Sales/Sales-strategy.DOCX")).write_bytes(b""); self.assertTrue(any("Sales-strategy.DOCX" in p for p in problems(d)))
        (d / W("02_Reference/Sales/Sales-plan-2026-09-10.py")).write_text("", encoding="utf-8"); self.assertTrue(any("Sales-plan-2026-09-10.py" in p for p in problems(d)))
    def test_raw_whatsapp_source_in_active_fails(self):
        d = clean_tree(); (d / W("01_Active/Operations/chat.txt")).write_text("", encoding="utf-8"); (d / W("01_Active/Sales/Principal.zip")).write_bytes(b"")
        pr = problems(d); self.assertTrue(any("chat.txt" in p and "04_Sources" in p for p in pr)); self.assertTrue(any("Principal.zip" in p for p in pr))
    def test_python_tool_inside_sources_fails(self):
        d = clean_tree(); (d / W("04_Sources/Imports/helper.py")).write_text("", encoding="utf-8"); self.assertTrue(any("helper.py" in p for p in problems(d)))
    def test_test_file_inside_skills_fails(self):
        d = clean_tree(); (d / ".claude/skills/test_engine.py").write_text("", encoding="utf-8"); self.assertTrue(any("test_engine.py" in p for p in problems(d)))
    def test_audit_log_inside_skills_fails(self):
        d = clean_tree(); (d / ".claude/skills/skill_audit.jsonl").write_text("", encoding="utf-8"); self.assertTrue(any("skill_audit.jsonl" in p and ".claude/skills" in p for p in problems(d)))
        (d / ".claude/skills/state").mkdir(); self.assertTrue(any(".claude/skills/state" in p for p in problems(d)))
    def test_missing_required_canonical_root_file_fails(self):
        d = clean_tree(); (d / W("Tasks.xlsx")).unlink(); self.assertTrue(any(f"missing canonical file {W('Tasks.xlsx')}" in p for p in problems(d)))
    def test_duplicate_canonical_task_register_fails(self):
        d = clean_tree(); (d / W("01_Active/Operations/Tasks.xlsx")).write_bytes(b""); self.assertTrue(any(f"duplicate canonical artifact for {W('Tasks.xlsx')}" in p for p in problems(d)))
        (d / W("03_Completed/Tasks-copy-2026-09-10.xlsx")).write_bytes(b""); self.assertTrue(any("Tasks-copy" in p for p in problems(d)))
    def test_technical_reserved_filenames_allowed(self):
        d = clean_tree()
        for f in ("CLAUDE.md", "README.md", ".gitignore", ".gitattributes", "desktop.ini"): (d / f).write_text(contract_line() if f != "README.md" else (d / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
        (d / ".claude/settings.json").write_text("{}", encoding="utf-8"); self.assertEqual(problems(d), [])
    def test_python_module_naming_exception_works(self):
        d = clean_tree(); (d / ".claude/tools/build_task_workbook.py").write_text("", encoding="utf-8"); self.assertEqual(problems(d), [])
        (d / ".claude/tools/Build-Task-Workbook.py").write_text("", encoding="utf-8"); self.assertTrue(any("snake_case" in p for p in problems(d)))
    def test_inbox_invariant(self):
        d = clean_tree(); (d / W("00_Inbox/random.docx")).write_bytes(b""); self.assertTrue(any("00_Inbox not in steady state" in p for p in problems(d)))
        (d / W("00_Inbox/random.docx")).unlink(); (d / W("00_Inbox/sub")).mkdir(); self.assertTrue(any("subdirectories are forbidden in 00_Inbox" in p for p in problems(d)))
    def test_reference_and_completed_semantics(self):
        d = clean_tree(); (d / W("02_Reference/People/Staffing-plan-2026-09-07.xlsx")).write_bytes(b""); (d / W("03_Completed/Staffing-plan-2026-09-07.xlsx")).write_bytes(b"")
        self.assertTrue(any(f"both {W('02_Reference')} and {W('03_Completed')}" in p for p in problems(d)))
        (d / W("02_Reference/Sales/Sales-plan-draft2.docx")).write_bytes(b""); self.assertTrue(any("draft2" in p for p in problems(d)))
    def test_arbitrary_subdirs_forbidden_in_active_and_reference(self):
        d = clean_tree(); (d / W("01_Active/Sales/Misc")).mkdir(); self.assertTrue(any("arbitrary subdirectories" in p for p in problems(d)))
        (d / W("02_Reference/Marketing")).mkdir(); self.assertTrue(any("only fixed subdomains" in p for p in problems(d)))
    def test_pycache_and_garbage(self):
        d = clean_tree(); (d / W("01_Active/__pycache__")).mkdir(); self.assertTrue(any("__pycache__ outside" in p for p in problems(d)))
        (d / W("03_Completed/Report-2026-09-10.tmp")).write_bytes(b""); self.assertTrue(any("garbage" in p for p in problems(d)))
    def test_broken_link_detected(self):
        d = clean_tree(); (d / W("Journal.md")).write_text("see [x](" + W("01_Active/Sales/Nope.docx") + ")\n", encoding="utf-8"); self.assertTrue(any("broken link" in p for p in problems(d)))
    def test_readme_policy_consistency(self):
        d = clean_tree(); (d / "README.md").write_text("nothing\n", encoding="utf-8"); self.assertTrue(any("README.md does not mention" in p for p in problems(d)))
    def test_policy_corruption_fails_closed(self):
        bad = pathlib.Path(tempfile.mkdtemp()) / "workspace_policy.json"; bad.write_text("{not json", encoding="utf-8")
        with self.assertRaises(vw.PolicyError): vw.load_policy(bad)
        self.assertTrue(any("POLICY" in p for p in vw.validate_tree(clean_tree(), None, bad)))
        p2 = copy.deepcopy(POLICY); p2["root"]["unknown_entries"] = "allow"; self.assertTrue(vw.validate_policy(p2))
        p3 = copy.deepcopy(POLICY); p3["naming"]["business_filename_regex"] = "(["; self.assertTrue(vw.validate_policy(p3))
        rc = subprocess.run([sys.executable, str(POLICY_DIR / "validate_workspace.py"), "--policy", str(bad), "--root", str(clean_tree())], capture_output=True).returncode
        self.assertEqual(rc, 2)
    def test_cli_exit_codes(self):
        d = clean_tree()
        self.assertEqual(subprocess.run([sys.executable, str(POLICY_DIR / "validate_workspace.py"), "--root", str(d), "--quiet"]).returncode, 0)
        (d / "Junk.txt").write_text("", encoding="utf-8")
        self.assertEqual(subprocess.run([sys.executable, str(POLICY_DIR / "validate_workspace.py"), "--root", str(d), "--quiet"]).returncode, 1)

class W03_Identity(unittest.TestCase):
    def test_policy_is_the_single_identity_source(self):
        ident = POLICY["identity"]
        self.assertEqual(ident["name"], "Deputy"); self.assertEqual(ident["workspace"], "Command-center"); self.assertEqual(ident["workspace"], POLICY["workspace_name"])
        self.assertEqual(ident["owner"], "Gev"); self.assertIn("Chief of Staff", ident["role"])
        sys.path.insert(0, str(ROOT / ".claude" / "skills")); import engine
        self.assertEqual(engine.identity()["name"], "Deputy")
    def test_identity_drift_fails(self):
        d = clean_tree(); (d / "CLAUDE.md").write_text("Deputy · Command-center\ncanonical agent = Assistant\n", encoding="utf-8")
        self.assertTrue(any("stale canonical reference" in p and "CLAUDE.md" in p for p in problems(d)))
        (d / "README.md").write_text((d / "README.md").read_text(encoding="utf-8") + "\nworkspace = Sales-operations-control\n", encoding="utf-8")
        self.assertTrue(any("Sales-operations-control" in p for p in problems(d)))
        (d / "README.md").write_text(readme_body() + "\nagent Deputy in Command-center\n", encoding="utf-8")
        (d / "CLAUDE.md").write_text("Deputy · Command-center\nformerly: Daily check (historical)\n", encoding="utf-8")   # historical marker → allowed
        for f in (".claude/docs/Role.md", ".claude/docs/Job-description.md"): (d / f).write_text("Deputy\n", encoding="utf-8")
        self.assertEqual([p for p in problems(d) if "stale" in p or "must mention" in p], [])
    def test_missing_identity_mention_fails(self):
        d = clean_tree(); (d / "CLAUDE.md").write_text("no names here\n", encoding="utf-8")
        self.assertTrue(any("must mention canonical identity 'Deputy'" in p for p in problems(d)))
    def test_policy_without_identity_fails_closed(self):
        p2 = copy.deepcopy(POLICY); del p2["identity"]
        self.assertTrue(any("identity" in p for p in vw.check_identity(clean_tree(), p2)))

class W02_Guard(unittest.TestCase):
    def guard(self, ev, tool, inp, root):
        d = {"hook_event_name": ev, "session_id": "ws-test", "tool_name": tool, "tool_input": inp, "cwd": str(root)}
        p = subprocess.run([sys.executable, str(GUARD), ev], input=json.dumps(d), capture_output=True, text=True, encoding="utf-8", env={**os.environ, "WORKSPACE_ROOT": str(root)})
        dec = None
        for line in p.stdout.splitlines():
            if line.startswith("{"): dec = json.loads(line).get("hookSpecificOutput", {})
        return (dec or {}).get("permissionDecision"), (dec or {}).get("permissionDecisionReason", ""), p.stdout
    def test_guard_uses_canonical_policy_not_a_duplicate_ruleset(self):
        src = GUARD.read_text(encoding="utf-8")
        self.assertIn("validate_workspace", src); self.assertIn("check_path", src)
        self.assertNotIn("forbidden_words = [", src); self.assertNotIn("business_filename_regex\"", src.replace("pol[\"naming\"]", ""))
    def test_guard_denies_invalid_write_targets(self):
        d = clean_tree()
        for path in (W("01_Active/Sales/Sales strategy final2.docx"), "Notes.md", W("04_Sources/Imports/helper.py"), ".claude/skills/test_x.py", W("01_Active/Sales/Ռազմ.docx")):
            dec, why, _ = self.guard("PreToolUse", "Write", {"file_path": str(d / path), "content": "x"}, d); self.assertEqual(dec, "deny", path)
    def test_guard_allows_valid_business_and_technical_targets(self):
        d = clean_tree()
        for path in (W("01_Active/Sales/Sales-strategy-v1.1-2026-09-10.docx"), W("Journal.md"), ".claude/tools/build_task_workbook.py", W("02_Reference/People/Staffing-plan-2026-09-07.xlsx"), W("00_Inbox/Input.md")):
            dec, why, _ = self.guard("PreToolUse", "Write", {"file_path": str(d / path), "content": "x"}, d); self.assertIsNone(dec, (path, why))
    def test_guard_bash_move_targets(self):
        d = clean_tree()
        dec, why, _ = self.guard("PreToolUse", "Bash", {"command": f'mv "{d}/{W("Journal.md")}" "{d}/{W("01_Active/Sales/journal copy (2).md")}"'}, d); self.assertEqual(dec, "deny")
        dec, why, _ = self.guard("PreToolUse", "Bash", {"command": f'mv "{d}/{W("Journal.md")}" "{d}/{W("05_Archive/Journal-2026-09-10.md")}"'}, d); self.assertIsNone(dec, why)
        dec, why, _ = self.guard("PreToolUse", "Bash", {"command": f'mkdir "{d}/06_New"'}, d); self.assertEqual(dec, "deny")
    def test_guard_post_mutation_validates_and_flags(self):
        d = clean_tree(); (d / "Junk.txt").write_text("", encoding="utf-8")
        dec, why, out = self.guard("PostToolUse", "Bash", {"command": "echo x"}, d)
        self.assertIn("WORKSPACE VIOLATION", out)
    def test_guard_fails_closed_on_corrupt_policy(self):
        d = clean_tree(); bad = pathlib.Path(tempfile.mkdtemp()) / "workspace_policy.json"; bad.write_text("{", encoding="utf-8")
        p = subprocess.run([sys.executable, str(GUARD), "PreToolUse"], input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": str(d / W("Journal.md"))}}),
                           capture_output=True, text=True, encoding="utf-8", env={**os.environ, "WORKSPACE_ROOT": str(d), "WORKSPACE_POLICY": str(bad)})
        self.assertIn('"deny"', p.stdout)

class W04_Interaction(unittest.TestCase):
    """THE INTERACTION CONTRACT — Deputy speaks to Gev in Eastern Armenian and presents people in human-readable form.
    It lives in the SAME policy owner as identity (no second policy system), it fails closed, and the runtime re-asserts it on
    every prompt instead of relying on the agent remembering it."""
    @classmethod
    def setUpClass(cls):
        for d in ("skills", "hooks"): sys.path.insert(0, str(ROOT / ".claude" / d))
        import engine, gate; cls.engine, cls.gate = engine, gate

    def test_a_human_label_is_enough_for_ordinary_work(self):
        """A label is not a mapping: for ordinary read/intelligence/reporting the provider label is sufficient to keep working."""
        hri = POLICY["interaction"]["human_readable_identity"]
        self.assertIn("@username", hri["label_rule"]); self.assertIn("NOT a blocker", hri["never_block"])
        ops = hri["confirmation_required_only_for"]
        self.assertTrue(isinstance(ops, dict) and ops)
        for need in ("OWNERSHIP", "AUTHORITY", "ROLE_BINDING"): self.assertIn(need, ops, need)
        for k in ("label_rule", "never_block", "confirmation_required_only_for"):
            p2 = copy.deepcopy(POLICY); del p2["interaction"]["human_readable_identity"][k]
            self.assertTrue(any(k in x for x in vw.check_interaction(clean_tree(), p2)), k)

    def test_the_no_blocker_guarantee_cannot_be_removed(self):
        p2 = copy.deepcopy(POLICY); p2["interaction"]["human_readable_identity"]["never_block"] = "ask Gev whenever unsure"
        self.assertTrue(any("never_block" in x for x in vw.check_interaction(clean_tree(), p2)))
        p3 = copy.deepcopy(POLICY); p3["interaction"]["human_readable_identity"]["confirmation_required_only_for"] = {}
        self.assertTrue(any("confirmation_required_only_for" in x for x in vw.check_interaction(clean_tree(), p3)))

    def test_runtime_tells_the_agent_to_continue_rather_than_ask(self):
        line = self.gate.interaction_line(self.engine)
        self.assertIn("ՇԱՐՈՒՆԱԿԻՐ", line); self.assertIn("blocker չէ", line)
        for op in ("OWNERSHIP", "AUTHORITY"): self.assertIn(op, line, op)

    def test_policy_is_the_single_interaction_source(self):
        ix = POLICY["interaction"]
        self.assertEqual(ix["user_language"], "hy-AM")
        self.assertIn("Eastern Armenian", ix["rule"])
        for k in ("approval cards", "error and blocker explanations", "user-visible reasoning summaries", "status updates"):
            self.assertIn(k, ix["applies_to"], k)
        self.assertEqual(self.engine.interaction()["user_language"], "hy-AM")

    def test_policy_without_interaction_fails_closed(self):
        p2 = copy.deepcopy(POLICY); del p2["interaction"]
        self.assertTrue(any("interaction section missing" in x for x in vw.check_interaction(clean_tree(), p2)))
        p3 = copy.deepcopy(POLICY); del p3["interaction"]["enforcement"]
        self.assertTrue(any("enforcement missing" in x for x in vw.check_interaction(clean_tree(), p3)))

    def test_language_downgrade_is_a_violation(self):
        for bad in ("en", "ru", "", None):
            p2 = copy.deepcopy(POLICY); p2["interaction"]["user_language"] = bad
            self.assertTrue(any("user_language" in x for x in vw.check_interaction(clean_tree(), p2)), bad)
        p3 = copy.deepcopy(POLICY); p3["interaction"]["rule"] = ""
        self.assertTrue(any("interaction.rule missing" in x for x in vw.check_interaction(clean_tree(), p3)))

    def test_human_readable_identity_rule_cannot_be_hollowed_out(self):
        p2 = copy.deepcopy(POLICY); del p2["interaction"]["human_readable_identity"]
        self.assertTrue(any("human_readable_identity" in x for x in vw.check_interaction(clean_tree(), p2)))
        for k in ("absent_field_rule", "order"):
            p3 = copy.deepcopy(POLICY); p3["interaction"]["human_readable_identity"][k] = ""
            self.assertTrue(any(k in x for x in vw.check_interaction(clean_tree(), p3)), k)

    def test_presentation_rule_may_never_become_an_identity_confirmation_rule(self):
        self.assertIn("NOT confirmed identity", POLICY["interaction"]["human_readable_identity"]["safety"])
        p2 = copy.deepcopy(POLICY); p2["interaction"]["human_readable_identity"]["safety"] = "a display name is good enough"
        self.assertTrue(any("OUT of confirmed identity" in x for x in vw.check_interaction(clean_tree(), p2)))

    def test_mirror_docs_must_state_the_contract(self):
        d = clean_tree()
        (d / "CLAUDE.md").write_text("Deputy · Command-center\n", encoding="utf-8")
        self.assertTrue(any("CLAUDE.md" in x and "interaction contract" in x for x in vw.check_interaction(d, POLICY)))
        self.assertEqual(vw.check_interaction(ROOT, POLICY), [])

    def test_runtime_reasserts_the_contract_on_every_prompt(self):
        """Enforced by the runtime, not by memory: the gate injects the contract into the context of EVERY prompt."""
        line = self.gate.interaction_line(self.engine)
        for needle in ("ԱՐԵՎԵԼԱՀԱՅԵՐԵՆ", "hy-AM", "blocker", "հաստատման քարտ", "ՉԵՍ փոխում", "ինքնության հաստատում ՉԷ"):
            self.assertIn(needle, line, needle)
        self.assertIn("interaction_line(engine)", (ROOT / ".claude/hooks/gate.py").read_text(encoding="utf-8"))

    def test_contract_does_not_weaken_authority_or_security(self):
        """A UX rule must never become a permission: it grants nothing and moves no approval/authority boundary."""
        blob = json.dumps(POLICY["interaction"], ensure_ascii=False).lower()
        for forbidden in ("autonomous", "bypass", "credential", "token", "without gev"):
            self.assertNotIn(forbidden, blob, forbidden)
        self.assertTrue(POLICY.get("authority"))
        ar = json.loads((ROOT / ".claude/policy/approval_rule.json").read_text(encoding="utf-8"))
        self.assertEqual(ar["autonomous_external_write_authority"], "NONE")
        self.assertEqual(vw.check_identity(ROOT, POLICY), [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
