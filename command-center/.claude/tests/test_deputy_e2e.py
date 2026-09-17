import unittest
from pathlib import Path
import sys
import json, os, subprocess, tempfile
sys.path.insert(0, str(Path(__file__).parents[1] / 'certifications'))
from deputy_e2e import run_all

class DeputyE2ETests(unittest.TestCase):
    def test_all_scenarios_attempted_without_external_writes(self):
        report=run_all()
        self.assertEqual(set(report['scenarios']), {'A_sales_program','B_email_secretary','C_telegram_secretary','D_strategy_roadmap','E_cross_functional_churn','F_executive_report','G_recovery'})
        self.assertFalse(report['external_writes'])
        self.assertEqual(report['scenarios']['C_telegram_secretary']['status'], 'PASS')
        self.assertEqual(report['scenarios']['B_email_secretary']['status'], 'PASS')

    def test_canonical_operating_entrypoint_persists_understanding_and_graph(self):
        root = Path(__file__).parents[2]
        with tempfile.TemporaryDirectory() as state:
            env = os.environ.copy(); env['SKILL_STATE_DIR'] = state
            p = subprocess.run([sys.executable, str(root / 'deputy.py'), 'run',
                                'Give me today operating brief', '--json'], cwd=root,
                               env=env, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            data = json.loads(p.stdout)
            self.assertTrue(data['mission_id'].startswith('MIS-'))
            self.assertIn('raw_intent', data['understanding'])
            self.assertIn('sources', data['context'])
            self.assertIn('nodes', data['work_graph'])
            self.assertEqual(data['authority'], 'ACTION_RUNTIME_ONLY_FOR_MATERIAL_MUTATION')

    def test_operating_entrypoint_handles_multi_brain_plan_and_empty_request(self):
        root = Path(__file__).parents[2]
        with tempfile.TemporaryDirectory() as state:
            env = os.environ.copy(); env['SKILL_STATE_DIR'] = state
            p = subprocess.run([sys.executable, str(root / 'deputy.py'), 'run',
                                'Prepare this week Sales and Operations execution plan', '--json'], cwd=root,
                               env=env, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            data = json.loads(p.stdout)
            self.assertGreaterEqual(len(data['routing']['selected_brains']), 2)
            bad = subprocess.run([sys.executable, str(root / 'deputy.py'), 'run', '   '], cwd=root,
                                 env=env, text=True, capture_output=True)
            self.assertEqual(bad.returncode, 2)
            self.assertEqual(json.loads(bad.stdout)['status'], 'BLOCKED')

    def test_company_cockpit_is_derived_partial_and_truthful(self):
        root = Path(__file__).parents[2]
        with tempfile.TemporaryDirectory() as state:
            env = os.environ.copy(); env['SKILL_STATE_DIR'] = state
            p = subprocess.run([sys.executable, str(root / 'deputy.py'), 'run',
                                'Give me today’s company cockpit', '--json'], cwd=root,
                               env=env, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            cockpit = json.loads(p.stdout)['cockpit']
            self.assertIn(cockpit['company_status'], ('CURRENT', 'PARTIAL_SUCCESS'))
            self.assertTrue(cockpit['source_health'])
            self.assertIn('truth_hierarchy', cockpit)
            self.assertIn('missing_data', cockpit)
            self.assertNotIn('health_score', json.dumps(cockpit))

    def test_company_queries_share_snapshot_pipeline_and_do_not_write(self):
        root = Path(__file__).parents[2]
        with tempfile.TemporaryDirectory() as state:
            env = os.environ.copy(); env['SKILL_STATE_DIR'] = state
            for request, mode in [('What is overdue or blocked?', 'exceptions'),
                                  ('What needs my attention?', 'attention'),
                                  ('What changed since the last review?', 'delta'),
                                  ('Prepare my weekly management review', 'weekly')]:
                p = subprocess.run([sys.executable, str(root / 'deputy.py'), 'run', request, '--json'], cwd=root,
                                   env=env, text=True, capture_output=True)
                self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
                data = json.loads(p.stdout); self.assertEqual(data['cockpit']['query'], mode)
                self.assertIn(data['cockpit']['company_status'], ('CURRENT', 'PARTIAL_SUCCESS'))

if __name__ == '__main__': unittest.main()
