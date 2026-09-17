"""Operational backup orchestration over existing state/recovery primitives."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, shutil
ROOT=pathlib.Path(__file__).resolve().parent
BACKUPS=pathlib.Path(os.environ.get("DEPUTY_BACKUP_DIR", str(ROOT/".secure"/"backups")))
import sys
sys.path.insert(0,str(ROOT/".claude"/"runtime"))

def backup(*, retention=7):
    import state_snapshot, secure_recovery
    stamp=dt.datetime.now().strftime("%Y%m%dT%H%M%S"); dest=BACKUPS/stamp; dest.mkdir(parents=True,exist_ok=False)
    state_snapshot.export(root=ROOT, log=lambda *_: None)
    durable=state_snapshot.durable_dir(ROOT); shutil.copytree(durable,dest/"durable")
    credential={"status":"NOT_RUN"}
    try: credential=secure_recovery.verify(log=lambda *_: None)
    except Exception as exc: credential={"status":"UNAVAILABLE","reason":type(exc).__name__}
    manifest={"backup_id":stamp,"created_at":dt.datetime.now().isoformat(timespec="seconds"),"durable_files":{},"credential_recovery":credential,"retention":retention}
    for p in sorted((dest/"durable").glob("*.jsonl")): manifest["durable_files"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    sets=sorted([p for p in BACKUPS.iterdir() if p.is_dir() and (p/"manifest.json").exists()])
    for old in sets[:-retention]: shutil.rmtree(old)
    return manifest

def verify(path):
    p=pathlib.Path(path); m=json.loads((p/"manifest.json").read_text(encoding="utf-8"));
    for name, digest in m["durable_files"].items():
        if hashlib.sha256((p/"durable"/name).read_bytes()).hexdigest()!=digest: raise ValueError("backup integrity failed")
    return {"ok":True,"backup_id":m["backup_id"],"files":len(m["durable_files"]),"credential_recovery":m["credential_recovery"]}

def restore_isolated(path):
    """Verify/import into a temporary state directory; never touches active state."""
    import tempfile
    import state_snapshot
    p=pathlib.Path(path); verified=verify(p)
    with tempfile.TemporaryDirectory(prefix="deputy-restore-") as td:
        target=pathlib.Path(td)/".claude"/"state"/"durable"; target.parent.mkdir(parents=True); shutil.copytree(p/"durable",target)
        result={"durable_files":len(list(target.glob("*.jsonl"))),"isolated_state_dir":str(target)}
    return {**verified,"isolated":True,"status":result}
