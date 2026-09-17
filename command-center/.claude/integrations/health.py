# -*- coding: utf-8 -*-
"""INTEGRATION HEALTH — per-integration status persisted in the runtime state dir (.claude/state/integrations_health.json):
AVAILABLE · DEGRADED · UNAVAILABLE · AUTH_FAILED · PERMISSION_DENIED · SCHEMA_CHANGED · NOT_CONFIGURED, with last_check,
last_success (REAL reads only), last_error (redacted), consecutive_failures, success_count and distinct success days.
Fixture reads (tests/evals) are counted separately and never become evidence of a real connection.

Concurrency (audit finding 5): every read-modify-write runs under an EXCLUSIVE cross-process file lock (msvcrt/fcntl on
<file>.lock) plus an in-process re-entrant lock, and the file is replaced atomically (tmp + os.replace). Parallel threads and
processes therefore never lose success_count / success_days / last_success. Readers retry across the replace window."""
import json, pathlib, datetime, os, sys, threading, time, contextlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import int_secrets as _secrets

_RLOCK = threading.RLock()
LOCK_TIMEOUT = 20.0

def state_dir():
    try:
        sys.path.insert(0, str(HERE.parent / "skills")); import engine
        return pathlib.Path(engine.STATE_DIR)
    except Exception:
        return pathlib.Path(os.environ.get("SKILL_STATE_DIR") or (HERE.parent / "state"))

def _path(): return state_dir() / "integrations_health.json"

def _lock_bytes(fh, mode):
    if os.name == "nt":
        import msvcrt; fh.seek(0); msvcrt.locking(fh.fileno(), mode, 1)
    else:
        import fcntl; fcntl.flock(fh.fileno(), mode)

@contextlib.contextmanager
def locked(path):
    """Exclusive lock on <path>.lock — serializes read-modify-write across threads AND processes."""
    lock = pathlib.Path(str(path) + ".lock"); lock.parent.mkdir(parents=True, exist_ok=True)
    with _RLOCK:
        fh = open(lock, "a+b")
        try:
            deadline = time.time() + LOCK_TIMEOUT
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt; _lock_bytes(fh, msvcrt.LK_NBLCK)
                    else:
                        import fcntl; _lock_bytes(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.time() > deadline: raise RuntimeError(f"lock timeout on {lock.name}")
                    time.sleep(0.005)
            try: yield
            finally:
                try:
                    if os.name == "nt":
                        import msvcrt; _lock_bytes(fh, msvcrt.LK_UNLCK)
                    else:
                        import fcntl; _lock_bytes(fh, fcntl.LOCK_UN)
                except OSError: pass
        finally: fh.close()

def read_json(p, default):
    """Read with retries across another writer's atomic replace window."""
    for i in range(20):
        try:
            if not p.exists(): return default
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.01)
    return default

def write_json_atomic(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for i in range(50):
        try: os.replace(tmp, p); return
        except PermissionError: time.sleep(0.01)
    os.replace(tmp, p)

def load(): return read_json(_path(), {})

def _blank():
    return {"status": "NOT_CONFIGURED", "last_check": None, "last_success": None, "last_success_op": None, "last_error": None, "consecutive_failures": 0,
            "success_count": 0, "success_days": [], "fixture_reads": 0, "last_fixture_success": None, "audit_failures": 0}

def update(integration_id, fn):
    """Atomic read-modify-write of one integration's health record under the exclusive lock. fn(record) mutates in place."""
    p = _path()
    with locked(p):
        d = read_json(p, {}); h = d.setdefault(integration_id, _blank())
        for k, v in _blank().items(): h.setdefault(k, v)
        fn(h); write_json_atomic(p, d)
        return dict(h)

def record(integration_id, ok, *, status="AVAILABLE", code=None, reason=None, op=None, mode="REAL"):
    now = datetime.datetime.now().isoformat(timespec="seconds"); today = now[:10]
    def mut(h):
        h["last_check"] = now; h["last_mode"] = mode
        if ok:
            h["status"] = status if status in ("AVAILABLE", "DEGRADED") else "AVAILABLE"
            if mode == "REAL":
                h["last_success"] = now; h["last_success_op"] = op; h["consecutive_failures"] = 0; h["success_count"] = h.get("success_count", 0) + 1
                if today not in h["success_days"]: h["success_days"] = (h["success_days"] + [today])[-30:]
            else:
                h["fixture_reads"] = h.get("fixture_reads", 0) + 1; h["last_fixture_success"] = now
        else:
            h["status"] = status; h["last_error"] = {"code": code, "reason": _secrets.redact(reason or "")[:300], "at": now, "op": op, "mode": mode}
            if mode == "REAL": h["consecutive_failures"] = h.get("consecutive_failures", 0) + 1
            if code == "AUDIT_UNAVAILABLE": h["audit_failures"] = h.get("audit_failures", 0) + 1
    return update(integration_id, mut)

def get(integration_id): return load().get(integration_id)

def snapshot():
    return {k: {kk: vv for kk, vv in v.items()} for k, v in load().items()}
