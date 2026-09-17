# -*- coding: utf-8 -*-
"""PROJECT-CONTROLLED PYTHON RUNTIME — Command-center runs on <root>/.venv, never on whichever `python` is first on PATH.

Contract
  manifest   .claude/runtime/requirements.txt   declared dependencies (exact pins) + `# python: X.Y` + `# import-check: mod mod`
  lock       .claude/runtime/requirements.lock  full `pip freeze` of the venv (installed with --no-deps → deterministic)
  venv       <root>/.venv  (git-ignored; rebuilt from the lock on any machine)     marker: .venv/command-center-runtime.json
  launcher   .claude/runtime/hook.sh <hook.py> <event>  → runs the hook IN the venv (settings.json uses only this)

Entry points (skill.py · certify.py · build_registry.py · evals.py · validate_workspace.py · brief.py · gate.py ·
workspace_guard.py · tests/testing.py) call ensure(): if the current interpreter is not the project venv, the process is
re-executed under it (bootstrapping the venv first when missing/stale); if that is impossible → exit 2 (fail closed).

CLI   python .claude/runtime/python_runtime.py bootstrap | status | lock | hook <script> [args…]
"""
import sys, os, json, hashlib, pathlib, subprocess, shutil, re

HERE = pathlib.Path(__file__).resolve().parent                 # .claude/runtime
ROOT = HERE.parent.parent                                      # Command-center/
VENV = pathlib.Path(os.environ.get("COMMAND_CENTER_VENV") or (ROOT / ".venv"))
REQUIREMENTS = HERE / "requirements.txt"
LOCK = HERE / "requirements.lock"
MARKER = VENV / "command-center-runtime.json"
MIN_VERSION = (3, 12)
BOOTSTRAP_CMD = "python .claude/runtime/python_runtime.py bootstrap"
STATE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Monitor"}
REPAIR_RX = re.compile(r"^\s*(cd\s+(\"[^\"]*\"|'[^']*'|\S+)\s*&&\s*)?(\S*[/\\])?(py(\s+-3(\.\d+)?)?|python3?(\.exe)?)\s+\S*python_runtime\.py\s+(bootstrap|status)\s*$")   # the ONLY state command allowed while broken

def venv_python():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def _sha(p):
    try: return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError: return None

def _same(a, b):
    try: return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))
    except OSError: return False

def manifest():
    """Parse requirements.txt: pins + declared python version + import-check modules."""
    py, mods, pins = None, [], []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        m = re.match(r"#\s*python:\s*(\d+)\.(\d+)", s)
        if m: py = (int(m.group(1)), int(m.group(2))); continue
        m = re.match(r"#\s*import-check:\s*(.+)", s)
        if m: mods += m.group(1).split(); continue
        if s and not s.startswith("#"): pins.append(s)
    if not py: raise RuntimeError("requirements.txt must declare `# python: X.Y`")
    return {"python": py, "import_check": mods, "pins": pins}

def status():
    """Health of the project runtime: ok · missing · stale (manifest/lock changed) · corrupt."""
    py = venv_python(); base = {"venv": str(VENV), "python": str(py)}
    if not py.exists(): return {**base, "ok": False, "state": "missing", "detail": f"{py} not found"}
    try: m = json.loads(MARKER.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {**base, "ok": False, "state": "corrupt", "detail": f"{MARKER.name} missing/unreadable"}
    if m.get("lock_sha256") != _sha(LOCK) or m.get("requirements_sha256") != _sha(REQUIREMENTS):
        return {**base, "ok": False, "state": "stale", "detail": "requirements.txt/requirements.lock changed since the venv was built"}
    return {**base, "ok": True, "state": "ok", "base_python": m.get("base_python"), "python_version": m.get("python_version"), "built_at": m.get("built_at")}

def _candidates(want):
    c = []
    if os.name == "nt":
        py = shutil.which("py")
        if py: c += [[py, f"-{want[0]}.{want[1]}"], [py, "-3"]]
    for n in (f"python{want[0]}.{want[1]}", "python3", "python"):
        w = shutil.which(n)
        if w: c.append([w])
    return c

def _probe(cmd):
    try: out = subprocess.run(cmd + ["-c", "import sys;print(sys.executable);print(sys.version_info[0],sys.version_info[1])"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError): return None
    if out.returncode != 0: return None
    lines = out.stdout.split("\n")
    try: return lines[0].strip(), tuple(int(x) for x in lines[1].split())
    except (IndexError, ValueError): return None

def find_base(want):
    """Exact declared version first; otherwise the first interpreter ≥ MIN_VERSION (recorded in the marker)."""
    fallback = None
    for cmd in _candidates(want):
        r = _probe(cmd)
        if not r: continue
        exe, ver = r
        if ver == want: return exe, ver
        if ver >= MIN_VERSION and fallback is None: fallback = (exe, ver)
    return fallback

def bootstrap(log=print):
    """Create/repair <root>/.venv from the lock (or the manifest when no lock exists yet) and verify the imports."""
    man = manifest(); want = man["python"]
    py = venv_python()
    if MARKER.exists():
        try: cur = tuple(json.loads(MARKER.read_text(encoding="utf-8")).get("python_version") or ())
        except (OSError, ValueError): cur = ()
        if cur and cur != want and find_base(want) and find_base(want)[1] == want:
            log(f"runtime: venv is Python {cur} but manifest wants {want} → rebuilding"); shutil.rmtree(VENV, ignore_errors=True)
    if not py.exists():
        base = find_base(want)
        if not base: raise RuntimeError(f"no Python ≥ {MIN_VERSION[0]}.{MIN_VERSION[1]} found on this machine (manifest wants {want[0]}.{want[1]}); install it, then: {BOOTSTRAP_CMD}")
        exe, ver = base
        if ver != want: log(f"runtime: Python {want} not installed → building venv from {exe} ({ver[0]}.{ver[1]})")
        log(f"runtime: creating {VENV} from {exe}")
        subprocess.run([exe, "-m", "venv", "--clear", str(VENV)], check=True)
    src = LOCK if LOCK.exists() else REQUIREMENTS
    log(f"runtime: installing {src.name} into {VENV.name}")
    subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-q"] + (["--no-deps"] if src == LOCK else []) + ["-r", str(src)], check=True)
    if man["import_check"]:
        subprocess.run([str(py), "-c", "import " + ",".join(man["import_check"])], check=True)
    info = _probe([str(py)]); cfg = {}
    try:
        for line in (VENV / "pyvenv.cfg").read_text(encoding="utf-8").splitlines():
            if "=" in line: k, v = line.split("=", 1); cfg[k.strip()] = v.strip()
    except OSError: pass
    import datetime
    MARKER.write_text(json.dumps({"workspace": "Command-center", "python_version": list(info[1]) if info else None, "base_python": cfg.get("executable") or cfg.get("home"),
                                  "lock_sha256": _sha(LOCK), "requirements_sha256": _sha(REQUIREMENTS), "built_at": datetime.datetime.now().isoformat(timespec="seconds")},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    return status()

def write_lock():
    """Freeze the venv into requirements.lock (exact versions, sorted) and refresh the marker."""
    py = venv_python()
    out = subprocess.run([str(py), "-m", "pip", "freeze", "--disable-pip-version-check", "--exclude-editable"], capture_output=True, text=True, check=True).stdout
    pins = sorted(l.strip() for l in out.splitlines() if l.strip() and "==" in l)
    man = manifest()
    declared = {p.split("==")[0].lower().replace("_", "-"): p.split("==")[1] for p in man["pins"]}
    locked = {p.split("==")[0].lower().replace("_", "-"): p.split("==")[1] for p in pins}
    for name, ver in declared.items():
        if locked.get(name) != ver: raise RuntimeError(f"lock/manifest mismatch for {name}: manifest {ver} vs venv {locked.get(name)}")
    LOCK.write_text("# Command-center dependency lock — generated by `python_runtime.py lock` (pip freeze); install with --no-deps. Do not hand-edit.\n"
                    f"# python: {man['python'][0]}.{man['python'][1]}\n" + "\n".join(pins) + "\n", encoding="utf-8")
    m = json.loads(MARKER.read_text(encoding="utf-8")); m["lock_sha256"] = _sha(LOCK); m["requirements_sha256"] = _sha(REQUIREMENTS)
    MARKER.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return pins

def _fail(msg, code=2):
    sys.stderr.write(f"⛔ Command-center runtime unavailable: {msg}\n   repair: {BOOTSTRAP_CMD}\n"); sys.stderr.flush(); sys.exit(code)

def _reexec_argv(py):
    main = sys.modules.get("__main__"); spec = getattr(main, "__spec__", None)
    if spec and getattr(spec, "name", None):
        mod = spec.name[:-9] if spec.name.endswith(".__main__") else spec.name
        return [str(py), "-m", mod] + sys.argv[1:]
    a0 = sys.argv[0] if sys.argv else ""
    if a0 and a0 not in ("-c", "-") and pathlib.Path(a0).exists(): return [str(py), a0] + sys.argv[1:]
    return None

def ensure(auto_bootstrap=True):
    """Guarantee the calling process runs on the project venv with a healthy, lock-matching install.
    Inside the venv → returns (after an in-place sync if the lock changed). Outside → bootstrap if needed, re-execute
    the same command line under the venv, exit with its return code. Fail closed (exit 2) when neither is possible."""
    st = status(); py = venv_python(); inside = _same(sys.executable, py)
    if inside and st["ok"]: return
    if not st["ok"]:
        if not auto_bootstrap: _fail(f"{st['state']} — {st['detail']}")
        try: bootstrap(log=lambda m: sys.stderr.write(m + "\n"))
        except Exception as e: _fail(f"bootstrap failed ({type(e).__name__}: {e})")
        if inside: return
    argv = _reexec_argv(py)
    if not argv: _fail(f"cannot re-execute `{sys.argv[:1]}` under {py}; run it with the project interpreter")
    sys.stdout.flush(); sys.stderr.flush()
    try: rc = subprocess.call(argv)
    except OSError as e: _fail(f"{py}: {e}")
    os._exit(rc)

# ───────────────────────── hook launcher (called by hook.sh, always inside the venv when it exists) ─────────────────────────
def _degraded(event, data, st):
    """Runtime broken → fail closed without deadlocking: state tools denied except the bootstrap command itself; prompts/stop continue with a loud notice."""
    msg = f"⛔ Command-center runtime {st['state']}: {st['detail']} — hooks cannot run; state-changing tools are DENIED until repaired: {BOOTSTRAP_CMD}"
    if event == "PreToolUse":
        tool = data.get("tool_name", ""); cmd = str((data.get("tool_input") or {}).get("command", ""))
        if tool in ("Bash", "PowerShell") and REPAIR_RX.match(cmd): sys.exit(0)
        if tool in STATE_TOOLS or tool.startswith("mcp__"):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": msg}}, ensure_ascii=False))
        sys.exit(0)
    if event == "Stop":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "systemMessage": msg}}, ensure_ascii=False)); sys.exit(0)
    print(msg); sys.exit(0)

def hook(script, args):
    raw = sys.stdin.read()
    try: data = json.loads(raw) if raw.strip() else {}
    except ValueError: data = {}
    event = data.get("hook_event_name") or (args[0] if args else "")
    st = status()
    if not st["ok"] and event == "SessionStart":
        try: bootstrap(log=lambda m: print("  " + m)); st = status()
        except Exception as e: st = {**st, "detail": f"{st.get('detail')}; auto-bootstrap failed: {type(e).__name__}: {e}"}
    if not st["ok"]: _degraded(event, data, st)
    py = venv_python()
    if not _same(sys.executable, py):                      # launcher had to fall back to a PATH python → hand over to the venv
        sys.stdout.flush()
        r = subprocess.run([str(py), str(script)] + list(args), input=raw.encode("utf-8"), capture_output=True)
        sys.stdout.buffer.write(r.stdout); sys.stderr.buffer.write(r.stderr); sys.stdout.flush(); sys.stderr.flush()
        if r.returncode != 0 and event == "PreToolUse" and data.get("tool_name") in STATE_TOOLS:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": f"hook {pathlib.Path(script).name} crashed (rc={r.returncode}) — fail closed"}}))
            sys.exit(0)
        sys.exit(r.returncode)
    import io, runpy
    sys.stdin = io.TextIOWrapper(io.BytesIO(raw.encode("utf-8")), encoding="utf-8")
    sys.argv = [str(script)] + list(args)
    try: runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e: raise
    except BaseException as e:
        import traceback; traceback.print_exc()
        if event == "PreToolUse" and data.get("tool_name") in STATE_TOOLS:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": f"hook {pathlib.Path(script).name} crashed ({type(e).__name__}: {e}) — fail closed"}}, ensure_ascii=False))
            sys.exit(0)
        sys.exit(1)

def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        st = status(); st["current_interpreter"] = sys.executable; st["inside_venv"] = _same(sys.executable, venv_python())
        print(json.dumps(st, ensure_ascii=False, indent=1)); return 0 if st["ok"] else 1
    if cmd == "bootstrap":
        st = bootstrap(); print(json.dumps(st, ensure_ascii=False, indent=1)); return 0 if st["ok"] else 1
    if cmd == "lock":
        if not status()["ok"] and not venv_python().exists(): bootstrap()
        pins = write_lock(); print("\n".join(pins)); print(f"→ {LOCK} ({len(pins)} pins)"); return 0
    if cmd == "hook" and len(argv) >= 2:
        hook(argv[1], argv[2:]); return 0
    print(__doc__); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
