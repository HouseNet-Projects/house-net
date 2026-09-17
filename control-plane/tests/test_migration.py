import json, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'bin/housenet-import'

class MigrationTests(unittest.TestCase):
    def run_tool(self, command, evidence=None):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'source'; source.mkdir()
            if evidence is None:
                result = subprocess.run([str(TOOL), command, str(source)], text=True, capture_output=True)
            else:
                path = Path(td) / 'evidence.json'; path.write_text(json.dumps(evidence))
                result = subprocess.run([str(TOOL), command, '--input', str(path)], text=True, capture_output=True)
            return result
    def test_clean_source_passes_discovery(self):
        self.assertEqual(self.run_tool('inspect').returncode, 0)
    def test_secret_blocks_validation(self):
        result = self.run_tool('validate', {'stage':'AUDITED','secret_findings':['.env']})
        self.assertNotEqual(result.returncode, 0); self.assertIn('SECRET FINDINGS', result.stdout)
    def test_conflicting_sources_block(self):
        result = self.run_tool('validate', {'stage':'PROPOSED','source_candidates':['a','b']})
        self.assertNotEqual(result.returncode, 0); self.assertIn('CONFLICTING', result.stdout)
    def test_certified_requires_approval(self):
        result = self.run_tool('certify', {'stage':'CERTIFIED','approval_state':'pending'})
        self.assertNotEqual(result.returncode, 0)
    def test_valid_certification_passes(self):
        result = self.run_tool('certify', {'stage':'CERTIFIED','approval_state':'approved','secret_findings':[]})
        self.assertEqual(result.returncode, 0)

if __name__ == '__main__': unittest.main()
