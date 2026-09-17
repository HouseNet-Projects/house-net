"""Supervised proactive worker using the canonical watcher/schedule model."""
from __future__ import annotations
import json, os, pathlib, signal, socket, time, datetime as dt
ROOT=pathlib.Path(__file__).resolve().parent
for p in (ROOT/'.claude/architecture',ROOT/'.claude/skills',ROOT/'.claude/integrations'): os.sys.path.insert(0,str(p))
import proactive
STOP=False

def _now(): return dt.datetime.now().isoformat(timespec='seconds')
def _lock(): return proactive._st().dir/'proactive-worker.lock'
def _pid_alive(pid):
    try:
        n=int(pid)
        if n <= 0: return False
        proc=pathlib.Path('/proc')/str(n)
        if proc.exists(): return True
        os.kill(n,0); return True
    except (ProcessLookupError,ValueError,TypeError,OSError,PermissionError): return False

def _status(row):
    r=dict(row or {}); pid=r.get('pid'); r['running']=bool(r.get('running') and pid and _pid_alive(pid)); return r

def _write_status(**kw):
    current=proactive._st().get('checkpoints','worker:status') or {}; current.update(kw); proactive._st().upsert('checkpoints','worker:status',current); return current

def run_once():
    lock=_lock(); lock.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.write(fd,json.dumps({'pid':os.getpid(),'started_at':_now(),'host':socket.gethostname()}).encode()); os.close(fd)
    except FileExistsError:
        try: info=json.loads(lock.read_text())
        except Exception: info={}
        if info.get('pid') and _pid_alive(info['pid']): return {'status':'SKIPPED_OVERLAP','running':True,'pid':info['pid']}
        try: lock.unlink()
        except FileNotFoundError: pass
        return run_once()
    _write_status(running=True,pid=os.getpid(),started_at=_now(),last_failure=None)
    try:
        result=proactive.run_cycle(); rec={'status':result.get('status'),'at':result.get('at'),'events':len(result.get('events',[]))}
        proactive._st().upsert('checkpoints','worker:last_run',rec); _write_status(running=True,last_run=rec,last_success=rec,last_failure=None)
        return {'status':'COMPLETED','events':rec['events'],'at':rec['at']}
    except Exception as exc:
        rec={'status':'FAILED','at':_now(),'error':type(exc).__name__}; proactive._st().upsert('checkpoints','worker:last_run',rec); _write_status(running=True,last_run=rec,last_failure=rec); return rec
    finally:
        _write_status(running=False,finished_at=_now())
        try: lock.unlink()
        except FileNotFoundError: pass

def status():
    s=_status(proactive._st().get('checkpoints','worker:status')); last=proactive._st().get('checkpoints','worker:last_run');
    return {'installed':True,**s,'last_run':last or s.get('last_run'),'last_success':s.get('last_success'),'last_failure':s.get('last_failure')}

def serve(interval=None):
    global STOP
    interval=int(interval or os.environ.get('DEPUTY_WORKER_INTERVAL','900')); signal.signal(signal.SIGTERM,lambda *_: globals().__setitem__('STOP',True)); signal.signal(signal.SIGINT,lambda *_: globals().__setitem__('STOP',True))
    while not STOP:
        run_once()
        for _ in range(interval):
            if STOP: break
            time.sleep(1)
if __name__=='__main__':
    import sys
    if '--once' in sys.argv: print(json.dumps(run_once(),ensure_ascii=False)); raise SystemExit(0)
    if '--status' in sys.argv: print(json.dumps(status(),ensure_ascii=False,default=str)); raise SystemExit(0)
    serve()
