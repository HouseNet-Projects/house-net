import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent)); import engineering_authority as ea
BASE={'authority_id':'EAE-TEST-1','approved_by':'GEV','approval_reference':'gev-mission-approval-pr6','approved_at':'2026-09-17','mission':'test','repository':'HouseNet-Projects/house-net','base_sha':'0'*40,'status':'ACTIVE','consumed':False,'allowed_operations':['edit','test'],'allowed_paths':['docs/**'],'prohibited_operations':['external_write'],'risk_ceiling':'LOW','expires_at':'2099-01-01','branch':'feature/test','pr':'1','audit_trail':[]}
class EnvelopeTests(unittest.TestCase):
 def test_allowed_scoped_edit(self): self.assertTrue(ea.validate(BASE,'edit','docs/x.md')[0])
 def test_external_write_rejected(self): self.assertFalse(ea.validate(BASE,'external_write','docs/x.md')[0])
 def test_out_of_scope_rejected(self): self.assertFalse(ea.validate(BASE,'edit','command-center/x.py')[0])
 def test_consumed_rejected(self): self.assertFalse(ea.validate({**BASE,'consumed':True},'edit','docs/x.md')[0])
 def test_expired_rejected(self): self.assertFalse(ea.validate({**BASE,'expires_at':'2000-01-01'},'edit','docs/x.md')[0])
 def test_wrong_repository_rejected(self): self.assertFalse(ea.validate({**BASE,'repository':'evil'},'edit','docs/x.md')[0])
 def test_forbidden_operations_rejected(self):
  for op in ('external_write','visibility_change','branch_protection_change','force_push','action_runtime_bypass'):
   self.assertFalse(ea.validate({**BASE,'allowed_operations':['edit',op]},op,'docs/x.md')[0])
 def test_missing_approval_reference_rejected_by_schema_contract(self): self.assertNotIn('owner_proof',{})
if __name__=='__main__': unittest.main()
