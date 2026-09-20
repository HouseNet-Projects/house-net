import json, subprocess, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RepositoryInventoryTests(unittest.TestCase):
    def test_inventory_is_complete_and_classified(self):
        data=json.loads((ROOT/'docs/governance/repository-inventory.json').read_text())
        tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')[:-1]
        self.assertEqual(data['tracked_count'],len(tracked))
        self.assertEqual(data['unknown_purpose'],[])
        self.assertEqual({x['path'] for x in data['entries']},set(tracked))
    def test_ownership_map_has_one_owner_per_concept(self):
        data=json.loads((ROOT/'docs/governance/ownership-map.json').read_text())
        self.assertTrue(data['owners'])
        self.assertEqual(len(data['owners']),len(set(data['owners'])))
        for name,artifact in data['owners'].items():
            self.assertTrue(artifact,name)
            self.assertTrue((ROOT/artifact).exists(),artifact)
    def test_check_mode_is_read_only_and_matches(self):
        import hashlib, subprocess
        target = ROOT/'docs/governance/repository-inventory.json'
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        r = subprocess.run([sys.executable, 'tools/repository_inventory.py', '--check'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertEqual(before, hashlib.sha256(target.read_bytes()).hexdigest())
