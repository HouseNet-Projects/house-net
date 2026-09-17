# -*- coding: utf-8 -*-
"""COMMAND-CENTER BOOTSTRAP — the one canonical recovery entry point.  GitHub + recovery key → complete Command-center.

    git clone https://github.com/HouseNet-Projects/house-net-command-center.git
    cd Command-center
    python bootstrap.py                 (or: py -3 bootstrap.py on Windows)

Idempotent and non-destructive: safe to run again at any time. Never overwrites a durable file, never resets state or ids,
never replaces credentials (existing files are kept unless --force-secrets), never prints or logs the recovery key.

Steps: 1 workspace root · 2 prerequisites (Python ≥3.11, git, Git LFS, gpg) · 3 canonical directories · 4 .venv · 5 pinned dependencies ·
6 encrypted credentials (if the recovery key is present) · 7 durable Deputy state import · 8 boundary hooks · 9 Business Model rebuild
(sources → extract → build → validate → certify) · 10 workspace + tree-manifest validation · 11 durable checksums ·
12 business certification · 13 integration certification (machine dependencies reported honestly) · 14 skill validation
(or full release with --release) · 15 readiness verdict.

Options: --release  run the full skill.py release at step 14 · --no-secrets  skip step 6 · --force-secrets  overwrite existing secret configs ·
         --key <file>  recovery key file · --json  machine-readable summary · --stage2 (internal)"""
import sys, os, json, pathlib, subprocess, shutil, datetime, platform
ROOT = pathlib.Path(__file__).resolve().parent
RUNTIME = ROOT / ".claude" / "runtime"
# Gev's business workspace: read straight from the versioned policy so stage 1 stays stdlib-only (no import of the runtime).
try: BUSINESS_ROOT_NAME = json.loads((ROOT / ".claude" / "policy" / "workspace_policy.json").read_text(encoding="utf-8")).get("business_root") or "WORKSPACE"
except Exception: BUSINESS_ROOT_NAME = "WORKSPACE"
BUSINESS_ROOT = ROOT / BUSINESS_ROOT_NAME
BUSINESS_AREAS = ("00_Inbox", "01_Active", "02_Reference", "03_Completed", "04_Sources", "05_Archive")
MIN_PY = (3, 11)

def _venv_python():
    venv = pathlib.Path(os.environ.get("COMMAND_CENTER_VENV") or (ROOT / ".venv"))      # same override python_runtime.py honours (tests share a venv)
    for c in (venv / "Scripts" / "python.exe", venv / "bin" / "python"):
        if c.exists(): return c
    return None

def _run(args, cwd=ROOT, env=None, capture=True):
    r = subprocess.run([str(a) for a in args], cwd=str(cwd), capture_output=capture, text=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")) if capture else ""

class Report:
    def __init__(self): self.steps = []; self.ok = True
    def step(self, n, name, status, detail=""):
        self.steps.append({"n": n, "step": name, "status": status, "detail": detail})
        mark = {"OK": "✓", "WARN": "△", "FAIL": "✗", "SKIP": "·"}[status]
        print(f"  {mark} {n:>2} {name}: {status}" + (f" — {detail}" if detail else ""))
        if status == "FAIL": self.ok = False

def stage1(argv, rep):
    """Stdlib-only: root, prerequisites, directories, venv. Then re-exec under the project interpreter."""
    print(f"\n══════ COMMAND-CENTER BOOTSTRAP — {ROOT} ══════")
    # 1 root
    must = [ROOT / "CLAUDE.md", ROOT / ".claude" / "policy" / "workspace_policy.json", RUNTIME / "python_runtime.py", RUNTIME / "requirements.lock"]
    missing = [str(p.relative_to(ROOT)) for p in must if not p.exists()]
    rep.step(1, "workspace root", "FAIL" if missing else "OK", f"missing {missing}" if missing else str(ROOT))
    if missing: return False
    # 2 prerequisites
    pre = []
    if sys.version_info < MIN_PY: pre.append(f"python {platform.python_version()} < {MIN_PY[0]}.{MIN_PY[1]}")
    if not shutil.which("git"): pre.append("git not on PATH")
    gpg = shutil.which("gpg") or shutil.which("gpg2")
    # Git LFS carries the binary business workspace (Office, PDF, archives). Without it a clone holds pointer files, not documents.
    lfs = shutil.which("git-lfs") or shutil.which("git-lfs.exe")
    ga = ROOT / ".gitattributes"
    lfs_required = ga.exists() and "filter=lfs" in ga.read_text(encoding="utf-8", errors="replace")
    if lfs_required and not lfs:
        pre.append("git-lfs not on PATH - this repository stores its Office/PDF/archive business files in Git LFS. "
                   "Install Git LFS from https://git-lfs.com, then run: git lfs install && git lfs pull")
    elif lfs_required:
        ptr = []
        for area in BUSINESS_AREAS[1:]:
            for f in (BUSINESS_ROOT / area).rglob("*"):
                if f.is_file() and f.suffix.lower() in (".docx", ".xlsx", ".xlsm", ".pptx", ".pdf", ".zip", ".7z", ".bundle"):
                    try:
                        if f.stat().st_size < 400 and f.read_bytes()[:24].startswith(b"version https://git-lfs"): ptr.append(str(f.relative_to(ROOT)))
                    except OSError: pass
        if ptr: pre.append("Git LFS objects are not downloaded (%d pointer file(s), e.g. %s) - run: git lfs pull" % (len(ptr), ptr[0]))
    # Windows MAX_PATH: the archive namespace carries long original filenames, so a clone placed deep in the filesystem can fail
    # checkout with "Filename too long". Verified real: a clone under a deeply nested temp path lost two files this way.
    if platform.system() == "Windows":
        rc_lp, out_lp = _run(["git", "config", "--get", "core.longpaths"])
        if (out_lp or "").strip().lower() != "true":
            longest = 0
            for area in ("05_Archive",):
                for f in (BUSINESS_ROOT / area).rglob("*"):
                    longest = max(longest, len(str(f)))
            if longest > 200:
                rep.step(2, "windows long paths", "WARN",
                         "longest path is %d characters and core.longpaths is off - if a clone ever fails with 'Filename too long', "
                         "run: git config --global core.longpaths true" % longest)
    rep.step(2, "prerequisites", "FAIL" if pre else ("OK" if gpg else "WARN"), ("; ".join(pre)) if pre else (f"python {platform.python_version()}, git, git-lfs={'yes' if lfs else 'not required'}, gpg={'yes' if gpg else 'NO (encrypted credentials cannot be restored)'}"))
    if pre: return False
    # 3 canonical directories (from the policy-derived manifest; stdlib read of the versioned manifest)
    man = json.loads((ROOT / ".claude" / "policy" / "workspace_tree_manifest.json").read_text(encoding="utf-8"))
    created = []
    for e in man["entries"]:
        if e["kind"] == "directory" and e["required"] and e["path"] not in (".git",):
            p = ROOT / e["path"]
            if not p.is_dir(): p.mkdir(parents=True, exist_ok=True); created.append(e["path"])
    for extra in (".claude/state", ".claude/audit"):
        (ROOT / extra).mkdir(parents=True, exist_ok=True)
    mirror = ROOT / ".claude" / "audit" / "skill_audit.jsonl"                       # ephemeral append-only audit mirror the policy expects to exist
    if not mirror.exists(): mirror.write_text("", encoding="utf-8"); created.append(".claude/audit/skill_audit.jsonl")
    rep.step(3, "canonical directories", "OK", f"created {created}" if created else "all present")
    # 4/5 venv + pinned dependencies (python_runtime bootstrap is idempotent)
    py = _venv_python()
    rc, out = _run([sys.executable, RUNTIME / "python_runtime.py", "bootstrap"])
    py = _venv_python()
    try: st = json.loads(out[out.index("{"):]) if "{" in out else {}
    except ValueError: st = {}
    rep.step(4, ".venv", "FAIL" if (rc != 0 or not py) else "OK", (f"{py} (python {'.'.join(map(str, st.get('python_version') or []))}, lock {str(st.get('lock_sha256', ''))[:12]})" if py else out.strip()[-200:]))
    if rc != 0 or not py: return False
    rc, out = _run([py, "-c", "import openpyxl, docx; print('deps ok')"])
    rep.step(5, "pinned dependencies", "FAIL" if rc != 0 else "OK", "requirements.lock installed" if rc == 0 else out[-200:])
    return rc == 0

def stage2(argv, rep, opts):
    sys.path.insert(0, str(RUNTIME)); sys.path.insert(0, str(ROOT / ".claude" / "policy")); sys.path.insert(0, str(ROOT / ".claude" / "skills")); sys.path.insert(0, str(ROOT / ".claude" / "integrations"))
    py = sys.executable
    # 6 encrypted credentials
    if opts["no_secrets"]: rep.step(6, "encrypted credentials", "SKIP", "--no-secrets")
    else:
        import secure_recovery as sr
        if opts["key"]: os.environ["COMMAND_CENTER_RECOVERY_KEY_FILE"] = opts["key"]
        if not (ROOT / ".secure" / "credentials.gpg").exists(): rep.step(6, "encrypted credentials", "WARN", "no .secure/credentials.gpg in the repository")
        elif not sr.key_file().exists(): rep.step(6, "encrypted credentials", "WARN", f"recovery key not present ({sr.key_file()}) — secret configs NOT restored; integrations needing them stay NOT_CONFIGURED")
        else:
            try: r = sr.restore(force=opts["force_secrets"], log=lambda *a: None); rep.step(6, "encrypted credentials", "OK", f"restored {len(r['restored'])}, kept {len(r['kept'])} → {r['home']}")
            except sr.RecoveryError as e: rep.step(6, "encrypted credentials", "FAIL", str(e))
    # 7 durable state import
    try:
        import state_snapshot as ss
        r = ss.import_(log=lambda *a: None); rep.step(7, "durable Deputy state", "OK", "; ".join(f"{k}: {v}" for k, v in r.items()))
    except Exception as e: rep.step(7, "durable Deputy state", "FAIL", f"{type(e).__name__}: {e}")
    # 8 boundary hooks
    try:
        import sensitive_scan; rep.step(8, "git boundary hooks", "OK" if sensitive_scan.install_hooks() else "WARN", "pre-commit + pre-push installed" if (ROOT / ".git").exists() else "no .git")
    except Exception as e: rep.step(8, "git boundary hooks", "WARN", str(e))
    # 9 business model rebuild (sources → extract → build → validate → certify); missing source = hard failure, never silent
    rc, out = _run([py, ROOT / ".claude" / "business" / "build_business_model.py"])
    tail = [l for l in out.strip().splitlines() if l.strip()][-1:] or ["?"]
    rep.step(9, "business model rebuild", "OK" if rc == 0 else "FAIL", tail[0][:180])
    # 10 workspace + tree manifest
    rc, out = _run([py, ROOT / ".claude" / "policy" / "validate_workspace.py", "--json"])
    try: vprobs = json.loads(out[out.index("{"):]).get("problems", [])
    except (ValueError, IndexError): vprobs = [out.strip()[-300:] or f"validator rc={rc}"]
    rep.step(10, "workspace validation", "OK" if rc == 0 else "FAIL", "contract + tree manifest satisfied" if rc == 0 else " | ".join(vprobs)[:600])
    import tree_manifest as tm
    miss = tm.verify(ROOT)
    if miss: rep.step(10, "tree manifest verify", "FAIL", f"missing {miss}")
    # 11 checksums
    cs = tm.verify_checksums(ROOT)
    rep.step(11, "durable checksums", "OK" if not (cs["changed"] or cs["missing"]) else "WARN", f"verified {len(cs['verified'])}, changed {len(cs['changed'])}, missing {len(cs['missing'])}, new {len(cs['new'])}" + (f" — changed: {cs['changed'][:5]}" if cs["changed"] else ""))
    # 12 business certification
    rc, out = _run([py, ROOT / ".claude" / "business" / "certify_business.py"])
    rep.step(12, "business certification", "OK" if rc == 0 else "FAIL", (out.strip().splitlines() or ["?"])[0][:180])
    # 13 integration certification (honest machine dependencies)
    rc, out = _run([py, ROOT / ".claude" / "integrations" / "certify_integrations.py"])
    lines = [l.strip() for l in out.strip().splitlines() if l.strip().startswith("INT-")]
    rep.step(13, "integration certification", "OK" if rc == 0 else "FAIL", " | ".join(l.split("evidence")[0].strip() for l in lines)[:300])
    try:
        import registry, layer
        for s in layer.status():
            spec = registry.get(s["integration_id"]); dep = spec.get("machine_dependency")
            needs = bool(spec["auth"].get("secrets")); sec = ("PRESENT" if s["configured"] else "ABSENT → NOT_CONFIGURED") if needs else "not needed"
            print(f"       {s['integration_id']}: code restored · safe config restored · secret config {sec}" + (f" · machine dependency: {dep}" if dep else "") + f" · status {s['certification']}/{s['health']}")
    except Exception as e: print(f"       integration status unavailable: {e}")
    # 14 skill validation / release
    if opts["release"]:
        rc, out = _run([py, ROOT / ".claude" / "skills" / "skill.py", "release"])
        rep.step(14, "skill release", "OK" if rc == 0 else "FAIL", ([l for l in out.splitlines() if l.startswith("RELEASE") or l.startswith("EVALS:")] or ["?"])[-1][:160])
    else:
        rc, out = _run([py, ROOT / ".claude" / "skills" / "skill.py", "validate"])
        rep.step(14, "skill validation", "OK" if rc == 0 else "FAIL", (out.strip().splitlines() or ["?"])[-1][:160])
    # 15 verdict
    verdict = "READY" if rep.ok else "NOT READY"
    rep.step(15, "readiness", "OK" if rep.ok else "FAIL", verdict)
    summary = {"root": str(ROOT), "at": datetime.datetime.now().isoformat(timespec="seconds"), "verdict": verdict, "steps": rep.steps}
    (ROOT / ".claude" / "state" / "bootstrap_last.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    if opts["json"]: print(json.dumps(summary, ensure_ascii=False))
    print(f"══════ BOOTSTRAP {verdict} ══════\n")
    return rep.ok

def main(argv):
    opts = {"release": "--release" in argv, "no_secrets": "--no-secrets" in argv, "force_secrets": "--force-secrets" in argv, "json": "--json" in argv, "key": argv[argv.index("--key") + 1] if "--key" in argv else None}
    rep = Report()
    if "--stage2" not in argv:
        if not stage1(argv, rep): print("══════ BOOTSTRAP NOT READY (stage 1) ══════"); return 1
        py = _venv_python()
        if pathlib.Path(sys.executable).resolve() != py.resolve():
            return subprocess.call([str(py), str(ROOT / "bootstrap.py"), "--stage2"] + [a for a in argv if a != "--stage2"], cwd=str(ROOT))
        rep2 = rep
    else:
        rep2 = rep
    return 0 if stage2(argv, rep2, opts) else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
