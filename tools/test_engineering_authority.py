import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent)); import engineering_authority as ea
BASE={'authority_id':'EAE-TEST-1','approved_by':'GEV','approved_at':'2026-09-17','mission':'test','repository':'HouseNet-Projects/house-net','base_sha':'0'*40,'status':'ACTIVE','consumed':False,'allowed_operations':['edit','test'],'allowed_paths':['docs/**'],'prohibited_operations':['external_write'],'risk_ceiling':'LOW','expires_at':'2099-01-01','audit_trail':[]}
class EnvelopeTests(unittest.TestCase):
 def test_allowed_scoped_edit(self): self.assertTrue(ea.validate(BASE,'edit','docs/x.md')[0])
 def test_external_write_rejected(self): self.assertFalse(ea.validate(BASE,'external_write','docs/x.md')[0])
 def test_out_of_scope_rejected(self): self.assertFalse(ea.validate(BASE,'edit','command-center/x.py')[0])
 def test_consumed_rejected(self): self.assertFalse(ea.validate({**BASE,'consumed':True},'edit','docs/x.md')[0])
if __name__=='__main__': unittest.main()
