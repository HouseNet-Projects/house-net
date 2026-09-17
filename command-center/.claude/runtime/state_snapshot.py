# -*- coding: utf-8 -*-
"""DURABLE STATE SNAPSHOT — Deputy's durable operating memory as a deterministic, versionable export of the hardened store.

    python .claude/runtime/state_snapshot.py export      store → .claude/state/durable/{commitments,decisions,audit}.jsonl (+ observations)
    python .claude/runtime/state_snapshot.py import      .claude/state/durable → store (idempotent: INSERT OR IGNORE by op_id; no duplicates, no id reset)
    python .claude/runtime/state_snapshot.py status      row counts store vs export

DURABLE (versioned): commitments · decisions · audit (governance history) · business observations.
EPHEMERAL (never versioned): tickets, SQLite file + WAL/SHM, journal.jsonl, locks, integration cache/health.
Export lines are canonical JSON (sorted keys) ordered by (recorded_at, op_id) → identical content on every machine; the store's own
checksum/journal semantics are untouched. Secrets never live in the store (engine._redact), so the export carries none either."""
import sys, json, pathlib, os
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); import python_runtime; python_runtime.ensure()
sys.path.insert(0, str(ROOT / ".claude" / "skills"))

DURABLE_TABLES = ("commitments", "decisions", "audit", "actions", "checkpoints", "loops", "alerts")
MUTABLE_TABLES = ("actions", "loops", "alerts", "commitments", "decisions")     # rows that change state in place (upsert): the export restores the latest exported state
# LOCAL-ONLY tables (never exported): channel_events (chat evidence excerpts), identities (confirmed external identity links), tickets, meta
EXTRA_COLS = {"audit": ("execution_id", "skill_id", "result_status"), "actions": ("status", "fingerprint", "idempotency_key", "session_id", "batch_id")}

def _index_cols(t, payload):
    """Indexed columns for a durable row. Actions keep them inside the payload (state / request.*), so they are derived — idempotency must survive a restart."""
    if t == "actions":
        rq = payload.get("request") or {}
        return {"status": payload.get("state"), "fingerprint": rq.get("action_fingerprint"), "idempotency_key": rq.get("idempotency_key"), "session_id": payload.get("session_id") or "", "batch_id": payload.get("batch_id") or ""}
    return {c: payload[c] for c in EXTRA_COLS.get(t, ()) if c in payload}

def durable_dir(root=ROOT): return pathlib.Path(root) / ".claude" / "state" / "durable"

def _store():
    import engine
    return engine._store()

def _canon(row): return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

def export(root=ROOT, log=print):
    d = durable_dir(root); d.mkdir(parents=True, exist_ok=True); st = _store(); counts = {}
    for t in DURABLE_TABLES:
        rows = st.list(t)
        lines = []
        for r in rows:
            payload = dict(r); op = payload.get("op_id"); rec = {"op_id": op, "recorded_at": payload.get("recorded_at"), "payload": payload}
            rec.update({k: v for k, v in _index_cols(t, payload).items() if v is not None})
            lines.append(rec)
        lines.sort(key=lambda x: (str(x.get("recorded_at") or ""), str(x.get("op_id") or "")))
        (d / f"{t}.jsonl").write_text("".join(_canon(x) + "\n" for x in lines), encoding="utf-8", newline="\n"); counts[t] = len(lines)
    obs = pathlib.Path(root) / ".claude" / "state" / "business_observations.jsonl"
    if obs.exists(): (d / "business_observations.jsonl").write_bytes(obs.read_bytes()); counts["business_observations"] = sum(1 for l in obs.read_text(encoding="utf-8").splitlines() if l.strip())
    else:
        p = d / "business_observations.jsonl"
        if not p.exists(): p.write_text("", encoding="utf-8")
        counts["business_observations"] = sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
    log(f"durable state exported: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return counts

def import_(root=ROOT, log=print):
    """Idempotent import: every exported row is offered to the store; existing op_ids are DUPLICATE (ignored), new ones RECORDED."""
    d = durable_dir(root); st = _store(); res = {}
    for t in DURABLE_TABLES:
        p = d / f"{t}.jsonl"; new = dup = bad = 0
        if not p.exists(): res[t] = {"file": "absent"}; continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try: rec = json.loads(line)
            except ValueError: bad += 1; continue
            op = rec.get("op_id"); payload = rec.get("payload") or {}
            if not op: bad += 1; continue
            extra = {c: rec[c] for c in EXTRA_COLS.get(t, ()) if c in rec} or _index_cols(t, payload)
            if t in MUTABLE_TABLES:                                       # mutable rows: restore the exported state (later exports win by recorded_at order)
                cur = st.get(t, op)
                if cur is None: st.upsert(t, op, payload, extra_cols=extra or None); new += 1
                else: dup += 1
                continue
            r = st.record(t, op, payload, extra_cols=extra or None)
            if r["status"] == "RECORDED": new += 1
            else: dup += 1
        res[t] = {"new": new, "existing": dup, "malformed": bad}
    obs_src = d / "business_observations.jsonl"; obs_dst = pathlib.Path(root) / ".claude" / "state" / "business_observations.jsonl"
    if obs_src.exists() and obs_src.stat().st_size:
        have = set(obs_dst.read_text(encoding="utf-8").splitlines()) if obs_dst.exists() else set()
        add = [l for l in obs_src.read_text(encoding="utf-8").splitlines() if l.strip() and l not in have]
        if add:
            obs_dst.parent.mkdir(parents=True, exist_ok=True)
            with obs_dst.open("a", encoding="utf-8") as f: f.write("".join(l + "\n" for l in add))
        res["business_observations"] = {"new": len(add), "existing": len(have)}
    log("durable state imported: " + ", ".join(f"{k}={v}" for k, v in res.items()))
    return res

def status(root=ROOT):
    d = durable_dir(root); st = _store(); out = {}
    for t in DURABLE_TABLES:
        p = d / f"{t}.jsonl"; n_exp = sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip()) if p.exists() else None
        out[t] = {"store": len(st.list(t)), "export": n_exp}
    return out

def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "export": export(); return 0
    if cmd == "import": import_(); return 0
    if cmd == "status": print(json.dumps(status(), indent=1)); return 0
    print(__doc__); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
