import json, pathlib, tempfile, unittest, os, sys
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path[:0]=[str(HERE),str(ROOT),str(ROOT/'.claude/integrations'),str(ROOT/'.claude/skills')]
import capabilities as cap
import registry, health
import worker

class CertificationTruthTests(unittest.TestCase):
    def test_durable_write_certificates_have_split_historical_and_current_state(self):
        records = cap._write_certs()
        self.assertTrue(records)
        for iid, operations in records.items():
            for op, record in operations.items():
                self.assertIn("certified_once", record, (iid, op))
                self.assertIn("executable_now", record, (iid, op))
                self.assertTrue(record["certified_once"].get("action_id"), (iid, op))
                self.assertIn(record["executable_now"].get("state"), {"AVAILABLE", "NOT_EXECUTABLE", "UNKNOWN"})

    def test_record_write_certification_does_not_overwrite_history(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "certs.json"; old = cap.WRITE_CERTS
            try:
                cap.WRITE_CERTS = p
                original = {"action_id": "ACT-original", "verified_at": "2026-01-01", "evidence": {"approved_by": "Gev"}, "provider": "INT-TASKS", "operation": "tasks.create", "executor": "adapter_tasks_write", "platform": "Linux", "runtime_requirements": None, "implementation_sha256": None}
                p.write_text(json.dumps({"INT-TASKS": {"tasks.create": {"certified_once": original, "executable_now": {"state": "UNKNOWN"}}}}))
                result = cap.record_write_certification("INT-TASKS", "tasks.create", "ACT-new", {"approved_by": "Gev"})
                self.assertEqual(result["certified_once"]["action_id"], "ACT-original")
            finally:
                cap.WRITE_CERTS = old

    def test_product_documents_do_not_claim_live_write_without_certificate(self):
        docs = [ROOT.parent / "docs" / name for name in ("DEPUTY_CAPABILITY_MATRIX.md", "DEPUTY_PRODUCT_BIBLE.md", "DEPUTY_PRODUCT_MAP.md", "DEPUTY_PRODUCT_ONE_PAGE.md")]
        records = cap._write_certs()
        certified = {(iid, op) for iid, ops in records.items() for op, item in ops.items() if item.get("certified_once")}
        for path in docs:
            self.assertTrue(path.exists(), path)
            for line in path.read_text(encoding="utf-8").splitlines():
                if "**CONFIRMED / LIVE**" in line and any(word in line.lower() for word in ("write", "send", "update", "create")):
                    self.assertTrue(certified, f"{path}: live write claim has no certified_once evidence")
    def test_outlook_windows_executor_is_not_executable_on_linux(self):
        with patch.object(cap.platform, 'system', return_value='Linux'):
            r=cap.capability('INT-OL-MAIL','mail.send')
        self.assertFalse(r['current_host_executable'])
        self.assertEqual(r['level'],'NOT_EXECUTABLE')
        self.assertFalse(r['runtime_available'])

    def test_historical_certificate_without_provenance_is_not_current_certification(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'certs.json'; old=cap.WRITE_CERTS
            try:
                cap.WRITE_CERTS=p; p.write_text(json.dumps({'INT-TASKS':{'tasks.create':{'action_id':'old','verified_at':'2026-01-01'}}}))
                with patch.object(cap.health, 'get', return_value={'status':'AVAILABLE','last_success':'2026-09-21'}), patch.object(cap._secrets, 'load_config', return_value={}):
                    r=cap.capability('INT-TASKS','tasks.create')
                self.assertEqual(r['level'],'CONNECTED'); self.assertFalse(r['certification_provenance_valid'])
            finally: cap.WRITE_CERTS=old

    def test_worker_truth_is_structured_and_not_constant(self):
        with tempfile.TemporaryDirectory() as d:
            missing=pathlib.Path(d)/'missing.service'
            with patch.dict(os.environ, {'DEPUTY_WORKER_UNIT': str(missing)}, clear=False):
                absent=worker._installation_truth()
            self.assertFalse(absent['supervisor_present'])
            self.assertFalse(absent['installed'])
            present_path=pathlib.Path(d)/'deputy-worker.service'; present_path.write_text('[Unit]\n')
            with patch.dict(os.environ, {'DEPUTY_WORKER_UNIT': str(present_path)}, clear=False):
                present=worker._installation_truth()
            self.assertTrue(present['supervisor_present'])
            self.assertTrue(present['installed'])
            self.assertEqual(present['installed'], present['runtime_available'])
        source=pathlib.Path(worker.__file__).read_text(encoding='utf-8')
        self.assertNotIn("'installed':runtime", source)

    def test_active_product_language_is_role_based(self):
        product = (ROOT / 'product_api.py').read_text(encoding='utf-8')
        self.assertNotRegex(product, r'Gev|Գև')

if __name__=='__main__': unittest.main()
