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
        r=worker._installation_truth()
        self.assertIn('runtime_available',r); self.assertIn('supervisor_present',r); self.assertEqual(r['installed'],r['runtime_available'])
        self.assertNotIn("'installed':True", open(worker.__file__,encoding='utf-8').read())

    def test_active_product_language_is_role_based(self):
        product = (ROOT / 'product_api.py').read_text(encoding='utf-8')
        for forbidden in ('Gev Attention', 'Needs Gev', 'Waiting for Gev', 'Rejected by Gev', 'Գևի ուշադրություն', 'Պահանջում է Գևի ուշադրությունը'):
            self.assertNotIn(forbidden, product)

if __name__=='__main__': unittest.main()
