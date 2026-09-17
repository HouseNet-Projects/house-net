# -*- coding: utf-8 -*-
"""HARD SCOPE LOCK suite — Deputy changes ONLY what Gev's current instruction requires.

Everything here drives the REAL machinery: the policy section (workspace_policy.json -> scope_lock), the real scope engine
(.claude/policy/scope.py), the real ticket owner (engine.set_scope) and the real PreToolUse hook (.claude/hooks/gate.py),
plus the real git scope-diff gate in a throwaway repository. Production state is never touched (SKILL_STATE_DIR).

Proven:
  · Gev asks for a Telegram fix        → unrelated workspace cleanup is DENIED
  · Gev asks for a folder reorganization → integration code mutation is DENIED
  · an unrelated bug found on the way   → report only; touching it is DENIED
  · one out-of-scope path                → commit/push gate HARD FAIL
  · scope extension                      → only with a NEW explicit instruction from Gev
  · Deputy widening its own scope        → mechanically REFUSED
  · necessary in-scope implementation    → allowed, no per-file approval
  · no contract at all                   → DEFAULT DENY
"""
import unittest, json, os, sys, pathlib, tempfile, subprocess, copy
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "policy")); sys.path.insert(0, str(ROOT / ".claude" / "skills"))
import scope, validate_workspace as vw
from testing import covers

GATE = ROOT / ".claude" / "hooks" / "gate.py"
SKILL = ROOT / ".claude" / "skills" / "skill.py"
POLICY = json.loads((ROOT / ".claude" / "policy" / "workspace_policy.json").read_text(encoding="utf-8"))
GOV = ("authority_checking", "approval_management", "audit_logging")

TELEGRAM_ASK = "Telegram-ի UX-ը ուղղիր — the telegram adapter shows the raw id instead of the username."
FOLDER_ASK = "Reorganize the workspace folders: move the business documents into the right areas of the taxonomy."
CLEANUP_ASK = "Do a full cleanup of the workspace folders and archive the old sources."


class Harness:
    """A ticket + scope contract in an isolated state dir, driven exactly like the harness drives the hook."""

    def __init__(self, prompt):
        self.state = pathlib.Path(tempfile.mkdtemp(prefix="scope_"))
        self.env = {**os.environ, "SKILL_STATE_DIR": str(self.state)}
        self.session = "scope-" + self.state.name[-6:]
        self.hook("UserPromptSubmit", user_prompt=prompt)

    def hook(self, ev, **payload):
        d = {"hook_event_name": ev, "session_id": self.session, "cwd": str(ROOT), **payload}
        p = subprocess.run([sys.executable, str(GATE), ev], input=json.dumps(d), capture_output=True, text=True,
                           encoding="utf-8", env=self.env, cwd=str(ROOT))
        dec = None
        for line in p.stdout.splitlines():
            if line.startswith("{"):
                try: dec = json.loads(line).get("hookSpecificOutput", {})
                except json.JSONDecodeError: pass
        return {"rc": p.returncode, "out": p.stdout, "err": p.stderr,
                "decision": (dec or {}).get("permissionDecision"), "reason": (dec or {}).get("permissionDecisionReason", "")}

    def cli(self, *args):
        p = subprocess.run([sys.executable, str(SKILL), *args], capture_output=True, text=True, encoding="utf-8",
                           env=self.env, cwd=str(ROOT))
        return p.returncode, p.stdout + p.stderr

    def ticket(self):
        rc, o = self.cli("ticket", "current")
        return json.loads(o) if o.strip().startswith("{") else None

    def tid(self):
        return self.ticket()["ticket_id"]

    def declare(self, reason="workspace housekeeping with no matching skill"):
        return self.cli("declare", "--ticket", self.tid(), reason)

    def set_scope(self, outcome, *subs, extend=False):
        rc, o = self.cli("scope", "extend" if extend else "set", "--ticket", self.tid(), "--outcome", outcome, *subs)
        return rc, json.loads(o) if o.strip().startswith("{") else {"raw": o}

    def write(self, rel, content="x"):
        return self.hook("PreToolUse", tool_name="Write", tool_input={"file_path": str(ROOT / rel), "content": content})


class ScopeAssertions:
    """The scope lock is ONE of several boundaries (skill routing, maintenance grants, the approval law all still apply).
    So 'in scope' is proven by the absence of a SCOPE denial, not by the absence of every denial."""

    def assertInScope(self, r, rel=""):
        self.assertNotIn("OUT_OF_SCOPE", r["reason"], f"{rel}: scope blocked work Gev did ask for — {r['reason']}")

    def assertOutOfScope(self, r, rel=""):
        self.assertEqual(r["decision"], "deny", rel)
        self.assertIn("OUT_OF_SCOPE", r["reason"], rel)


class S01_SubsystemMap(unittest.TestCase):
    """Every mutable surface has exactly one declared owner, and the map is the policy's, not the code's."""

    @covers(*GOV, kinds=("unit",))
    def test_every_business_and_technical_surface_maps_to_a_subsystem(self):
        for rel, expected in (("WORKSPACE/01_Active/Sales/Sales-plan-2026-09-10.docx", "business_workspace"),
                              ("WORKSPACE/Tasks.xlsx", "task_register"),
                              ("WORKSPACE/Journal.md", "journal_and_actions"),
                              (".claude/skills/engine.py", "skill_system"),
                              (".claude/hooks/gate.py", "enforcement_hooks"),
                              (".claude/policy/workspace_policy.json", "workspace_policy"),
                              (".claude/tests/test_scope.py", "tests"),
                              (".claude/integrations/adapter_telegram.py", "integrations"),
                              (".claude/business/bm_kpis.py", "business_model"),
                              ("bootstrap.py", "runtime"),
                              ("CLAUDE.md", "agent_docs"),
                              (".gitattributes", "git_config")):
            self.assertIn(expected, scope.subsystems_for(rel), rel)

    @covers(*GOV, kinds=("unit",))
    def test_runtime_byproducts_are_never_a_scope_decision(self):
        for rel in (".claude/state/skill_state.db", ".claude/audit/skill_audit.jsonl"):
            self.assertTrue(scope.always_allowed(rel), rel)

    @covers(*GOV, kinds=("unit", "failure"))
    def test_an_unmapped_path_fails_closed(self):
        c = scope.confirm(scope.new_contract("t", CLEANUP_ASK), "reorganize the workspace folders", ["business_workspace"])["contract"]
        ok, why = scope.in_scope("something/unknown.txt", c)
        self.assertFalse(ok); self.assertIn("no declared subsystem", why)


class S02_DefaultDeny(unittest.TestCase):
    """Nothing is in scope until Gev's ask has been stated back and recorded."""

    @covers(*GOV, kinds=("unit", "failure", "enforcement"))
    def test_without_a_confirmed_contract_every_mutation_is_denied(self):
        c = scope.new_contract("t", FOLDER_ASK)
        self.assertEqual(c["status"], "DERIVED")
        self.assertEqual(c["allowed_subsystems"], [])
        for rel in ("WORKSPACE/01_Active/Sales/X.docx", ".claude/skills/engine.py", "CLAUDE.md"):
            ok, why = scope.in_scope(rel, c)
            self.assertFalse(ok, rel); self.assertIn("default DENY", why)

    @covers(*GOV, kinds=("enforcement", "failure"))
    def test_the_real_hook_denies_a_write_with_no_contract(self):
        h = Harness(FOLDER_ASK); h.declare()
        r = h.write("WORKSPACE/01_Active/Sales/Whatever-2026-09-14.docx")
        self.assertEqual(r["decision"], "deny")
        self.assertIn("OUT_OF_SCOPE", r["reason"])

    @covers(*GOV, kinds=("unit",))
    def test_a_ticket_carries_a_scope_contract_from_the_moment_it_is_opened(self):
        h = Harness(TELEGRAM_ASK)
        sc = h.ticket()["scope"]
        self.assertEqual(sc["status"], "DERIVED")
        self.assertEqual(sc["task_id"], h.tid())
        self.assertIn("integrations", sc["evidence_subsystems"])
        for field in ("requested_outcome", "allowed_subsystems", "allowed_paths", "allowed_operations", "out_of_scope", "task_id", "provenance"):
            self.assertIn(field, sc, field)


class S03_TheTwoRequiredCases(unittest.TestCase, ScopeAssertions):
    """The two cases Gev named: a Telegram fix must not become a workspace cleanup, and a folder move must not
    become an integration change."""

    @covers(*GOV, kinds=("enforcement", "failure", "adversarial"))
    def test_a_telegram_fix_cannot_become_a_workspace_cleanup(self):
        h = Harness(TELEGRAM_ASK); h.declare()
        rc, r = h.set_scope("fix how the Telegram adapter labels a sender", "integrations")
        self.assertEqual(rc, 0, r); self.assertEqual(r["status"], "CONFIRMED")
        self.assertInScope(h.write(".claude/integrations/adapter_telegram.py"), "adapter_telegram.py")
        for rel in ("WORKSPACE/01_Active/Sales/Tidy-2026-09-14.docx", "WORKSPACE/05_Archive/Old-2026-09-14.md", "WORKSPACE/Journal.md"):
            self.assertOutOfScope(h.write(rel), rel)

    @covers(*GOV, kinds=("enforcement", "failure", "adversarial"))
    def test_a_folder_reorganization_cannot_mutate_integration_code(self):
        h = Harness(FOLDER_ASK); h.declare()
        rc, r = h.set_scope("move the business documents into the right areas", "business_workspace")
        self.assertEqual(rc, 0, r)
        self.assertInScope(h.write("WORKSPACE/02_Reference/Sales/Moved-plan-2026-09-14.md"))
        for rel in (".claude/integrations/adapter_telegram.py", ".claude/integrations/registry.py"):
            self.assertOutOfScope(h.write(rel), rel)


class S04_ReportOnly(unittest.TestCase):
    """Something noticed on the way is reported, never fixed on Deputy's own authority."""

    @covers(*GOV, kinds=("enforcement", "failure"))
    def test_an_unrelated_bug_found_during_the_task_is_report_only(self):
        h = Harness(FOLDER_ASK); h.declare()
        h.set_scope("move the business documents into the right areas", "business_workspace")
        # Deputy notices a real defect in an unrelated subsystem while moving files
        d = h.write(".claude/skills/intelligence.py")
        self.assertEqual(d["decision"], "deny")
        self.assertIn("OUT_OF_SCOPE", d["reason"])
        self.assertIn("outside this task's scope", d["reason"])
        # the finding itself is not suppressed: reporting it needs no permission at all (a read is never gated)
        r = h.hook("PreToolUse", tool_name="Read", tool_input={"file_path": str(ROOT / ".claude/skills/intelligence.py")})
        self.assertIsNone(r["decision"])

    @covers(*GOV, kinds=("unit", "failure"))
    def test_report_only_categories_are_named_in_the_policy(self):
        rep = " ".join(POLICY["scope_lock"]["report_only"]).lower()
        for needle in ("unrelated bug", "security hardening", "architecturally better", "nice to clean up"):
            self.assertIn(needle, rep, needle)
        self.assertIn("STOPS the work", POLICY["scope_lock"]["dependency_rule"])


class S05_NoSelfExtension(unittest.TestCase, ScopeAssertions):
    """The contract may only be widened by GEV. Deputy restating its own wish is not evidence."""

    @covers(*GOV, kinds=("adversarial", "failure", "enforcement"))
    def test_deputy_cannot_widen_its_own_scope(self):
        h = Harness(TELEGRAM_ASK); h.declare()
        h.set_scope("fix how the Telegram adapter labels a sender", "integrations")
        for wish in ("business_workspace", "skill_system", "workspace_policy"):
            rc, r = h.set_scope("while I am here I will also tidy this up", wish)
            self.assertEqual(rc, 2, (wish, r))
            self.assertEqual(r["status"], "REFUSED")
            self.assertEqual(r["code"], "OUT_OF_SCOPE")
            self.assertIn("no evidence", r["reason"])
        self.assertEqual(h.ticket()["scope"]["allowed_subsystems"], ["integrations"])

    @covers(*GOV, kinds=("adversarial", "failure"))
    def test_an_extension_without_a_new_instruction_is_refused(self):
        h = Harness(TELEGRAM_ASK); h.declare()
        h.set_scope("fix how the Telegram adapter labels a sender", "integrations")
        rc, r = h.set_scope("also clean the folders", "business_workspace", extend=True)
        self.assertEqual(rc, 2); self.assertEqual(r["code"], "OUT_OF_SCOPE")

    @covers(*GOV, kinds=("unit", "enforcement"))
    def test_scope_extends_only_on_a_new_explicit_instruction_from_gev(self):
        h = Harness(TELEGRAM_ASK); h.declare()
        h.set_scope("fix how the Telegram adapter labels a sender", "integrations")
        self.assertOutOfScope(h.write("WORKSPACE/01_Active/Sales/X-2026-09-14.docx"))
        # Gev now says it himself — a NEW message carrying his own words. The task's contract is inherited, so the ask is an
        # EXTENSION of the same task, and it is granted only because HIS new message supplies the evidence.
        h.hook("UserPromptSubmit", user_prompt="Also reorganize the workspace folders while you are at it.")
        inherited = h.ticket()["scope"]
        self.assertEqual(inherited["status"], "CONFIRMED"); self.assertEqual(inherited["allowed_subsystems"], ["integrations"])
        rc, r = h.set_scope("reorganize the workspace folders as Gev just asked", "business_workspace", extend=True)
        self.assertEqual(rc, 0, r)
        self.assertEqual(sorted(r["scope"]["allowed_subsystems"]), ["business_workspace", "integrations"])
        self.assertInScope(h.write("WORKSPACE/01_Active/Sales/X-2026-09-14.docx"))

    @covers(*GOV, kinds=("unit", "failure"))
    def test_an_unknown_subsystem_is_refused(self):
        h = Harness(FOLDER_ASK); h.declare()
        rc, r = h.set_scope("move the business documents", "everything")
        self.assertEqual(rc, 2); self.assertEqual(r["code"], "UNKNOWN_SUBSYSTEM")

    @covers(*GOV, kinds=("unit", "failure"))
    def test_a_contract_needs_a_real_stated_outcome(self):
        h = Harness(FOLDER_ASK); h.declare()
        rc, r = h.set_scope("ok", "business_workspace")
        self.assertEqual(rc, 2); self.assertEqual(r["code"], "NO_OUTCOME")


class S06_ImplementationDetail(unittest.TestCase, ScopeAssertions):
    """Inside an allowed subsystem, ordinary work does not turn into an approval stream."""

    @covers(*GOV, kinds=("unit", "enforcement"))
    def test_every_necessary_file_inside_an_allowed_subsystem_is_allowed(self):
        h = Harness("Fix the skill engine: the resolver and its executors need a change, plus the registry.")
        h.declare()
        rc, r = h.set_scope("fix the resolver in the skill system", "skill_system")
        self.assertEqual(rc, 0, r)
        for rel in (".claude/skills/intelligence.py", ".claude/skills/documents.py", ".claude/skills/people.py",
                    ".claude/skills/actions.py", ".claude/skills/routines.py"):
            self.assertInScope(h.write(rel), rel)

    @covers(*GOV, kinds=("unit",))
    def test_the_policy_states_the_per_subsystem_rule(self):
        self.assertIn("per subsystem, not per file", POLICY["scope_lock"]["implementation_detail"])


class S07_GitGate(unittest.TestCase):
    """One out-of-scope path = HARD FAIL: no commit, no push, no PR."""

    def _repo(self, h):
        d = pathlib.Path(tempfile.mkdtemp(prefix="scopegit_"))
        for cmd in (["init", "-q"], ["config", "user.email", "t@example.invalid"], ["config", "user.name", "t"]):
            subprocess.run(["git"] + cmd, cwd=str(d), capture_output=True, text=True)
        (d / ".claude" / "integrations").mkdir(parents=True); (d / "WORKSPACE" / "01_Active" / "Sales").mkdir(parents=True)
        (d / ".claude" / "integrations" / "adapter_telegram.py").write_text("# x\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(d), capture_output=True)
        subprocess.run(["git", "commit", "-qm", "base", "--no-verify"], cwd=str(d), capture_output=True)
        return d

    def _gate(self, repo, env, mode="--staged"):
        p = subprocess.run([sys.executable, str(ROOT / ".claude" / "policy" / "scope.py"), mode, "--root", str(repo)],
                           capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(ROOT))
        return p.returncode, p.stdout + p.stderr

    @covers(*GOV, kinds=("enforcement", "failure", "completion"))
    def test_an_out_of_scope_staged_change_hard_fails_the_gate(self):
        h = Harness(TELEGRAM_ASK); h.declare()
        h.set_scope("fix how the Telegram adapter labels a sender", "integrations")
        repo = self._repo(h)
        (repo / ".claude" / "integrations" / "adapter_telegram.py").write_text("# fixed\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
        rc, out = self._gate(repo, h.env)
        self.assertEqual(rc, 0, out)                                     # in scope → the commit may proceed
        (repo / "WORKSPACE" / "01_Active" / "Sales" / "Tidy-2026-09-14.md").write_text("tidy\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
        rc, out = self._gate(repo, h.env)
        self.assertEqual(rc, 1, out)                                     # one out-of-scope path → HARD FAIL
        self.assertIn("OUT_OF_SCOPE", out)
        self.assertIn("WORKSPACE/01_Active/Sales/Tidy-2026-09-14.md", out)
        self.assertIn("No commit, no push, no PR", out)

    @covers(*GOV, kinds=("enforcement", "failure"))
    def test_the_gate_refuses_when_there_is_no_contract(self):
        h = Harness(TELEGRAM_ASK); h.declare()
        repo = self._repo(h)
        (repo / ".claude" / "integrations" / "adapter_telegram.py").write_text("# fixed\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
        rc, out = self._gate(repo, h.env)
        self.assertEqual(rc, 2, out); self.assertIn("OUT_OF_SCOPE", out); self.assertIn("no confirmed Scope Contract", out)

    @covers(*GOV, kinds=("unit", "enforcement"))
    def test_the_precommit_hook_runs_the_boundary_scan_and_then_the_scope_gate(self):
        import sensitive_scan as ss
        body = ss.HOOK_PRE_COMMIT
        self.assertIn("sensitive_scan.py", body); self.assertIn("scope.py", body)
        self.assertLess(body.index("sensitive_scan.py"), body.index("scope.py"), "the credential boundary decides first")
        self.assertIn("--staged", body)
        installed = ROOT / ".git" / "hooks" / "pre-commit"
        if installed.exists():
            self.assertEqual(installed.read_text(encoding="utf-8"), body, "the installed hook drifted from the versioned one")
        self.assertTrue(ss.hooks_installed(ROOT) or not (ROOT / ".git").is_dir())


class S08_ActionRuntime(unittest.TestCase):
    """An external system outside the contract never even reaches an approval card."""

    @covers(*GOV, kinds=("unit", "failure", "authority"))
    def test_an_external_system_outside_the_contract_is_out_of_scope(self):
        import engine
        t = {"scope": scope.confirm(scope.new_contract("t", TELEGRAM_ASK),
                                    "fix the telegram adapter label", ["integrations"])["contract"]}
        ok, why = engine.scope_allows_system(t, "INT-TG")
        self.assertTrue(ok, why)
        ok, why = engine.scope_allows_system(t, "INT-TASKS")
        self.assertFalse(ok); self.assertIn("task_register", why)

    @covers(*GOV, kinds=("unit",))
    def test_the_approval_law_is_untouched_by_scope(self):
        """Scope narrows what may be proposed; it never grants a mutation."""
        ar = json.loads((ROOT / ".claude" / "policy" / "approval_rule.json").read_text(encoding="utf-8"))
        self.assertEqual(ar["autonomous_external_write_authority"], "NONE")
        self.assertIn("never grants a mutation", POLICY["scope_lock"]["relation_to_approval_rule"])
        blob = json.dumps(POLICY["scope_lock"], ensure_ascii=False).lower()
        for forbidden in ("autonomous", "bypass approval", "without gev"):
            self.assertNotIn(forbidden, blob, forbidden)


class S09_PolicyFailsClosed(unittest.TestCase):
    """An unenforceable scope rule is the same as no scope rule."""

    @covers(*GOV, kinds=("unit", "failure", "failure_injection"))
    def test_a_hollowed_out_scope_section_is_a_policy_violation(self):
        for mutate, needle in (
            (lambda p: p["scope_lock"].clear(), "scope_lock"),
            (lambda p: p["scope_lock"].update(default="ALLOW"), "default"),
            (lambda p: p["scope_lock"].update(law="Deputy does what it likes"), "law"),
            (lambda p: p["scope_lock"].update(self_extension="Deputy may extend when useful"), "self_extension"),
            (lambda p: p["scope_lock"].update(subsystems={}), "subsystems"),
            (lambda p: p["scope_lock"]["enforcement"].pop("git_gate"), "git_gate"),
        ):
            p2 = copy.deepcopy(POLICY); mutate(p2)
            self.assertTrue(any(needle in x for x in vw.validate_scope_policy(p2)), needle)

    @covers(*GOV, kinds=("unit", "failure"))
    def test_the_section_is_mandatory(self):
        p2 = copy.deepcopy(POLICY); del p2["scope_lock"]
        self.assertTrue(any("scope_lock" in x for x in vw.validate_policy(p2)))

    @covers(*GOV, kinds=("unit", "failure"))
    def test_the_named_machinery_must_actually_exist(self):
        self.assertEqual(vw.check_scope(ROOT, POLICY), [])
        p2 = copy.deepcopy(POLICY)
        p2["scope_lock"]["enforcement_files"] = [".claude/policy/nonexistent_scope.py"]
        self.assertTrue(any("nonexistent_scope.py" in x for x in vw.check_scope(ROOT, p2)))
        p3 = copy.deepcopy(POLICY)
        p3["scope_lock"]["mirror_files"] = {"CLAUDE.md": ["A RULE NOBODY WROTE DOWN"]}
        self.assertTrue(any("CLAUDE.md" in x for x in vw.check_scope(ROOT, p3)))

    @covers(*GOV, kinds=("unit",))
    def test_claude_md_mirrors_the_rule_for_the_agent(self):
        txt = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("HARD SCOPE LOCK", txt)
        self.assertIn("REPORT ONLY", txt)
        self.assertIn("scope set", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
