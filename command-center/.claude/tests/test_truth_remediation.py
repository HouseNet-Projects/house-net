import json, pathlib, tempfile, unittest, os, sys
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path[:0]=[str(HERE),str(ROOT),str(ROOT/'.claude/integrations'),str(ROOT/'.claude/skills')]
import capabilities as cap
import registry, health
import worker

class CertificationTruthTests(unittest.TestCase):
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
