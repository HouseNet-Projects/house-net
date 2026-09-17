# -*- coding: utf-8 -*-
"""RUNTIME suite — the project-controlled Python runtime (.claude/runtime + <root>/.venv) is deterministic and fail-closed:
  · every suite/hook/CLI runs on <root>/.venv (exact declared Python), never on the PATH interpreter
  · requirements.lock pins every declared dependency; the declared import-check modules import
  · the hook launcher (hook.sh) works with NO python on PATH and ignores a broken PATH python
  · a missing/broken venv fails closed without deadlock: state tools denied, repair command allowed, prompts/stop continue
State for hook runs lives in a temp SKILL_STATE_DIR; production state is never touched."""
import unittest, json, os, sys, subprocess, pathlib, tempfile, shutil, stat
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "runtime"))
from testing import covers
import python_runtime as rt

GOV = ("authority_checking", "approval_management", "completion_verification", "audit_logging")
HOOK_SH = ROOT / ".claude" / "runtime" / "hook.sh"
GATE = ROOT / ".claude" / "hooks" / "gate.py"
BASH = shutil.which("bash")

def decision(out):
    for line in out.splitlines():
        if line.startswith("{"):
            try: return json.loads(line).get("hookSpecificOutput", {})
            except json.JSONDecodeError: pass
    return {}

def launch(env, event, payload, script="gate.py"):
    d = {"hook_event_name": event, "session_id": "rt-test", "cwd": str(ROOT), **payload}
    return subprocess.run([BASH, str(HOOK_SH), script, event], input=json.dumps(d), capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(ROOT))

class R01_ProjectInterpreter(unittest.TestCase):
    @covers(*GOV, kinds=("enforcement",))
    def test_suite_runs_on_project_venv_with_declared_python(self):
        st = rt.status(); self.assertTrue(st["ok"], st)
        self.assertTrue(rt._same(sys.executable, rt.venv_python()), f"{sys.executable} is not the project interpreter {rt.venv_python()}")
        self.assertEqual(tuple(sys.version_info[:2]), tuple(rt.manifest()["python"]))
        self.assertEqual(tuple(st["python_version"]), tuple(rt.manifest()["python"]))
    @covers(*GOV, kinds=("enforcement",))
    def test_lock_pins_every_declared_dependency_and_imports_work(self):
        man = rt.manifest(); lock = [l.strip() for l in rt.LOCK.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
        self.assertTrue(lock and all("==" in l for l in lock), lock)
        locked = {l.split("==")[0].lower().replace("_", "-"): l.split("==")[1] for l in lock}
        for pin in man["pins"]:
            n, v = pin.split("=="); self.assertEqual(locked.get(n.lower().replace("_", "-")), v, pin)
        for mod in man["import_check"]: __import__(mod)
        self.assertIn(f"# python: {man['python'][0]}.{man['python'][1]}", rt.LOCK.read_text(encoding="utf-8"))
    @covers(*GOV, kinds=("enforcement",))
    def test_venv_is_not_versioned_and_settings_use_the_launcher(self):
        self.assertIn(".venv/", (ROOT / ".gitignore").read_text(encoding="utf-8"))
        if shutil.which("git"): self.assertEqual(subprocess.run(["git", "check-ignore", "-q", ".venv"], cwd=str(ROOT)).returncode, 0, ".venv must be git-ignored")
        cfg = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for grp in cfg["hooks"].values() for g in grp for h in g["hooks"]]
        self.assertEqual(len(cmds), 7); self.assertTrue(all(".claude/runtime/hook.sh" in c for c in cmds), cmds)
        self.assertFalse(any(c.lstrip().startswith("python") for c in cmds), "hooks must not start with the PATH python")

@unittest.skipUnless(BASH, "bash launcher not available on this machine")
class R02_LauncherIndependentOfPath(unittest.TestCase):
    def _env(self, fake_python_rc=None):
        bin_ = pathlib.Path(tempfile.mkdtemp(prefix="rt_bin_"))
        if fake_python_rc is not None:
            for n in ("python", "python3"):
                p = bin_ / n; p.write_text(f"#!/bin/sh\necho FAKE PYTHON USED >&2\nexit {fake_python_rc}\n", encoding="utf-8"); p.chmod(p.stat().st_mode | stat.S_IEXEC)
        env = {k: v for k, v in os.environ.items() if k.upper() not in ("PATH", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CLAUDE_PROJECT_DIR")}
        env["PATH"] = str(bin_); env["SKILL_STATE_DIR"] = tempfile.mkdtemp(prefix="rt_state_"); env["CLAUDE_PROJECT_DIR"] = str(ROOT)
        return env
    @covers(*GOV, kinds=("enforcement", "failure_injection"))
    def test_hooks_run_with_no_python_and_no_git_on_path(self):
        env = self._env()                                            # PATH = one empty dir
        r = launch(env, "PreToolUse", {"tool_name": "Read", "tool_input": {"file_path": "x"}})
        self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(decision(r.stdout), {})
        r = launch(env, "PreToolUse", {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "01_Active" / "Sales" / "X.md"), "content": "x"}})
        self.assertEqual(decision(r.stdout).get("permissionDecision"), "deny", r.stdout + r.stderr)      # real gate, real verdict (no ticket)
        r = launch(env, "PreToolUse", {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "Stray-file.txt"), "content": "x"}}, script="workspace_guard.py")
        self.assertIn("WORKSPACE POLICY", decision(r.stdout).get("permissionDecisionReason", ""), r.stdout + r.stderr)
    @covers(*GOV, kinds=("enforcement", "failure_injection"))
    def test_broken_path_python_does_not_change_behaviour(self):
        env = self._env(fake_python_rc=99)                           # PATH python is a bomb; the launcher must never use it
        r = launch(env, "UserPromptSubmit", {"user_prompt": "remind me friday to call arman"})
        self.assertEqual(r.returncode, 0, r.stderr); self.assertNotIn("FAKE PYTHON", r.stderr); self.assertIn("SKILL GATE", r.stdout); self.assertIn("commitment_tracking", r.stdout)
        r = launch(env, "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "echo x > out.txt"}})
        self.assertNotIn("FAKE PYTHON", r.stderr); self.assertEqual(decision(r.stdout).get("permissionDecision"), "deny")
        r = launch(env, "Stop", {"stop_hook_active": False}); self.assertEqual(r.returncode, 0, r.stderr)
        r = launch(env, "SessionStart", {"source": "startup"}, script="brief.py"); self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("DAILY BRIEF", r.stdout)

class R03_FailClosedWhenRuntimeBroken(unittest.TestCase):
    def _run(self, event, payload):
        env = {**os.environ, "COMMAND_CENTER_VENV": str(pathlib.Path(tempfile.mkdtemp(prefix="rt_novenv_")) / "missing"), "SKILL_STATE_DIR": tempfile.mkdtemp(prefix="rt_state_")}
        d = {"hook_event_name": event, "session_id": "rt-broken", **payload}
        return subprocess.run([sys.executable, str(rt.__file__), "hook", str(GATE), event], input=json.dumps(d), capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(ROOT))
    @covers(*GOV, kinds=("enforcement", "failure_injection"))
    def test_state_tools_denied_repair_allowed_prompt_and_stop_continue(self):
        r = self._run("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "echo x > out.txt"}})
        self.assertEqual(r.returncode, 0, r.stderr); d = decision(r.stdout); self.assertEqual(d.get("permissionDecision"), "deny"); self.assertIn("bootstrap", d.get("permissionDecisionReason", ""))
        r = self._run("PreToolUse", {"tool_name": "Write", "tool_input": {"file_path": "C:/tmp/x.md", "content": "x"}}); self.assertEqual(decision(r.stdout).get("permissionDecision"), "deny")
        r = self._run("PreToolUse", {"tool_name": "Read", "tool_input": {"file_path": "x"}}); self.assertEqual(decision(r.stdout), {})
        r = self._run("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "python .claude/runtime/python_runtime.py bootstrap"}}); self.assertEqual(decision(r.stdout), {}, r.stdout)   # the repair itself
        r = self._run("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "cd C:/x && py -3.13 .claude/runtime/python_runtime.py bootstrap"}}); self.assertEqual(decision(r.stdout), {}, r.stdout)
        r = self._run("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "rm -rf .claude && python .claude/runtime/python_runtime.py bootstrap"}}); self.assertEqual(decision(r.stdout).get("permissionDecision"), "deny")
        r = self._run("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "python .claude/runtime/python_runtime.py bootstrap; rm -rf .claude"}}); self.assertEqual(decision(r.stdout).get("permissionDecision"), "deny")
        r = self._run("UserPromptSubmit", {"user_prompt": "hi"}); self.assertEqual(r.returncode, 0); self.assertIn("runtime missing", r.stdout)
        r = self._run("Stop", {"stop_hook_active": False}); self.assertEqual(r.returncode, 0); self.assertIn("runtime missing", r.stdout)
    @covers(*GOV, kinds=("enforcement", "failure_injection"))
    def test_entry_point_outside_venv_fails_closed_without_bootstrap(self):
        env = {**os.environ, "COMMAND_CENTER_VENV": str(pathlib.Path(tempfile.mkdtemp(prefix="rt_novenv_")) / "missing")}
        code = f"import sys; sys.path.insert(0, {str(ROOT / '.claude' / 'runtime')!r}); import python_runtime as rt; rt.ensure(auto_bootstrap=False)"
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 2); self.assertIn("runtime unavailable", r.stderr); self.assertIn("bootstrap", r.stderr)

if __name__ == "__main__":
    unittest.main(verbosity=2)
