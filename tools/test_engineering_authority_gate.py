import os, subprocess, unittest
ROOT=os.path.dirname(os.path.dirname(__file__))
class GateTests(unittest.TestCase):
 def test_gate_requires_envelope_for_ordinary_change(self):
  env=os.environ.copy(); env.update(GITHUB_BASE_SHA='HEAD',GITHUB_SHA='HEAD')
  p=subprocess.run(['python3','tools/engineering_authority_gate.py'],cwd=ROOT,env=env,text=True,capture_output=True)
  self.assertNotEqual(p.returncode,0)
if __name__=='__main__': unittest.main()
