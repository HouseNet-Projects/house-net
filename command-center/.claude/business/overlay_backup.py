# -*- coding: utf-8 -*-
"""SENSITIVE OVERLAY BACKUP / RESTORE — encrypted at rest with GnuPG symmetric AES-256 (standard, auditable; no custom crypto).

    python .claude/business/overlay_backup.py backup                       → <backup_dir>/overlay-<ts>-<fingerprint>.tar.gpg (+ .manifest.json)
    python .claude/business/overlay_backup.py verify  <archive.tar.gpg>    → decrypt to a temp dir, check every sha256 in the manifest, remove plaintext
    python .claude/business/overlay_backup.py restore <archive.tar.gpg> --to <dir>   [--force]   → atomic restore (staging dir + rename)
    python .claude/business/overlay_backup.py drill   [<archive.tar.gpg>]  → restore into an isolated temp dir, merge with the Core, prove it loads, clean up
    python .claude/business/overlay_backup.py list

Scope: overlay/ov_*.py (+ overlay/*.md if any) and the generated overlay.json (its meta carries schema/model version and
the overlay fingerprint). Nothing else — no .venv, caches, audit logs, raw exports or generated core files.
Key boundary: the passphrase lives in <key_file> OUTSIDE the repository and outside audit payloads (gpg reads it from the
file; it is never placed on a command line, never printed, never logged). Default locations (override with env):
  COMMAND_CENTER_BACKUP_KEY   default %USERPROFILE%/.command-center/overlay-backup.key   (created on first backup, 0600)
  COMMAND_CENTER_BACKUP_DIR   default %USERPROFILE%/.command-center/backups
Wrong or missing key → explicit failure (gpg exit code); integrity → sha256 manifest inside AND beside the archive."""
import sys, os, io, json, pathlib, tarfile, hashlib, datetime, subprocess, tempfile, shutil, secrets, argparse
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "runtime")); import python_runtime; python_runtime.ensure()
sys.path.insert(0, str(HERE))
OVERLAY_DIR = HERE / "overlay"
OVERLAY_JSON = HERE / "overlay.json"
def _default_key():
    """ONE external recovery key (Mission 4.1): recovery.key; the pre-4.1 overlay-backup.key is honoured as a fallback."""
    home = pathlib.Path(os.environ.get("COMMAND_CENTER_HOME") or (pathlib.Path.home() / ".command-center"))
    rk = pathlib.Path(os.environ.get("COMMAND_CENTER_RECOVERY_KEY_FILE") or (home / "recovery.key"))
    return rk if rk.exists() or not (home / "overlay-backup.key").exists() else home / "overlay-backup.key"
KEY_FILE = pathlib.Path(os.environ.get("COMMAND_CENTER_BACKUP_KEY") or _default_key())
BACKUP_DIR = pathlib.Path(os.environ.get("COMMAND_CENTER_BACKUP_DIR") or (pathlib.Path.home() / ".command-center" / "backups"))
FORMAT = "overlay-backup/1 · tar(ustar, utf-8) · gpg --symmetric AES256 (s2k iterated) · manifest.json sha256 per file"

class BackupError(Exception): pass

def _gpg():
    g = shutil.which("gpg") or shutil.which("gpg2")
    if not g: raise BackupError("GnuPG (gpg) not available — no standard encryption capability; backup contract stops here (no insecure substitute)")
    return g

def _sha(b): return hashlib.sha256(b).hexdigest()

def ensure_key(create=True):
    if KEY_FILE.exists():
        k = KEY_FILE.read_bytes().strip()
        if len(k) < 32: raise BackupError(f"key file {KEY_FILE} too short/corrupt")
        return KEY_FILE
    if not create: raise BackupError(f"backup key missing: {KEY_FILE} — restore impossible without the original key")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(secrets.token_urlsafe(48).encode("ascii") + b"\n")
    try: os.chmod(KEY_FILE, 0o600)
    except OSError: pass
    return KEY_FILE

def _in_repo(p):
    try: pathlib.Path(p).resolve().relative_to(ROOT.resolve()); return True
    except ValueError: return False

def scope_files():
    files = []
    if OVERLAY_DIR.is_dir():
        for p in sorted(OVERLAY_DIR.iterdir()):
            if p.is_file() and p.suffix in (".py", ".md", ".json"): files.append(("overlay/" + p.name, p))
    if OVERLAY_JSON.exists(): files.append(("overlay.json", OVERLAY_JSON))
    if not files: raise BackupError("nothing to back up: overlay/ and overlay.json absent")
    return files

def manifest(files):
    ov = json.loads(OVERLAY_JSON.read_text(encoding="utf-8")) if OVERLAY_JSON.exists() else {}
    meta = ov.get("meta", {})
    entries = {rel: {"sha256": _sha(p.read_bytes()), "size": p.stat().st_size} for rel, p in files}
    return {"format": FORMAT, "created_at": datetime.datetime.now().isoformat(timespec="seconds"), "workspace": "Command-center", "layer": "SENSITIVE_" + "OVERLAY",
            "schema_version": meta.get("schema_version"), "model_version": meta.get("model_version"), "overlay_fingerprint": meta.get("overlay_fingerprint"),
            "core_fingerprint": meta.get("core_fingerprint"), "source_snapshot_id": meta.get("source_snapshot_id"), "files": entries,
            "manifest_sha256": _sha(json.dumps(entries, sort_keys=True).encode("utf-8"))}

def backup(out_dir=None):
    gpg = _gpg(); key = ensure_key(True); files = scope_files(); man = manifest(files)
    out_dir = pathlib.Path(out_dir or BACKUP_DIR); out_dir.mkdir(parents=True, exist_ok=True)
    if _in_repo(out_dir): raise BackupError(f"backup dir {out_dir} is inside the repository — refused")
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); stem = f"overlay-{ts}-{(man['overlay_fingerprint'] or 'nofp')[:12]}"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT, encoding="utf-8") as tar:
        for rel, p in files: tar.add(str(p), arcname=rel)
        mb = json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8"); ti = tarfile.TarInfo("manifest.json"); ti.size = len(mb); ti.mtime = int(datetime.datetime.now().timestamp()); tar.addfile(ti, io.BytesIO(mb))
    plain = buf.getvalue(); archive = out_dir / f"{stem}.tar.gpg"
    r = subprocess.run([gpg, "--batch", "--yes", "--quiet", "--symmetric", "--cipher-algo", "AES256", "--s2k-mode", "3", "--s2k-count", "65011712", "--pinentry-mode", "loopback", "--passphrase-file", str(key), "-o", str(archive)], input=plain, capture_output=True)
    if r.returncode != 0 or not archive.exists(): raise BackupError(f"gpg encryption failed rc={r.returncode}: {r.stderr.decode('utf-8', 'replace')[:200]}")
    side = out_dir / f"{stem}.manifest.json"; man["archive"] = archive.name; man["archive_sha256"] = _sha(archive.read_bytes()); man["archive_size"] = archive.stat().st_size
    side.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return archive, side, man

def decrypt_to(archive, tmp):
    gpg = _gpg(); key = ensure_key(False); tmp = pathlib.Path(tmp); tmp.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([gpg, "--batch", "--yes", "--quiet", "--decrypt", "--pinentry-mode", "loopback", "--passphrase-file", str(key), str(archive)], capture_output=True)
    if r.returncode != 0: raise BackupError(f"decryption FAILED (wrong key or corrupt archive) rc={r.returncode}: {r.stderr.decode('utf-8', 'replace').strip()[:160]}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout), mode="r") as tar:
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in m.name: raise BackupError(f"unsafe member {m.name}")
        try: tar.extractall(tmp, filter="data")
        except TypeError: tar.extractall(tmp)
    man = json.loads((tmp / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    for rel, e in man["files"].items():
        p = tmp / rel
        if not p.exists(): problems.append(f"missing {rel}"); continue
        if _sha(p.read_bytes()) != e["sha256"]: problems.append(f"sha256 mismatch {rel}")
    entries = {k: v for k, v in man["files"].items()}
    if _sha(json.dumps(entries, sort_keys=True).encode("utf-8")) != man["manifest_sha256"]: problems.append("manifest self-hash mismatch")
    if problems: raise BackupError("integrity verification FAILED: " + "; ".join(problems))
    return man

def verify(archive):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ovbk_verify_"))
    try: man = decrypt_to(archive, tmp)
    finally: shutil.rmtree(tmp, ignore_errors=True)
    side = pathlib.Path(archive).with_name(pathlib.Path(archive).name.replace(".tar.gpg", ".manifest.json"))
    if side.exists():
        sm = json.loads(side.read_text(encoding="utf-8"))
        if sm.get("archive_sha256") and sm["archive_sha256"] != _sha(pathlib.Path(archive).read_bytes()): raise BackupError("archive sha256 differs from the side manifest")
    return man

def restore(archive, to, force=False):
    to = pathlib.Path(to)
    if _in_repo(to) and not force: raise BackupError(f"restore target {to} is inside the repository; use --force only for the real overlay location")
    staging = to.with_name(to.name + ".restoring"); shutil.rmtree(staging, ignore_errors=True)
    man = decrypt_to(archive, staging)
    if to.exists():
        if not force: raise BackupError(f"target {to} exists — refusing to overwrite (use --force)")
        bak = to.with_name(to.name + ".previous"); shutil.rmtree(bak, ignore_errors=True); to.rename(bak)
    staging.rename(to)                      # atomic on the same filesystem
    return man

def drill(archive=None):
    """Prove recovery: restore into an isolated temp dir, assemble Core + restored overlay, load through the runtime, clean up."""
    archive = pathlib.Path(archive) if archive else latest()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ovbk_drill_")); report = {"archive": str(archive), "steps": []}
    try:
        man = restore(archive, tmp / "restored"); report["steps"].append("decrypt+integrity OK")
        ov = json.loads((tmp / "restored" / "overlay.json").read_text(encoding="utf-8"))
        if ov["meta"].get("overlay_fingerprint") != man["overlay_fingerprint"]: raise BackupError("overlay fingerprint in restored overlay.json ≠ manifest")
        if OVERLAY_JSON.exists():
            cur = json.loads(OVERLAY_JSON.read_text(encoding="utf-8"))["meta"].get("overlay_fingerprint")
            report["fingerprint_matches_production"] = (cur == man["overlay_fingerprint"])
        report["steps"].append(f"overlay fingerprint {man['overlay_fingerprint']} verified")
        # assemble an isolated model dir: current Core files + restored overlay + certification → load via the runtime
        model = tmp / "model"; model.mkdir()
        import bm_schema
        for n in bm_schema.CORE_FILES + ("certification",):
            src = HERE / f"{n}.json"
            if src.exists(): shutil.copy(src, model / f"{n}.json")
        shutil.copy(tmp / "restored" / "overlay.json", model / "overlay.json")
        sys.path.insert(0, str(HERE.parent / "skills")); import business
        old = os.environ.get("COMMAND_CENTER_BUSINESS_DIR"); os.environ["COMMAND_CENTER_BUSINESS_DIR"] = str(model)
        try:
            m = business.load(force=True)
            if not m: raise BackupError(f"restored model failed to load: {business.last_error()}")
            names = m["_names"]; rendered = business.render("owner @P0"); st = business.model_state(m)
            report["steps"].append(f"business model loads: {len(names)} persons merged, render('@P0')={'ok' if '@P0' not in rendered else 'FAIL'}, state={st['state']}, overlay_present={st['overlay_present']}")
            if "@P0" in rendered or not st["overlay_present"]: raise BackupError("overlay did not merge with the core")
        finally:
            if old is None: os.environ.pop("COMMAND_CENTER_BUSINESS_DIR", None)
            else: os.environ["COMMAND_CENTER_BUSINESS_DIR"] = old
            business.load(force=True)
        # restored files must not be inside the repo / git index
        st_ = subprocess.run(["git", "status", "--porcelain", "--ignored", str(tmp)], cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
        report["steps"].append("restored plaintext is outside the repository; git sees nothing" if not st_ else f"git sees: {st_[:80]}")
        report["result"] = "PASS"; report["manifest"] = {k: man[k] for k in ("created_at", "schema_version", "model_version", "overlay_fingerprint", "core_fingerprint")}; report["files"] = sorted(man["files"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True); report["plaintext_removed"] = not tmp.exists()
    return report

def latest():
    arcs = sorted(BACKUP_DIR.glob("overlay-*.tar.gpg"))
    if not arcs: raise BackupError(f"no backups in {BACKUP_DIR}")
    return arcs[-1]

def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["backup", "verify", "restore", "drill", "list"]); ap.add_argument("archive", nargs="?"); ap.add_argument("--to"); ap.add_argument("--force", action="store_true"); a = ap.parse_args(argv)
    try:
        if a.cmd == "backup":
            arc, side, man = backup(); print(f"backup OK → {arc} ({man['archive_size']} bytes) · manifest {side.name} · files {len(man['files'])} · overlay {man['overlay_fingerprint']} · model {man['model_version']} · schema {man['schema_version']}"); return 0
        if a.cmd == "verify":
            man = verify(a.archive or latest()); print(f"verify OK · {len(man['files'])} files · overlay {man['overlay_fingerprint']} · created {man['created_at']}"); return 0
        if a.cmd == "restore":
            if not a.to: print("--to <dir> required"); return 2
            man = restore(a.archive or latest(), a.to, a.force); print(f"restore OK → {a.to} · {len(man['files'])} files · overlay {man['overlay_fingerprint']}"); return 0
        if a.cmd == "drill":
            rep = drill(a.archive); print(json.dumps(rep, ensure_ascii=False, indent=1)); return 0 if rep.get("result") == "PASS" else 1
        if a.cmd == "list":
            for p in sorted(BACKUP_DIR.glob("overlay-*.tar.gpg")): print(p.name, p.stat().st_size)
            return 0
    except BackupError as e: print(f"⛔ {e}"); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
