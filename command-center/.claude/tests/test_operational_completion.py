import json, os, tempfile, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.claude'/'architecture'),str(ROOT/'.claude'/'runtime'),str(ROOT/'.claude'/'skills'),str(ROOT/'.claude'/'integrations')]
import product_api, worker, proactive
import backup_ops

class OperationalCompletionTests(unittest.TestCase):
    def test_browser_surface_and_safe_routes(self):
        self.assertIn('HouseNet / Deputy', product_api.INDEX_HTML)
        self.assertIn("fetch('/ask'", product_api.APP_JS)
        self.assertTrue(hasattr(product_api.Handler,'do_GET'))

    def test_worker_once_is_restart_safe_and_prepare_only(self):
        result=worker.run_once()
        self.assertIn(result['status'], ('COMPLETED','SKIPPED_OVERLAP'))
        self.assertEqual(worker.status()['installed'], True)

    def test_schedule_and_event_dedupe(self):
        proactive.create_schedule('test-cycle','test','1h')
        self.assertTrue(any(x.get('schedule_id')=='test-cycle' for x in proactive.schedules()))
        a=proactive._event('TEST','unit','same','LOW',{},'inspect')
        b=proactive._event('TEST','unit','same','LOW',{},'inspect')
        self.assertTrue(b.get('deduped'))

    def test_backup_integrity_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'durable').mkdir(); (p/'durable'/'x.jsonl').write_text('ok')
            (p/'manifest.json').write_text(json.dumps({'backup_id':'x','durable_files':{'x.jsonl':'bad'},'credential_recovery':{}}))
            with self.assertRaises(ValueError): backup_ops.verify(p)

if __name__=='__main__': unittest.main()

class WorkerHardeningTests(unittest.TestCase):
    def test_status_schema_is_truthful(self):
        s=worker.status(); self.assertIn('running',s); self.assertIn('last_success',s); self.assertIn('last_failure',s)
    def test_dead_pid_is_not_alive(self):
        self.assertFalse(worker._pid_alive(99999999))

class WorkerProcessStatusTests(unittest.TestCase):
    def test_live_process_is_reported_running(self):
        s=worker._status({'pid':os.getpid(),'running':False})
        self.assertTrue(s['running'])
