import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
def copyroot():
 d=Path(tempfile.mkdtemp());
 for name in ['bin','vault','schemas']:
  shutil.copytree(ROOT/name,d/name)
 subprocess.run(['git','init','-q'],cwd=d,check=True); subprocess.run(['git','config','user.email','test@example.invalid'],cwd=d); subprocess.run(['git','config','user.name','Test'],cwd=d); subprocess.run(['git','add','.'],cwd=d,check=True); subprocess.run(['git','commit','-qm','base'],cwd=d,check=True); return d
class VaultTests(unittest.TestCase):
 def test_safe_fixture_passes(self): subprocess.check_call([str(ROOT/'bin/validate-vault')])
 def test_plaintext_current_tree_fails(self):
  d=copyroot(); p=d/'vault/references/bad.json'; p.write_text(json.dumps({'pass'+'word':'synthetic-secret-value'})); subprocess.run(['git','add','.'],cwd=d,check=True); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-vault'),'--root',str(d)]).returncode,0)
 def test_history_secret_fails(self):
  d=copyroot(); p=d/'vault/references/old.txt'; p.write_text('-----BEGIN '+"RSA PRIVATE"+' KEY-----'); subprocess.run(['git','add','.'],cwd=d,check=True); subprocess.run(['git','commit','-qm','bad fixture'],cwd=d,check=True); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-vault'),'--root',str(d)]).returncode,0)
 def test_unsafe_reference_fails(self):
  d=copyroot(); p=d/'vault/references/example-recovery-reference.json'; x=json.loads(p.read_text()); x['storage']['reference']='value://plaintext'; p.write_text(json.dumps(x)); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-vault'),'--root',str(d)]).returncode,0)
 def test_bootstrap_requires_recovery(self):
  d=copyroot(); p=d/'vault/references/example-recovery-reference.json'; x=json.loads(p.read_text()); x['required_for_bootstrap']=True; p.write_text(json.dumps(x)); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-vault'),'--root',str(d)]).returncode,0)
if __name__=='__main__': unittest.main()
