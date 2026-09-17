# -*- coding: utf-8 -*-
"""State store hardening: concurrency (threads + processes), atomicity, interruption, corruption, recovery.
All fixtures live in a temp dir; production state is never touched."""
import unittest, json, tempfile, pathlib, threading, subprocess, sys, os, sqlite3
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "skills"))
import store
from testing import covers

HERE = pathlib.Path(__file__).resolve().parent.parent / "skills"
STATE_SKILLS = ("commitment_tracking", "decision_logging", "commitment_memory", "decision_memory", "audit_logging")

def tmpdir(): return pathlib.Path(tempfile.mkdtemp(prefix="skillstore_"))

WRITER = r'''
import sys, pathlib; sys.path.insert(0, r"%s")
import store
s = store.Store(sys.argv[1]); r = s.record("commitments", sys.argv[2], {"text": sys.argv[3]})
print(r["status"])
''' % str(HERE)

INTERRUPTED = r'''
import sys, sqlite3, os, pathlib; sys.path.insert(0, r"%s")
import store
s = store.Store(sys.argv[1])
con = s._connect(); con.execute("BEGIN IMMEDIATE")
con.execute("INSERT INTO commitments(op_id,recorded_at,payload,checksum) VALUES('half','t','{}','x')")
os._exit(9)      # hard crash before COMMIT — no ROLLBACK, no close
''' % str(HERE)

class S01_Concurrency(unittest.TestCase):
    @covers(*STATE_SKILLS, kinds=("concurrency",))
    def test_threads_same_op_exactly_one_record(self):
        d = tmpdir(); s = store.Store(d); results = []
        def w(): results.append(s.record("commitments", "same", {"text": "Concurrent promise"})["status"])
        ts = [threading.Thread(target=w) for _ in range(16)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(results.count("RECORDED"), 1); self.assertEqual(results.count("DUPLICATE"), 15)
        self.assertEqual(s.count("commitments"), 1)
    @covers(*STATE_SKILLS, kinds=("concurrency",))
    def test_processes_same_op_exactly_one_record(self):
        d = tmpdir(); store.Store(d)
        procs = [subprocess.Popen([sys.executable, "-c", WRITER, str(d), "shared", "Multi-process promise"], stdout=subprocess.PIPE, text=True) for _ in range(8)]
        outs = [p.communicate()[0].strip() for p in procs]
        self.assertEqual(outs.count("RECORDED"), 1, outs); self.assertEqual(outs.count("DUPLICATE"), 7, outs)
        self.assertEqual(store.Store(d).count("commitments"), 1)
    @covers(*STATE_SKILLS, kinds=("concurrency",))
    def test_processes_distinct_ops_all_recorded(self):
        d = tmpdir(); store.Store(d)
        procs = [subprocess.Popen([sys.executable, "-c", WRITER, str(d), f"op{i}", f"promise {i}"], stdout=subprocess.PIPE, text=True) for i in range(8)]
        outs = [p.communicate()[0].strip() for p in procs]
        self.assertEqual(outs.count("RECORDED"), 8, outs); self.assertEqual(store.Store(d).count("commitments"), 8)
    @covers(*STATE_SKILLS, kinds=("concurrency",))
    def test_threads_distinct_tables_no_interference(self):
        d = tmpdir(); s = store.Store(d)
        def w(i): s.record("commitments", f"c{i}", {"text": i}); s.record("decisions", f"d{i}", {"decision": i})
        ts = [threading.Thread(target=w, args=(i,)) for i in range(20)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(s.count("commitments"), 20); self.assertEqual(s.count("decisions"), 20); self.assertTrue(s.check()["ok"])

class S02_AtomicityInterruption(unittest.TestCase):
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_crash_before_commit_leaves_no_partial_row(self):
        d = tmpdir(); s = store.Store(d); s.record("commitments", "before", {"text": "ok"})
        rc = subprocess.call([sys.executable, "-c", INTERRUPTED, str(d)])
        self.assertEqual(rc, 9)
        s2 = store.Store(d); self.assertIsNone(s2.get("commitments", "half")); self.assertIsNotNone(s2.get("commitments", "before"))
        self.assertTrue(s2.check()["ok"])
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_journal_written_but_db_row_lost_is_healed_by_recovery(self):
        d = tmpdir(); s = store.Store(d)
        s._journal("commitments", "orphan", {"text": "journaled only", "op_id": "orphan", "recorded_at": "2026-09-10T00:00:00"})
        self.assertIsNone(s.get("commitments", "orphan"))
        rec = s.recover(reason="test"); self.assertGreaterEqual(rec["replayed"], 1)
        self.assertEqual(s.get("commitments", "orphan")["text"], "journaled only")
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_torn_journal_line_is_skipped_not_fatal(self):
        d = tmpdir(); s = store.Store(d); s.record("commitments", "good", {"text": "good"})
        with s.journal.open("a", encoding="utf-8") as f: f.write('{"table":"commitments","op_id":"torn","payl')
        rec = s.recover(reason="test"); self.assertEqual(rec["skipped"], 1); self.assertEqual(s.get("commitments", "good")["text"], "good")
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_unwritable_dir_fails_loudly(self):
        d = tmpdir(); f = d / "notadir"; f.write_text("x", encoding="utf-8")
        with self.assertRaises(Exception): store.Store(f)

class S03_CorruptionDetection(unittest.TestCase):
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_garbage_db_file_detected_quarantined_recovered(self):
        d = tmpdir(); s = store.Store(d); s.record("commitments", "c1", {"text": "keep me"}); s.record("decisions", "d1", {"decision": "keep"})
        s.db.write_bytes(b"\x00garbage" * 2000)
        s2 = store.Store(d)
        self.assertIsNotNone(s2.last_recovery); self.assertTrue(any("corrupt" in q for q in s2.last_recovery["quarantined"]))
        self.assertEqual(s2.get("commitments", "c1")["text"], "keep me"); self.assertEqual(s2.count("decisions"), 1)
        self.assertTrue((d / "quarantine").exists())
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_row_tamper_detected_by_checksum(self):
        d = tmpdir(); s = store.Store(d); s.record("commitments", "c1", {"text": "original"})
        con = sqlite3.connect(str(s.db)); con.execute("UPDATE commitments SET payload='{\"text\":\"tampered\",\"op_id\":\"c1\"}' WHERE op_id='c1'"); con.commit(); con.close()
        with self.assertRaises(store.CorruptionError): s.list("commitments")
        self.assertFalse(s.check()["ok"])
        s.recover(reason="tamper"); self.assertEqual(s.get("commitments", "c1")["text"], "original")   # journal is the truth
    @covers(*STATE_SKILLS, kinds=("failure_injection",))
    def test_recovery_is_deterministic(self):
        d = tmpdir(); s = store.Store(d)
        for i in range(5): s.record("commitments", f"c{i}", {"text": f"t{i}"})
        s.record("commitments", "c2", {"text": "dup attempt"})
        a = s.list("commitments"); s.recover(reason="r1"); b = s.list("commitments"); s.recover(reason="r2"); c = s.list("commitments")
        self.assertEqual(a, b); self.assertEqual(b, c); self.assertEqual(len(c), 5)

class S04_LegacyMigration(unittest.TestCase):
    @covers("commitment_tracking", "decision_logging", kinds=("unit",))
    def test_jsonl_migrated_once_and_moved_aside(self):
        d = tmpdir()
        (d / "commitments.jsonl").write_text(json.dumps({"op_id": "legacy1", "text": "old promise"}) + "\n", encoding="utf-8")
        orig = store.STATE_DIR; store.STATE_DIR = d        # migration only ever runs for the production state dir
        try: s = store.Store(d)
        finally: store.STATE_DIR = orig
        self.assertEqual(s.get("commitments", "legacy1")["text"], "old promise")
        self.assertFalse((d / "commitments.jsonl").exists()); self.assertTrue(list((d / "migrated").glob("commitments.jsonl.migrated_*")))

if __name__ == "__main__":
    unittest.main(verbosity=2)
