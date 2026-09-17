# -*- coding: utf-8 -*-
"""LIVE DATA SYNC — the lightweight durability path for LIVE OPERATIONAL DATA and durable runtime state (policy durability.live_data):
WORKSPACE/Tasks.xlsx · WORKSPACE/Journal.md · WORKSPACE/00_Inbox/Input.md · business documents that are not model extraction sources · .claude/state/durable/* ·
.claude/policy/durable_checksums.json. Reuses the existing primitives (tree_manifest checksums/classification, state_snapshot export,
business.model_state, certify_business) — no second integrity system.

    python .claude/skills/skill.py sync [--dry-run] [--no-push]        (sanctioned entry point; this module is what it runs)

Steps (fail closed at the first problem):
  1 CLASSIFY   git working tree + stored checksums → CLEAN · SYNC_REQUIRED · RELEASE_REQUIRED · UNCLASSIFIED (tree_manifest.classify_drift)
               RELEASE_REQUIRED / UNCLASSIFIED → refused: product/model/unknown changes only travel through skill.py release
  2 STATIC OK  the certified business model must still be CURRENT (business.model_state) and certify_business must still PASS
               without a rebuild — a LIVE register row change never touches it; a schema/model-source change is RELEASE_REQUIRED
  3 EXPORT     durable Deputy state (actions, audit, commitments, decisions, observations) → .claude/state/durable/*.jsonl —
               refused (DURABLE_REGRESSION) when the local store holds fewer rows than the versioned files (import first)
  4 CHECKSUMS  durable_checksums.json refreshed; the refresh may only touch sync classes (otherwise refused)
  5 COMMIT     only the classified sync paths are staged and committed (git identity required; never --no-verify)
  6 PUSH       to the upstream of the current branch, then HEAD == upstream is verified (unless --no-push)
Nothing here is a business mutation: the approved mutation already happened through the Action Runtime; sync persists its evidence."""
import sys, os, json, pathlib, subprocess, datetime
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / ".claude" / "policy")); sys.path.insert(0, str(ROOT / ".claude" / "business")); sys.path.insert(0, str(ROOT / ".claude" / "skills"))

class SyncError(Exception):
    def __init__(self, code, detail): super().__init__(f"{code}: {detail}"); self.code = code; self.detail = detail

def _git(args, root, check=True):
    r = subprocess.run(["git"] + [str(a) for a in args], cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0: raise SyncError("GIT", f"git {' '.join(map(str, args))}: {(r.stderr or r.stdout).strip()[:400]}")
    return r.stdout

def model_source_paths():
    """Paths of CONTENT-scoped (extracted) business-model sources: a change there is a MODEL change (release), never live data."""
    try:
        import bm_sources, paths
        return [paths.to_repo(s["path"]) for s in bm_sources.SOURCES if s["currency"] == "CURRENT" and bm_sources.scope(s) == "CONTENT"]
    except Exception: return []

def plan(root=ROOT):
    import tree_manifest as tm
    return tm.classify_drift(root, model_source_paths())

def _static_model_check(root, log):
    """The certified model must remain valid WITHOUT a rebuild. Absent model (clean clone before bootstrap) → reported, not faked."""
    import business
    m = business.load(force=True)
    if not m: return {"status": "SKIPPED", "detail": f"business model not built here ({business.last_error()}) — nothing to certify; bootstrap builds it"}
    st = business.model_state(m)
    if st["state"] != "CURRENT": raise SyncError("RELEASE_REQUIRED", f"business model is {st['state']} (changed {st['changed']}, missing {st['missing']}) — a model input changed: rebuild + skill.py release")
    import certify_business as cb
    core, ov = cb.load_built(); rec = cb.certify(core, ov, root=root, check_git=True)
    if rec["result"] != "PASS": raise SyncError("RELEASE_REQUIRED", "business certification would FAIL: " + "; ".join(f"{k}: {v['problems'][:2]}" for k, v in rec["checks"].items() if not v["pass"]))
    return {"status": "OK", "detail": f"model {rec['model_version']} core {rec['core_fingerprint']} still certified (no rebuild)"}

def _durable_regression(root, ss):
    """{table: (store_rows, file_rows)} for every durable table whose versioned file carries MORE rows than the local store — fail closed."""
    import engine
    st = engine._store(); d = ss.durable_dir(root); behind = {}
    for t in ss.DURABLE_TABLES:
        p = d / f"{t}.jsonl"
        if not p.exists(): continue
        rows = sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
        try: have = st.count(t)
        except Exception: have = 0
        if have < rows: behind[t] = (have, rows)
    return behind

def run(root=ROOT, dry_run=False, push=True, log=print, allow_branch=None):
    """Execute the sync. Returns the report dict; raises SyncError (fail closed) — the CLI maps it to a non-zero exit code."""
    import tree_manifest as tm, state_snapshot as ss
    root = pathlib.Path(root); rep = {"root": str(root), "at": datetime.datetime.now().isoformat(timespec="seconds"), "dry_run": dry_run, "steps": []}
    def step(name, status, detail=""):
        rep["steps"].append({"step": name, "status": status, "detail": detail}); log(f"  {'✓' if status == 'OK' else '·' if status in ('SKIPPED', 'DRY') else '✗'} {name}: {status}" + (f" — {detail}" if detail else ""))
    d = plan(root); rep["classification"] = d
    branch = d.get("branch"); want = allow_branch or "main"
    if branch != want: raise SyncError("WRONG_BRANCH", f"sync persists to {want}; current branch is {branch!r}")
    if d["state"] == "UNCLASSIFIED": raise SyncError("UNCLASSIFIED", f"unknown paths changed — nothing synced: {d['changes'].get('UNKNOWN') or d['checksum_drift'].get('UNKNOWN')}")
    if d["state"] == "RELEASE_REQUIRED":
        what = {k: v for k, v in list(d["changes"].items()) + [(f"checksum:{k}", v) for k, v in d["checksum_drift"].items()] if k.split(':')[-1] in tm.RELEASE_CLASSES}
        raise SyncError("RELEASE_REQUIRED", f"product/model change — use skill.py release: {what}")
    step("classify", "OK", f"{d['state']} · changes {{{', '.join(f'{k}: {len(v)}' for k, v in d['changes'].items())}}} · checksum drift {{{', '.join(f'{k}: {len(v)}' for k, v in d['checksum_drift'].items())}}} · ahead {d['ahead']} behind {d['behind']}")
    if d["state"] == "CLEAN": rep["result"] = "CLEAN"; step("result", "OK", "nothing to persist — GitHub main is current"); return rep
    # 2 static model still certified (no rebuild) — checked BEFORE anything is written
    sm = _static_model_check(root, log); step("static business model", sm["status"], sm["detail"])
    # 3 export durable state — never behind the versioned history: the local store must hold every row the durable files already carry
    # (a fresh machine before `state_snapshot.py import` would otherwise export an empty state and erase history)
    behind = _durable_regression(root, ss)
    if behind: raise SyncError("DURABLE_REGRESSION", f"local store holds fewer rows than the versioned durable files {behind} — import first (python .claude/runtime/state_snapshot.py import / bootstrap.py); nothing exported")
    if dry_run: step("durable state export", "DRY", "would export .claude/state/durable/*.jsonl")
    else:
        c = ss.export(root, log=lambda *a: None); step("durable state export", "OK", ", ".join(f"{k}={v}" for k, v in c.items()))
    # 4 checksums (only sync classes may move)
    spec = tm.live_data_spec(); ms = model_source_paths()
    cs = tm.verify_checksums(root); moving = cs["changed"] + cs["missing"] + cs["new"]
    bad = [f for f in moving if tm.classify_path(f, spec, ms) not in tm.SYNC_CLASSES]
    if bad: raise SyncError("RELEASE_REQUIRED", f"checksum refresh would cover non-data paths {bad} — use skill.py release")
    if dry_run: step("durable checksums", "DRY", f"would refresh {len(moving)} entries: {moving[:6]}")
    else:
        tm.write_checksums(root, root / ".claude" / "policy" / "durable_checksums.json"); v = tm.verify_checksums(root)
        if v["changed"] or v["missing"]: raise SyncError("INTEGRITY", f"checksums still drift after refresh: {v['changed'][:3]} {v['missing'][:3]}")
        step("durable checksums", "OK", f"refreshed {len(moving)} entries, verified {len(v['verified'])}")
    # 5 commit only sync-class paths
    d2 = plan(root)
    if d2["state"] not in ("SYNC_REQUIRED", "CLEAN"): raise SyncError(d2["state"], f"after export/checksums the tree is {d2['state']}: {d2['changes']}")
    paths = sorted({p for k in tm.SYNC_CLASSES for p in d2["changes"].get(k, [])})
    sha_before = _git(["rev-parse", "HEAD"], root).strip()
    if paths:
        if not (_git(["config", "--get", "user.name"], root, check=False).strip() and _git(["config", "--get", "user.email"], root, check=False).strip()):
            raise SyncError("GIT_IDENTITY", "git user.name/user.email not configured for this repository — configure once (git config user.name/user.email), then sync")
        by = {k: d2["changes"].get(k, []) for k in tm.SYNC_CLASSES if d2["changes"].get(k)}
        msg = "sync: live data + durable state — " + "; ".join(f"{k.lower()} {', '.join(pathlib.Path(p).name for p in v[:4])}{' …' if len(v) > 4 else ''}" for k, v in by.items()) + "\n\nLIVE DATA SYNC (skill.py sync): classified data-only change; static business model unchanged and still certified; durable checksums refreshed."
        if dry_run: step("commit", "DRY", f"would commit {len(paths)} path(s): {paths[:8]}")
        else:
            _git(["add", "--"] + paths, root); _git(["commit", "-q", "-m", msg, "--"] + paths, root)
            sha = _git(["rev-parse", "HEAD"], root).strip(); rep["commit"] = sha; step("commit", "OK", f"{sha[:12]} · {len(paths)} path(s): {paths[:8]}")
    else: step("commit", "SKIPPED", "no working-tree change to commit" + (f" (ahead {d2['ahead']})" if d2.get("ahead") else ""))
    # 6 push + verify
    if not push: step("push", "SKIPPED", "--no-push"); rep["result"] = "SYNCED_LOCAL" if paths else ("UNPUSHED" if (d2.get("ahead") or 0) else "CLEAN")
    elif dry_run: step("push", "DRY", "would push to upstream and verify HEAD == upstream"); rep["result"] = "DRY_RUN"
    else:
        up = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], root, check=False).strip()
        if not up: raise SyncError("NO_UPSTREAM", f"branch {branch} has no upstream — nothing pushed; set it once (git push -u origin {branch})")
        _git(["push", "-q"], root); _git(["fetch", "-q"], root)
        head, remote = _git(["rev-parse", "HEAD"], root).strip(), _git(["rev-parse", up], root).strip()
        if head != remote: raise SyncError("PUSH_UNVERIFIED", f"after push HEAD {head[:12]} ≠ {up} {remote[:12]}")
        step("push", "OK", f"{up} == HEAD {head[:12]}"); rep["result"] = "SYNCED"; rep["head"] = head
    final = plan(root); rep["final_state"] = final["state"]
    if not dry_run and push and final["state"] != "CLEAN": raise SyncError("NOT_CLEAN", f"after sync the tree is still {final['state']}: {final['changes']} {final['checksum_drift']}")
    step("result", "OK", f"{rep['result']} · tree {final['state']}" + (f" · {rep.get('head', rep.get('commit', sha_before))[:12]}" if rep.get("result") != "CLEAN" else ""))
    return rep

def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1]) if "--root" in argv else ROOT
    try:
        rep = run(root, dry_run="--dry-run" in argv, push="--no-push" not in argv, allow_branch=(argv[argv.index("--branch") + 1] if "--branch" in argv else None))
        if "--json" in argv: print(json.dumps(rep, ensure_ascii=False, indent=1))
        print(f"LIVE DATA SYNC {rep['result']}" + (f" — {rep['head'][:12]}" if rep.get("head") else "")); return 0
    except SyncError as e:
        print(f"⛔ LIVE DATA SYNC REFUSED — {e.code}: {e.detail}"); return {"RELEASE_REQUIRED": 2, "UNCLASSIFIED": 3}.get(e.code, 1)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
