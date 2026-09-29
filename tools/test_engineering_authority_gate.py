import os, subprocess, unittest, json
from datetime import datetime
import engineering_authority_gate as gate
ROOT=os.path.dirname(os.path.dirname(__file__))
class GateTests(unittest.TestCase):
 def test_changed_paths_comes_from_real_git_diff(self):
  expected=subprocess.check_output(['git','diff','--name-only','HEAD~1...HEAD'],cwd=ROOT,text=True).splitlines()
  self.assertEqual(gate.changed_paths('HEAD~1','HEAD'), expected)
  self.assertTrue(expected)

 def test_envelope_file_is_not_a_self_authorised_path(self):
  envelope={'status':'ACTIVE','approved_by':'GEV','repository':'HouseNet-Projects/house-net','expires_at':'2999-01-01T00:00:00Z','allowed_operations':['edit'],'allowed_paths':['.github/engineering-authority.json']}
  self.assertEqual(gate.validate(envelope,'edit','.github/engineering-authority.json'), (False, 'AUTHORITY_SELF_REFERENCE'))

 def test_current_envelope_has_no_self_path_and_short_lifetime(self):
  envelope=json.load(open(os.path.join(ROOT,'.github','engineering-authority.json')))
  self.assertNotIn('.github/engineering-authority.json', envelope.get('allowed_paths', []))
  approved=datetime.fromisoformat(envelope['approved_at'].replace('Z','+00:00'))
  expires=datetime.fromisoformat(envelope['expires_at'].replace('Z','+00:00'))
  self.assertLessEqual((expires-approved).total_seconds(), 48*60*60)

 def test_gate_requires_envelope_for_ordinary_change(self):
  env=os.environ.copy(); env.update(
   GITHUB_BASE_SHA='HEAD', GITHUB_SHA='HEAD',
   GITHUB_EVENT_NAME='pull_request',
   GITHUB_EVENT_PULL_REQUEST_NUMBER='',
   GITHUB_HEAD_REF=''
  )
  p=subprocess.run(['python3','tools/engineering_authority_gate.py'],cwd=ROOT,env=env,text=True,capture_output=True)
  self.assertNotEqual(p.returncode,0)
 def test_gate_fails_closed_for_sensitive_change_without_envelope(self):
  env=os.environ.copy(); env.update(
   GITHUB_BASE_SHA='HEAD', GITHUB_SHA='HEAD',
   GITHUB_EVENT_NAME='pull_request', GITHUB_EVENT_PULL_REQUEST_NUMBER='', GITHUB_HEAD_REF='')
  self.assertTrue(gate.is_sensitive(['.github/workflows/house-net-ci.yml']))
  self.assertFalse(gate.is_sensitive(['command-center/README.md']))
if __name__=='__main__': unittest.main()
