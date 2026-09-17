# -*- coding: utf-8 -*-
"""Hardened operational state store — SQLite (stdlib) replacing the JSONL race.

Guarantees (each covered by test_store.py):
  · safe concurrent access   — WAL + BEGIN IMMEDIATE + busy_timeout; threads AND processes
  · atomic writes            — one transaction per record; a crash mid-write leaves no partial row
  · duplicate protection     — PRIMARY KEY(op_id); the DB, not a read-then-append race, decides RECORDED vs DUPLICATE
  · crash safety             — synchronous=FULL; journal_mode=WAL
  · corruption detection     — PRAGMA quick_check on open + per-row sha256 checksum verified on read
  · deterministic recovery   — every write is journaled (append-only JSONL, written BEFORE the DB row);
                               a corrupt DB is quarantined and rebuilt by replaying the journal (idempotent by op_id)

Tables: commitments · decisions · audit · tickets (gate tickets used by the enforcement hooks) · meta
Only skill executors / engine / hooks write here. Direct edits are a governance violation (PreToolUse hook denies them).
"""
import sqlite3, json, hashlib, datetime, pathlib, os, shutil, uuid, time

HERE = pathlib.Path(__file__).resolve().parent
STATE_DIR = HERE.parent / "state"          # .claude/state (workspace contract)
SCHEMA_VERSION = 2
TABLES = {
    "commitments": "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "decisions":   "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "audit":       "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, execution_id TEXT, skill_id TEXT, result_status TEXT, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "tickets":     "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, updated_at TEXT NOT NULL, session_id TEXT, status TEXT, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    # Mission 4.2 — governed mutations (Action Runtime): one row per action, mutable state via upsert; idempotency_key/fingerprint indexed by query
    "actions":     "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, status TEXT, fingerprint TEXT, idempotency_key TEXT, session_id TEXT, batch_id TEXT, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    # Mission 5 — intelligence continuity: immutable observation checkpoints (signatures only) and mutable open loops (references only, upsert)
    "checkpoints": "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "loops":       "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    # operating layer: chat channel evidence log (LOCAL only — ids, sender refs, timestamps, short excerpts; never versioned), confirmed identity links (LOCAL), alert state (durable, upsert)
    "channel_events": "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "identities":  "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "alerts":      "op_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL",
    "meta":        "key TEXT PRIMARY KEY, value TEXT",
}

class StoreError(Exception): pass
class CorruptionError(StoreError): pass

def _now(): return datetime.datetime.now().isoformat(timespec="seconds")
def canonical(payload): return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
def checksum(payload): return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
def op_id_for(*parts):
    import re
    norm = "|".join(re.sub(r"\s+", " ", str(p).lower().strip()) for p in parts)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

class Store:
    """One Store per state directory. Connections are opened per operation (cheap; thread- and process-safe)."""
    def __init__(self, state_dir=None, *, check=True):
        self.dir = pathlib.Path(state_dir or STATE_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db = self.dir / "skill_state.db"
        self.journal = self.dir / "journal.jsonl"
        self.last_recovery = None
        self._init(check=check)

    # ───────────── connection / schema ─────────────
    def _connect(self):
        con = sqlite3.connect(str(self.db), timeout=15, isolation_level=None)   # autocommit off via explicit BEGIN
        try:
            con.execute("PRAGMA busy_timeout=15000")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
        except sqlite3.DatabaseError:
            con.close(); raise                       # never hold a handle on a corrupt file (recovery must move it)
        return con

    def _init(self, check=True):
        fresh = not self.db.exists()
        try:
            con = self._connect()
            try:
                if check and not fresh:
                    self._integrity(con)
                self._schema(con)
            finally: con.close()
        except (sqlite3.DatabaseError, CorruptionError) as e:
            self.recover(reason=f"{type(e).__name__}: {e}")
        if fresh and self.dir.resolve() == STATE_DIR.resolve(): self._migrate_legacy()      # never from a test/temp store

    def _schema(self, con):
        con.execute("BEGIN IMMEDIATE")
        for t, cols in TABLES.items(): con.execute(f"CREATE TABLE IF NOT EXISTS {t} ({cols})")
        con.execute("CREATE INDEX IF NOT EXISTS audit_exec ON audit(execution_id)")
        con.execute("CREATE INDEX IF NOT EXISTS tickets_session ON tickets(session_id, status)")
        con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('created',?)", (_now(),))
        con.execute("COMMIT")

    def _integrity(self, con):
        row = con.execute("PRAGMA quick_check").fetchone()
        if not row or row[0] != "ok": raise CorruptionError(f"quick_check: {row and row[0]}")
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "meta" in names:
            v = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if v and int(v[0]) > SCHEMA_VERSION: raise StoreError(f"db schema {v[0]} newer than code {SCHEMA_VERSION}")

    # ───────────── journal (recovery source) ─────────────
    def _journal(self, table, op_id, payload, extra=None):
        rec = {"table": table, "op_id": op_id, "ts": _now(), "payload": payload, "checksum": checksum(payload)}
        if extra: rec.update(extra)
        with self.journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n"); f.flush(); os.fsync(f.fileno())

    # ───────────── writes ─────────────
    def record(self, table, op_id, payload, *, extra_cols=None):
        """Idempotent insert. Returns {'status': RECORDED|DUPLICATE, 'op_id', 'record'}. Journal first, DB second:
        a crash between the two is healed by recovery/replay (INSERT OR IGNORE)."""
        if table not in TABLES or table == "meta": raise StoreError(f"unknown table {table}")
        payload = dict(payload); payload.setdefault("op_id", op_id); ts = _now(); payload.setdefault("recorded_at", ts)
        self._journal(table, op_id, payload, extra_cols)
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(f"SELECT payload FROM {table} WHERE op_id=?", (op_id,)).fetchone()
            if row:
                con.execute("COMMIT"); return {"status": "DUPLICATE", "op_id": op_id, "existing": json.loads(row[0])}
            cols = ["op_id", "recorded_at", "payload", "checksum"]; vals = [op_id, ts, canonical(payload), checksum(payload)]
            for k, v in (extra_cols or {}).items(): cols.append(k); vals.append(v)
            con.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals)
            con.execute("COMMIT")
        except Exception:
            try: con.execute("ROLLBACK")
            except Exception: pass
            raise
        finally: con.close()
        return {"status": "RECORDED", "op_id": op_id, "record": payload}

    def upsert(self, table, op_id, payload, *, extra_cols=None):
        """Replace-in-place for mutable rows (tickets). Journaled; atomic."""
        payload = dict(payload); payload["op_id"] = op_id; ts = _now()
        self._journal(table, op_id, payload, {"upsert": True, **(extra_cols or {})})
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            exists = con.execute(f"SELECT 1 FROM {table} WHERE op_id=?", (op_id,)).fetchone()
            cols = {"payload": canonical(payload), "checksum": checksum(payload), **(extra_cols or {})}
            if table == "tickets": cols["updated_at"] = ts
            if exists:
                con.execute(f"UPDATE {table} SET {','.join(k + '=?' for k in cols)} WHERE op_id=?", [*cols.values(), op_id])
            else:
                allc = {"op_id": op_id, "recorded_at": ts, **cols}
                if table == "tickets": allc.setdefault("updated_at", ts)
                con.execute(f"INSERT INTO {table}({','.join(allc)}) VALUES({','.join('?' * len(allc))})", list(allc.values()))
            con.execute("COMMIT")
        except Exception:
            try: con.execute("ROLLBACK")
            except Exception: pass
            raise
        finally: con.close()
        return {"status": "UPSERTED", "op_id": op_id, "record": payload}

    # ───────────── reads (checksum-verified) ─────────────
    def _rows(self, sql, args=()):
        con = self._connect()
        try: return con.execute(sql, args).fetchall()
        finally: con.close()

    def _verify(self, table, rows):
        out, corrupt = [], []
        for op_id, payload, cs in rows:
            try: p = json.loads(payload)
            except json.JSONDecodeError: corrupt.append(op_id); continue
            if checksum(p) != cs: corrupt.append(op_id); continue
            out.append(p)
        if corrupt: raise CorruptionError(f"{table}: checksum mismatch for {corrupt}")
        return out

    def get(self, table, op_id):
        rows = self._rows(f"SELECT op_id,payload,checksum FROM {table} WHERE op_id=?", (op_id,))
        r = self._verify(table, rows); return r[0] if r else None

    def list(self, table, *, where="", args=(), limit=None, order="recorded_at ASC, rowid ASC"):
        sql = f"SELECT op_id,payload,checksum FROM {table}" + (f" WHERE {where}" if where else "") + f" ORDER BY {order}"
        if limit: sql += f" LIMIT {int(limit)}"
        return self._verify(table, self._rows(sql, args))

    def count(self, table, where="", args=()):
        return self._rows(f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else ""), args)[0][0]

    def tail(self, table, n):
        rows = self._rows(f"SELECT op_id,payload,checksum FROM {table} ORDER BY rowid DESC LIMIT ?", (int(n),))
        return list(reversed(self._verify(table, rows)))

    # ───────────── integrity / recovery ─────────────
    def check(self):
        """Full verification: quick_check + every row's checksum. Returns dict; raises nothing."""
        res = {"db": str(self.db), "ok": True, "problems": []}
        try:
            con = self._connect()
            try: self._integrity(con)
            finally: con.close()
            for t in TABLES:
                if t == "meta": continue
                try: self.list(t)
                except CorruptionError as e: res["ok"] = False; res["problems"].append(str(e))
        except Exception as e:
            res["ok"] = False; res["problems"].append(f"{type(e).__name__}: {e}")
        return res

    def recover(self, reason="manual"):
        """Quarantine the current DB and rebuild deterministically from the journal (idempotent replay)."""
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine = self.dir / "quarantine"; quarantine.mkdir(exist_ok=True)
        moved = []
        for suffix in ("", "-wal", "-shm"):
            p = pathlib.Path(str(self.db) + suffix)
            if p.exists():
                dest = quarantine / f"{p.name}.corrupt_{stamp}"
                for _ in range(20):
                    try: shutil.move(str(p), str(dest)); moved.append(dest.name); break
                    except PermissionError: time.sleep(0.05)
                else:  # locked: copy then truncate
                    shutil.copy(str(p), str(dest)); p.unlink(missing_ok=True); moved.append(dest.name)
        con = self._connect()
        try: self._schema(con)
        finally: con.close()
        replayed, skipped = self._replay()
        self.last_recovery = {"at": _now(), "reason": reason, "quarantined": moved, "replayed": replayed, "skipped": skipped}
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('last_recovery',?)", (json.dumps(self.last_recovery, ensure_ascii=False),))
            con.execute("COMMIT")
        finally: con.close()
        return self.last_recovery

    def _replay(self):
        if not self.journal.exists(): return 0, 0
        replayed = skipped = 0
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            for line in self.journal.read_text(encoding="utf-8").splitlines():
                if not line.strip(): continue
                try: rec = json.loads(line)
                except json.JSONDecodeError: skipped += 1; continue          # torn tail line from a crash mid-append
                t, oid, p = rec.get("table"), rec.get("op_id"), rec.get("payload")
                if t not in TABLES or t == "meta" or not oid or not isinstance(p, dict): skipped += 1; continue
                if checksum(p) != rec.get("checksum"): skipped += 1; continue
                cs = checksum(p); ts = p.get("recorded_at") or rec.get("ts") or _now()
                extra = {k: rec[k] for k in ("execution_id", "skill_id", "result_status", "session_id", "status") if k in rec}
                if rec.get("upsert"):
                    cols = {"op_id": oid, "recorded_at": ts, "payload": canonical(p), "checksum": cs, **extra}
                    if t == "tickets": cols["updated_at"] = rec.get("ts", ts)
                    con.execute(f"INSERT OR REPLACE INTO {t}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", list(cols.values()))
                else:
                    cols = {"op_id": oid, "recorded_at": ts, "payload": canonical(p), "checksum": cs, **extra}
                    if t == "tickets": cols["updated_at"] = ts
                    con.execute(f"INSERT OR IGNORE INTO {t}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", list(cols.values()))
                replayed += 1
            con.execute("COMMIT")
        finally: con.close()
        return replayed, skipped

    # ───────────── legacy JSONL migration (one-time, deterministic) ─────────────
    def _migrate_legacy(self):
        legacy = [("commitments", self.dir / "commitments.jsonl"), ("decisions", self.dir / "decisions.jsonl"),
                  ("audit", HERE / "audit" / "skill_audit.jsonl")]
        moved = []
        for table, p in legacy:
            if not p.exists(): continue
            n = 0
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip(): continue
                try: rec = json.loads(line)
                except json.JSONDecodeError: continue
                oid = rec.get("op_id") or op_id_for(table, rec.get("execution_id", ""), rec.get("skill_id", ""), rec.get("ts", ""), n)
                extra = {"execution_id": rec.get("execution_id"), "skill_id": rec.get("skill_id"), "result_status": rec.get("result_status")} if table == "audit" else None
                try: self.record(table, oid, rec, extra_cols=extra); n += 1
                except Exception: pass
            dest = self.dir / "migrated"; dest.mkdir(exist_ok=True)
            shutil.move(str(p), str(dest / f"{p.name}.migrated_{datetime.date.today().isoformat()}")); moved.append((p.name, n))
        return moved

    def export_jsonl(self, table, path):
        path = pathlib.Path(path)
        with path.open("w", encoding="utf-8") as f:
            for r in self.list(table): f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return path

# ───────────── module-level default (state dir may be redirected by tests) ─────────────
_default = None
def get(state_dir=None):
    global _default
    d = pathlib.Path(state_dir or STATE_DIR)
    if _default is None or _default.dir != d: _default = Store(d)
    return _default

def reset():
    global _default; _default = None
