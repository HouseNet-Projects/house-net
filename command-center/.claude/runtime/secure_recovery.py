# -*- coding: utf-8 -*-
"""SECRET RECOVERY — the ONE encrypted recovery artifact for active external-system credentials.

    .secure/credentials.gpg   GnuPG symmetric AES-256 (s2k iterated) tar of ~/.command-center/integrations/*.json  — versioned
    .secure/manifest.json     artifact version, created_at, format, expected credential names, sha256 per file + of the artifact,
                              restore paths — NO secret values                                                        — versioned

    python .claude/runtime/secure_recovery.py backup             package the local secret configs (idempotent; empty set allowed)
    python .claude/runtime/secure_recovery.py verify             decrypt in memory/temp, check checksums, never write plaintext to the repo
    python .claude/runtime/secure_recovery.py restore [--force]  decrypt into $COMMAND_CENTER_HOME/integrations (existing files kept unless --force)
    python .claude/runtime/secure_recovery.py status

Recovery key: COMMAND_CENTER_RECOVERY_KEY_FILE, else $COMMAND_CENTER_HOME/recovery.key, else ~/.command-center/recovery.key.
The key is read by gpg from the file (--passphrase-file); it is never printed, logged, audited or written anywhere else.
Wrong key / missing key → explicit failure. No custom cryptography."""
import sys, os, io, json, tarfile, hashlib, pathlib, subprocess, tempfile, datetime, shutil, secrets as _pysecrets
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SECURE = ROOT / ".secure"; ARTIFACT = SECURE / "credentials.gpg"; MANIFEST = SECURE / "manifest.json"
ARTIFACT_VERSION = "1.0"

class RecoveryError(Exception): pass

def home_dir():
    return pathlib.Path(os.environ.get("COMMAND_CENTER_HOME") or (pathlib.Path.home() / ".command-center"))

def key_file():
    return pathlib.Path(os.environ.get("COMMAND_CENTER_RECOVERY_KEY_FILE") or (home_dir() / "recovery.key"))

def ensure_key(create=False):
    k = key_file()
    if k.exists():
        if len(k.read_bytes().strip()) < 32: raise RecoveryError(f"recovery key {k} too short/corrupt")
        return k
    if not create: raise RecoveryError(f"recovery key missing: {k} — restore impossible without the external key")
    k.parent.mkdir(parents=True, exist_ok=True); k.write_bytes(_pysecrets.token_urlsafe(48).encode("ascii") + b"\n")
    try: os.chmod(k, 0o600)
    except OSError: pass
    return k

def _gpg():
    g = shutil.which("gpg") or shutil.which("gpg2")
    if not g: raise RecoveryError("gpg not found — GnuPG is required for the encrypted recovery artifact")
    return g

def _sha(b): return hashlib.sha256(b).hexdigest()

def scope_files():
    """Secret configs that grant access to other systems: $COMMAND_CENTER_HOME/integrations/*.json (may be empty)."""
    d = home_dir() / "integrations"
    return sorted(p for p in d.glob("*.json")) if d.is_dir() else []

def expected_credentials():
    try:
        sys.path.insert(0, str(ROOT / ".claude" / "integrations")); import registry
        return {iid: list(spec["auth"].get("secrets", [])) for iid, spec in registry.INTEGRATIONS.items() if spec["auth"].get("secrets")}
    except Exception: return {}

def backup(log=print):
    key = ensure_key(create=True); files = scope_files(); SECURE.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); entries = []
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for p in files:
            data = p.read_bytes(); ti = tarfile.TarInfo(name=f"integrations/{p.name}"); ti.size = len(data); ti.mtime = int(p.stat().st_mtime); ti.mode = 0o600
            tar.addfile(ti, io.BytesIO(data)); entries.append({"name": f"integrations/{p.name}", "sha256": _sha(data), "size": len(data), "restore_path": f"$COMMAND_CENTER_HOME/integrations/{p.name}"})
    plain = buf.getvalue()
    with tempfile.TemporaryDirectory(prefix="ccsec_") as td:
        src = pathlib.Path(td) / "c.tar"; out = pathlib.Path(td) / "c.gpg"; src.write_bytes(plain)
        r = subprocess.run([_gpg(), "--batch", "--yes", "--quiet", "--pinentry-mode", "loopback", "--passphrase-file", str(key), "--symmetric", "--cipher-algo", "AES256", "--s2k-mode", "3", "--s2k-count", "65011712", "--output", str(out), str(src)], capture_output=True, text=True)
        if r.returncode != 0: raise RecoveryError(f"gpg encryption failed (rc {r.returncode})")
        enc = out.read_bytes()
    ARTIFACT.write_bytes(enc)
    exp = expected_credentials(); present = {e["name"].split("/")[-1].rsplit(".", 1)[0] for e in entries}
    man = {"artifact_version": ARTIFACT_VERSION, "created_at": datetime.datetime.now().isoformat(timespec="seconds"), "format": "tar inside GnuPG symmetric AES-256 (s2k iterated+salted)", "artifact": "credentials.gpg", "artifact_sha256": _sha(enc), "artifact_size": len(enc),
           "plain_sha256": _sha(plain), "files": entries, "expected_credentials": {iid: {"secrets": names, "status": "PRESENT" if iid in present else "ABSENT"} for iid, names in exp.items()},
           "key": "external — COMMAND_CENTER_RECOVERY_KEY_FILE | $COMMAND_CENTER_HOME/recovery.key | ~/.command-center/recovery.key (never in Git)", "restore": "python bootstrap.py (or secure_recovery.py restore)"}
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"secure backup: {len(entries)} credential file(s) → .secure/credentials.gpg ({len(enc)} bytes); expected: " + ", ".join(f"{k}={v['status']}" for k, v in man["expected_credentials"].items()))
    return man

def _decrypt():
    key = ensure_key(create=False)
    if not ARTIFACT.exists(): raise RecoveryError(".secure/credentials.gpg missing")
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    if not man: raise RecoveryError(".secure/manifest.json missing")
    enc = ARTIFACT.read_bytes()
    if _sha(enc) != man["artifact_sha256"]: raise RecoveryError("artifact sha256 does not match the manifest — integrity FAILED")
    with tempfile.TemporaryDirectory(prefix="ccsec_") as td:
        src = pathlib.Path(td) / "c.gpg"; out = pathlib.Path(td) / "c.tar"; src.write_bytes(enc)
        r = subprocess.run([_gpg(), "--batch", "--yes", "--quiet", "--pinentry-mode", "loopback", "--passphrase-file", str(key), "--decrypt", "--output", str(out), str(src)], capture_output=True, text=True)
        if r.returncode != 0: raise RecoveryError(f"decryption FAILED (wrong recovery key or corrupt artifact, gpg rc {r.returncode})")
        plain = out.read_bytes()
    if _sha(plain) != man["plain_sha256"]: raise RecoveryError("decrypted content does not match the manifest — integrity FAILED")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(plain), mode="r") as tar:
        for m in tar.getmembers():
            if not m.isfile() or ".." in m.name or m.name.startswith("/"): continue
            files[m.name] = tar.extractfile(m).read()
    for e in man["files"]:
        if e["name"] not in files or _sha(files[e["name"]]) != e["sha256"]: raise RecoveryError(f"integrity FAILED for {e['name']}")
    return man, files

def verify(log=print):
    man, files = _decrypt(); log(f"secure verify OK: {len(files)} file(s), artifact {man['artifact_sha256'][:12]}…"); return {"ok": True, "files": sorted(files), "created_at": man["created_at"]}

def restore(force=False, log=print):
    man, files = _decrypt(); dest = home_dir(); restored, kept = [], []
    for name, data in files.items():
        p = dest / name; p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not force:
            if _sha(p.read_bytes()) == _sha(data): kept.append(name + " (identical)")
            else: kept.append(name + " (existing file differs — kept; use --force to overwrite)")
            continue
        p.write_bytes(data)
        try: os.chmod(p, 0o600)
        except OSError: pass
        restored.append(name)
    log(f"secure restore: restored {restored or 'nothing'}; kept {kept or 'nothing'}")
    return {"restored": restored, "kept": kept, "home": str(dest)}

def status():
    exp = expected_credentials(); have = {p.stem for p in scope_files()}
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    return {"artifact": ARTIFACT.exists(), "manifest": bool(man), "created_at": (man or {}).get("created_at"), "key_present": key_file().exists(), "key_path": str(key_file()),
            "local_secret_configs": sorted(have), "expected": {iid: ("CONFIGURED" if iid in have else "NOT_CONFIGURED") for iid in exp}}

def main(argv):
    cmd = argv[0] if argv else "status"
    try:
        if cmd == "backup": backup(); return 0
        if cmd == "verify": verify(); return 0
        if cmd == "restore": restore(force="--force" in argv); return 0
        if cmd == "status": print(json.dumps(status(), ensure_ascii=False, indent=1)); return 0
    except RecoveryError as e:
        print(f"⛔ {e}"); return 1
    print(__doc__); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
