import os, subprocess, unittest
ROOT=os.path.dirname(os.path.dirname(__file__))
class GateTests(unittest.TestCase):
 def test_gate_requires_envelope_for_ordinary_change(self):
  env=os.environ.copy(); env.update(
   GITHUB_BASE_SHA='HEAD', GITHUB_SHA='HEAD',
   GITHUB_EVENT_NAME='pull_request',
   GITHUB_EVENT_PULL_REQUEST_NUMBER='',
   GITHUB_HEAD_REF=''
  )
  p=subprocess.run(['python3','tools/engineering_authority_gate.py'],cwd=ROOT,env=env,text=True,capture_output=True)
  self.assertNotEqual(p.returncode,0)
if __name__=='__main__': unittest.main()
