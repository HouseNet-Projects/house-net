"""Supervised proactive worker for the canonical Deputy watcher model."""
from __future__ import annotations
import json, os, pathlib, signal, time
ROOT=pathlib.Path(__file__).resolve().parent
for p in (ROOT/".claude"/"architecture",ROOT/".claude"/"skills",ROOT/".claude"/"integrations"): os.sys.path.insert(0,str(p))
import proactive

STOP=False
def _stop(*_):
    global STOP; STOP=True

def run_once():
    """One non-overlapping, restart-safe cycle; only PREPARE work is performed."""
    lock=proactive._st().dir / "proactive-worker.lock"
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:
        return {"status":"SKIPPED_OVERLAP"}
    try:
        result=proactive.run_cycle()
        proactive._st().upsert("checkpoints","worker:last_run",{"status":result.get("status"),"at":result.get("at"),"events":len(result.get("events",[]))})
        return {"status":"COMPLETED","events":len(result.get("events",[])),"at":result.get("at")}
    except Exception as exc:
        proactive._st().upsert("checkpoints","worker:last_run",{"status":"FAILED","error":type(exc).__name__})
        return {"status":"FAILED","error":type(exc).__name__}
    finally:
        os.close(fd)
        try: lock.unlink()
        except FileNotFoundError: pass

def status():
    r=proactive._st().get("checkpoints","worker:last_run")
    return {"installed":True,"running":False,"last_run":r}

def serve(interval=None):
    interval=int(interval or os.environ.get("DEPUTY_WORKER_INTERVAL", "900")); signal.signal(signal.SIGTERM,_stop); signal.signal(signal.SIGINT,_stop)
    while not STOP:
        run_once();
        for _ in range(interval):
            if STOP: break
            time.sleep(1)

if __name__=="__main__":
    import sys
    if "--once" in sys.argv: print(json.dumps(run_once(),ensure_ascii=False)); raise SystemExit(0)
    if "--status" in sys.argv: print(json.dumps(status(),ensure_ascii=False,default=str)); raise SystemExit(0)
    serve()
