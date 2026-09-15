import subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class VaultTests(unittest.TestCase):
 def test_safe_fixture_passes(self): subprocess.check_call([str(ROOT/'bin/validate-vault')])
 def test_plaintext_fixture_fails(self):
  p=ROOT/'vault/references'/'bad.json'; p.write_text('{"password":"plaintext-secret-value"}')
  subprocess.run(['git','add','-N',str(p)],cwd=ROOT,check=True)
  try: self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-vault')],capture_output=True).returncode,0)
  finally:
   subprocess.run(['git','reset','--',str(p)],cwd=ROOT,stdout=subprocess.DEVNULL); p.unlink()
if __name__=='__main__': unittest.main()
