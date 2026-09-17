# -*- coding: utf-8 -*-
"""CANONICAL TREE MANIFEST — the machine-readable filesystem contract of Command-center, DERIVED from workspace_policy.json
(one definition, not two): every required path with kind, durability class and restore rule; plus content checksums of durable
files and a parity snapshot used to compare the source workspace with a clean-machine restore.

    python .claude/policy/tree_manifest.py build --write        write .claude/policy/workspace_tree_manifest.json from the policy
    python .claude/policy/tree_manifest.py check                 manifest file == derived manifest (no competing definition)
    python .claude/policy/tree_manifest.py verify [--root R]     every required path physically exists (after clone/bootstrap)
    python .claude/policy/tree_manifest.py checksums --write|--verify [--root R]
    python .claude/policy/tree_manifest.py snapshot [--root R] [--out F]      parity snapshot (required paths + durable files + sha256)
    python .claude/policy/tree_manifest.py parity <source.json> <restored.json>

Durability classes: VERSION_DIRECTLY · VERSION_ENCRYPTED · REGENERATE · MACHINE_LOCAL · EPHEMERAL."""
import sys, os, json, hashlib, pathlib, datetime, fnmatch
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); import paths        # ONE business-root resolver (workspace_policy.json -> business_root)
ROOT = HERE.parent.parent
POLICY = HERE / "workspace_policy.json"
MANIFEST = HERE / "workspace_tree_manifest.json"
CHECKSUMS = HERE / "durable_checksums.json"
MANIFEST_VERSION = "1.0"

DURABLE_DIRS = paths.areas() + (".claude/business", ".claude/docs", ".claude/hooks", ".claude/policy",
                ".claude/runtime", ".claude/skills", ".claude/tools", ".claude/tests", ".claude/integrations", ".claude/state/durable", ".secure")
DURABLE_ROOT_FILES = ("CLAUDE.md", "README.md", "bootstrap.py", ".gitignore", ".gitattributes") + paths.registers()
REGENERATED_GLOBS = (".claude/business/*.json", ".claude/business/Business-model.md", ".claude/integrations/certification.json", "**/__pycache__/**", ".venv/**")
EPHEMERAL_GLOBS = (".claude/state/*", ".claude/audit/**", "*.lock", "*.tmp", "~$*", "desktop.ini", ".claude/settings.local.json")
SKIP_WALK = {".git", ".venv", "__pycache__"}
# Versioned but rewritten by every release/bootstrap (timestamps, appended history): restored by clone, then legitimately regenerated —
# excluded from content checksums and parity (their EXISTENCE is still required by the manifest where listed).
RELEASE_CHURN = ("**/.claude/skills/certifications/*.json", ".claude/skills/certifications/*.json", ".claude/skills/registry.json", ".claude/docs/Registry-audit-*.md",
                 ".claude/state/durable/audit.jsonl", ".claude/state/durable/business_observations.jsonl", ".claude/state/durable/actions.jsonl", ".claude/state/durable/write_certifications.json",
                 ".claude/state/durable/checkpoints.jsonl", ".claude/state/durable/loops.jsonl", ".claude/state/durable/alerts.jsonl", ".claude/policy/durable_checksums.json")

def _churn(rel):
    r = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(r, g) for g in RELEASE_CHURN)

def load_policy(p=POLICY): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))

def _is_business(rel, pol=None):
    """True for a path inside Gev's business workspace, wherever the declared business root puts it."""
    b = paths.to_business(rel, pol)
    return b is not None and (b == "" or b.split("/")[0] in paths.AREAS or b in paths.REGISTERS)

def _cls_for(rel):
    r = rel.replace("\\", "/")
    for g in EPHEMERAL_GLOBS:
        if fnmatch.fnmatch(r, g) or (g.endswith("/**") and r.startswith(g[:-3] + "/")): return "EPHEMERAL"
    for g in REGENERATED_GLOBS:
        if fnmatch.fnmatch(r, g) or (g.endswith("/**") and r.startswith(g[:-3] + "/")): return "REGENERATE"
    if r.startswith(".secure/") and r.endswith(".gpg"): return "VERSION_ENCRYPTED"
    return "VERSION_DIRECTLY"

def build(pol=None):
    """Derive the manifest from the policy: root files/dirs, canonical directories and their fixed subdirs, durability + restore rule per entry."""
    pol = pol or load_policy(); rt = pol["root"]; entries = []
    def add(path, kind, required, durability, restore, classification="INTERNAL", note=None):
        e = {"path": path, "kind": kind, "required": bool(required), "durability": durability, "restore": restore, "classification": classification}
        if note: e["note"] = note
        entries.append(e)
    for f in list(rt["required_files"]) + list(paths.registers(pol)):
        add(f, "file", True, "VERSION_DIRECTLY", "git clone", "CONFIDENTIAL" if pathlib.PurePosixPath(f).name in paths.REGISTERS else "INTERNAL")
    for f in (".gitignore", ".gitattributes"): add(f, "file", True, "VERSION_DIRECTLY", "git clone")
    for d in list(rt["required_dirs"]) + list(paths.areas(pol)):
        add(d, "directory", True, "VERSION_DIRECTLY", "git clone (.gitkeep keeps empty directories alive)", "CONFIDENTIAL" if _is_business(d, pol) else "INTERNAL")
    add(".claude/business", "directory", True, "VERSION_DIRECTLY", "git clone (bm_*.py + overlay authoring; generated json regenerated)", "CONFIDENTIAL")
    add(".claude/integrations", "directory", True, "VERSION_DIRECTLY", "git clone (adapters, registry, fixed reader)", "INTERNAL")
    add(".venv", "directory", False, "REGENERATE", "bootstrap.py → python_runtime.py bootstrap (requirements.lock)", "PUBLIC")
    add(".git", "directory", True, "MACHINE_LOCAL", "git clone", "PUBLIC")
    for area, dc in pol["directories"].items():
        if area not in [e["path"] for e in entries] and dc.get("required", True):
            add(area, "directory", True, "REGENERATE" if area in (".claude/state", ".claude/audit") else "VERSION_DIRECTLY",
                "bootstrap.py creates" if area in (".claude/state", ".claude/audit") else "git clone (.gitkeep)", "CONFIDENTIAL" if _is_business(area, pol) or "business" in area or "state" in area or "audit" in area else "INTERNAL")
        for sub in dc.get("fixed_subdirs", []):
            p = f"{area}/{sub}"
            if p not in [e["path"] for e in entries] and p not in pol["directories"]:
                add(p, "directory", True, "VERSION_DIRECTLY", "git clone (.gitkeep)", "CONFIDENTIAL" if _is_business(area, pol) else "INTERNAL")
        for sub in dc.get("optional_subdirs", []):
            p = f"{area}/{sub}"
            if p not in [e["path"] for e in entries] and p not in pol["directories"]: add(p, "directory", False, "VERSION_DIRECTLY", "git clone", "INTERNAL")
    add(paths.to_repo("00_Inbox/Input.md", pol), "file", True, "VERSION_DIRECTLY", "git clone", "CONFIDENTIAL")
    add(".claude/settings.json", "file", True, "VERSION_DIRECTLY", "git clone")
    for f in (pol.get("scope_lock") or {}).get("enforcement_files", []):
        add(f, "file", True, "VERSION_DIRECTLY", "git clone (HARD SCOPE LOCK machinery — the rule is only real if it exists)")
    add(".claude/runtime/requirements.txt", "file", True, "VERSION_DIRECTLY", "git clone"); add(".claude/runtime/requirements.lock", "file", True, "VERSION_DIRECTLY", "git clone")
    add(".claude/skills/registry.json", "file", True, "VERSION_DIRECTLY", "git clone; rebuilt by skill.py release")
    add(".claude/policy/workspace_tree_manifest.json", "file", True, "VERSION_DIRECTLY", "git clone; regenerated by tree_manifest.py build (must equal the derived manifest)")
    add(".claude/policy/durable_checksums.json", "file", True, "VERSION_DIRECTLY", "git clone; refreshed by release/bootstrap")
    add(".claude/state/durable/commitments.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import (idempotent)", "CONFIDENTIAL")
    add(".claude/state/durable/decisions.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import", "CONFIDENTIAL")
    add(".claude/state/durable/audit.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import (governance history)", "CONFIDENTIAL")
    add(".claude/state/durable/actions.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import (governed mutations: idempotency survives restart)", "CONFIDENTIAL")
    add(".claude/state/durable/checkpoints.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import (Mission 5 observation checkpoints: signatures only)", "CONFIDENTIAL")
    add(".claude/state/durable/loops.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import (Mission 5 open management loops: references only)", "CONFIDENTIAL")
    add(".claude/state/durable/alerts.jsonl", "file", True, "VERSION_DIRECTLY", "git clone → state_snapshot.py import (alert state: dedupe/escalation/ack/resolution, references only)", "CONFIDENTIAL")
    add(".secure/manifest.json", "file", True, "VERSION_DIRECTLY", "git clone (names/checksums/restore paths only)")
    add(".secure/credentials.gpg", "file", True, "VERSION_ENCRYPTED", "bootstrap.py → secure_recovery.py restore (needs the external recovery key)", "RESTRICTED")
    add(".claude/business/overlay", "directory", True, "VERSION_DIRECTLY", "git clone (overlay authoring ov_*.py)", "CONFIDENTIAL")
    for f in ("sources", "business_model", "processes", "ownership", "kpis", "targets", "playbooks", "routines", "gaps", "overlay", "certification"):
        add(f".claude/business/{f}.json", "file", False, "REGENERATE", "bootstrap.py → build_business_model.py", "CONFIDENTIAL")
    add(".claude/business/Business-model.md", "file", False, "REGENERATE", "bootstrap.py → build_business_model.py", "CONFIDENTIAL")
    add(".claude/integrations/certification.json", "file", False, "REGENERATE", "bootstrap.py → certify_integrations.py")
    add(".claude/state/skill_state.db", "file", False, "EPHEMERAL", "recreated by the hardened store; durable rows imported from .claude/state/durable", "CONFIDENTIAL")
    add(".claude/audit/skill_audit.jsonl", "file", False, "EPHEMERAL", "best-effort mirror; the versioned form is .claude/state/durable/audit.jsonl", "CONFIDENTIAL")
    add(".claude/settings.local.json", "file", False, "MACHINE_LOCAL", "per machine", "RESTRICTED")
    seen = set(); uniq = []
    for e in entries:
        if e["path"] in seen: continue
        seen.add(e["path"]); uniq.append(e)
    return {"manifest_version": MANIFEST_VERSION, "policy_version": pol["policy_version"], "workspace": pol["workspace_name"], "durable_dirs": list(DURABLE_DIRS), "durable_root_files": list(DURABLE_ROOT_FILES),
            "regenerated_globs": list(REGENERATED_GLOBS), "ephemeral_globs": list(EPHEMERAL_GLOBS), "release_churn": list(RELEASE_CHURN), "entries": sorted(uniq, key=lambda e: e["path"]),
            "recovery": {"command": "python bootstrap.py", "external_secret": "~/.command-center/recovery.key (ONE key: decrypts .secure/credentials.gpg and overlay backups)", "law": pol.get("durability", {}).get("law")}}

def write_manifest(m=None, path=MANIFEST):
    m = m or build(); pathlib.Path(path).write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"); return m

def check_manifest(path=MANIFEST, pol=None):
    """Problems if the stored manifest differs from the policy-derived one."""
    if not pathlib.Path(path).exists(): return ["workspace_tree_manifest.json missing — run tree_manifest.py build --write"]
    try: stored = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except ValueError as e: return [f"workspace_tree_manifest.json unreadable: {e}"]
    derived = build(pol)
    if stored != derived: return ["workspace_tree_manifest.json is out of date with workspace_policy.json — run tree_manifest.py build --write"]
    return []

def verify(root=ROOT, m=None):
    """Required paths that do not physically exist."""
    root = pathlib.Path(root); m = m or build(); missing = []
    for e in m["entries"]:
        if not e["required"] or e["durability"] == "MACHINE_LOCAL": continue          # .git etc. are the clone itself, not canonical content
        p = root / e["path"]
        if e["kind"] == "directory" and not p.is_dir(): missing.append(e["path"])
        if e["kind"] == "file" and not p.is_file(): missing.append(e["path"])
    return missing

def _sha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""): h.update(b)
    return h.hexdigest()

def durable_files(root=ROOT):
    """Every durable, directly-versioned file (business workspace, model authoring, docs, code, durable state, encrypted artifacts, root files)."""
    root = pathlib.Path(root); out = []
    for f in DURABLE_ROOT_FILES:
        if (root / f).is_file(): out.append(f)
    for d in DURABLE_DIRS:
        base = root / d
        if not base.is_dir(): continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [x for x in dn if x not in SKIP_WALK]
            for f in fn:
                rel = (pathlib.Path(dp) / f).relative_to(root).as_posix()
                if _cls_for(rel) != "VERSION_DIRECTLY" and not rel.startswith(".secure/"): continue
                if f.endswith((".pyc", ".tmp", ".lock")) or f.startswith("~$") or _churn(rel): continue
                out.append(rel)
    return sorted(set(out))

def checksums(root=ROOT):
    root = pathlib.Path(root)
    return {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "algorithm": "sha256", "files": {rel: {"sha256": _sha(root / rel), "size": (root / rel).stat().st_size} for rel in durable_files(root) if rel != ".claude/policy/durable_checksums.json"}}

def write_checksums(root=ROOT, path=CHECKSUMS):
    c = checksums(root); pathlib.Path(path).write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"); return c

def verify_checksums(root=ROOT, path=None):
    """Compare the durable files on disk with the stored checksum file → {verified, changed, missing, new}."""
    root = pathlib.Path(root); path = path or (root / ".claude" / "policy" / "durable_checksums.json")
    stored = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["files"] if pathlib.Path(path).exists() else {}
    cur = checksums(root)["files"]; res = {"verified": [], "changed": [], "missing": [], "new": []}
    for rel, v in stored.items():
        if rel not in cur: res["missing"].append(rel)
        elif cur[rel]["sha256"] != v["sha256"]: res["changed"].append(rel)
        else: res["verified"].append(rel)
    res["new"] = [r for r in cur if r not in stored and r != ".claude/policy/durable_checksums.json"]
    return res

def snapshot(root=ROOT):
    """Parity snapshot: required manifest paths present/missing + durable files with sha256 (regenerated/ephemeral paths excluded by design)."""
    root = pathlib.Path(root); m = build()
    req = {e["path"]: ((root / e["path"]).is_dir() if e["kind"] == "directory" else (root / e["path"]).is_file()) for e in m["entries"] if e["required"]}
    files = {rel: _sha(root / rel) for rel in durable_files(root) if rel != ".claude/policy/durable_checksums.json"}
    return {"root": str(root), "taken_at": datetime.datetime.now().isoformat(timespec="seconds"), "required": req, "durable_files": files, "counts": {"required": len(req), "required_present": sum(req.values()), "durable_files": len(files)}}

def parity(src, dst):
    """Compare two snapshots → missing required, drifted durable files, extra durable files (unexpected drift)."""
    miss_req = [p for p, ok in dst["required"].items() if not ok]
    missing_files = [f for f in src["durable_files"] if f not in dst["durable_files"]]
    changed = [f for f in src["durable_files"] if f in dst["durable_files"] and src["durable_files"][f] != dst["durable_files"][f]]
    extra = [f for f in dst["durable_files"] if f not in src["durable_files"]]
    return {"source_required": len(src["required"]), "restored_required": len(dst["required"]), "missing_required": miss_req, "missing_durable_files": missing_files, "changed_durable_files": changed, "unexpected_extra_files": extra,
            "pass": not (miss_req or missing_files or changed or extra)}

# ───────────────────────── drift classification: LIVE DATA SYNC vs PRODUCT RELEASE (policy durability.live_data) ─────────────────────────
DRIFT_STATES = ("CLEAN", "SYNC_REQUIRED", "RELEASE_REQUIRED", "UNCLASSIFIED")
SYNC_CLASSES = ("LIVE_DATA", "DOCUMENT", "DURABLE_STATE", "INTEGRITY_META")          # persisted by skill.py sync (data only)
RELEASE_CLASSES = ("PRODUCT", "MODEL_SOURCE", "RELEASE_ARTIFACT")                   # only skill.py release may certify + persist these
BUSINESS_DIRS = paths.areas()

def _git_out(args, root):
    import subprocess
    r = subprocess.run(["git"] + list(args), cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0: raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return r.stdout

def live_data_spec(pol=None):
    ld = (pol or load_policy()).get("durability", {}).get("live_data", {})
    return {"files": list(ld.get("live_data_files", [])), "state_dirs": list(ld.get("live_state_dirs", [])), "meta": list(ld.get("integrity_metadata", []))}

def classify_path(rel, spec=None, model_sources=()):
    """One deterministic class per path: LIVE_DATA · DOCUMENT · DURABLE_STATE · INTEGRITY_META (sync) — MODEL_SOURCE · PRODUCT ·
    RELEASE_ARTIFACT (release) — UNKNOWN (fail closed). A declared CONTENT-scoped business-model source is MODEL_SOURCE even inside a business folder."""
    spec = spec or live_data_spec(); r = rel.replace("\\", "/").strip("/")
    if r in spec["meta"]: return "INTEGRITY_META"
    if r in spec["files"]: return "LIVE_DATA"
    if any(r == d.strip("/") or r.startswith(d.strip("/") + "/") for d in spec["state_dirs"]): return "DURABLE_STATE"
    if r in {m.replace("\\", "/") for m in model_sources}: return "MODEL_SOURCE"
    if _churn(r): return "RELEASE_ARTIFACT"
    if any(r == d or r.startswith(d + "/") for d in BUSINESS_DIRS): return "DOCUMENT"
    if r.startswith(".claude/") or r.startswith(".secure/") or r in DURABLE_ROOT_FILES or r in (".gitignore", ".gitattributes"): return "PRODUCT"
    return "UNKNOWN"

def classify_drift(root=ROOT, model_sources=(), pol=None):
    """Deterministic state of the working tree vs the last commit and vs the stored checksums:
       CLEAN — nothing to persist and no unpushed commit · SYNC_REQUIRED — only live data / documents / durable state / integrity metadata differ
       (or commits are not pushed) · RELEASE_REQUIRED — product, model-authoring or extraction-source change · UNCLASSIFIED — an unknown path (fail closed)."""
    root = pathlib.Path(root); spec = live_data_spec(pol); changes, stale = {}, {}
    for line in _git_out(["status", "--porcelain", "--untracked-files=all"], root).splitlines():
        if not line.strip(): continue
        path = line[3:].strip()
        for p in (path.split(" -> ") if " -> " in path else [path]): changes.setdefault(classify_path(p.strip('"'), spec, model_sources), []).append(p.strip('"'))
    cs = verify_checksums(root)
    for f in cs["changed"] + cs["missing"] + cs["new"]: stale.setdefault(classify_path(f, spec, model_sources), []).append(f)
    ahead = behind = None
    try: a, b = _git_out(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], root).split(); ahead, behind = int(a), int(b)
    except Exception: pass
    if changes.get("UNKNOWN") or stale.get("UNKNOWN"): state = "UNCLASSIFIED"
    elif any(changes.get(k) or stale.get(k) for k in RELEASE_CLASSES): state = "RELEASE_REQUIRED"
    elif changes or stale or (ahead or 0) > 0: state = "SYNC_REQUIRED"
    else: state = "CLEAN"
    try: branch = _git_out(["branch", "--show-current"], root).strip()
    except Exception: branch = None
    return {"state": state, "changes": {k: sorted(v) for k, v in changes.items()}, "checksum_drift": {k: sorted(v) for k, v in stale.items()}, "ahead": ahead, "behind": behind, "branch": branch}

def main(argv):
    cmd = argv[0] if argv else "check"; root = ROOT
    if "--root" in argv: root = pathlib.Path(argv[argv.index("--root") + 1])
    if cmd == "build":
        m = build()
        if "--write" in argv: write_manifest(m); print(f"manifest written: {len(m['entries'])} entries ({MANIFEST})")
        else: print(json.dumps(m, ensure_ascii=False, indent=1))
        return 0
    if cmd == "check":
        p = check_manifest(); print("\n".join(p) if p else "✓ tree manifest matches workspace_policy.json"); return 1 if p else 0
    if cmd == "verify":
        miss = verify(root); print(("✗ missing required paths: " + ", ".join(miss)) if miss else f"✓ every required path exists under {root}"); return 1 if miss else 0
    if cmd == "checksums":
        if "--write" in argv: c = write_checksums(root, (root / ".claude" / "policy" / "durable_checksums.json")); print(f"checksums written for {len(c['files'])} durable files"); return 0
        r = verify_checksums(root); print(f"verified {len(r['verified'])} · changed {len(r['changed'])} · missing {len(r['missing'])} · new {len(r['new'])}")
        for k in ("changed", "missing"):
            for f in r[k][:20]: print(f"  {k}: {f}")
        return 1 if (r["changed"] or r["missing"]) else 0
    if cmd == "snapshot":
        s = snapshot(root); out = argv[argv.index("--out") + 1] if "--out" in argv else None
        if out: pathlib.Path(out).write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8"); print(f"snapshot: {s['counts']} → {out}")
        else: print(json.dumps(s["counts"]))
        return 0
    if cmd == "drift":
        d = classify_drift(root); print(json.dumps(d, ensure_ascii=False, indent=1)); return {"CLEAN": 0, "SYNC_REQUIRED": 1, "RELEASE_REQUIRED": 2, "UNCLASSIFIED": 3}[d["state"]]
    if cmd == "parity" and len(argv) >= 3:
        a = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8")); b = json.loads(pathlib.Path(argv[2]).read_text(encoding="utf-8")); r = parity(a, b)
        print(json.dumps(r, ensure_ascii=False, indent=1)); return 0 if r["pass"] else 1
    print(__doc__); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
