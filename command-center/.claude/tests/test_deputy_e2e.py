import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'certifications'))
from deputy_e2e import run_all

class DeputyE2ETests(unittest.TestCase):
    def test_all_scenarios_attempted_without_external_writes(self):
        report=run_all()
        self.assertEqual(set(report['scenarios']), {'A_sales_program','B_email_secretary','C_telegram_secretary','D_strategy_roadmap','E_cross_functional_churn','F_executive_report','G_recovery'})
        self.assertFalse(report['external_writes'])
        self.assertEqual(report['scenarios']['C_telegram_secretary']['status'], 'PASS')
        self.assertEqual(report['scenarios']['B_email_secretary']['status'], 'PASS')

if __name__ == '__main__': unittest.main()
