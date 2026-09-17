import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
def copyroot():
 d=Path(tempfile.mkdtemp());
 for name in ['bin','knowledge','schemas']:
  shutil.copytree(ROOT/name,d/name)
 return d
class KnowledgeTests(unittest.TestCase):
 def test_empty_catalog_passes(self): subprocess.check_call([str(ROOT/'bin/validate-knowledge')])
 def test_schema_rejects_unknown_property(self):
  d=copyroot(); p=d/'knowledge/intake/bad.json'; p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'id':'HN-KNOW-BAD','title':'x','domain':'x','owner':'HOUSE_NET_OWNER','status':'draft','source':{'type':'repository','uri':'x','hash':'0'*64},'sensitivity':'INTERNAL','language':['en'],'last_verified':'2026-09-16','extra':1})); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-knowledge'),'--root',str(d)]).returncode,0)
 def test_bad_date_rejected(self):
  d=copyroot(); p=d/'knowledge/intake/bad.json'; p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'id':'HN-KNOW-BAD','title':'x','domain':'x','owner':'HOUSE_NET_OWNER','status':'draft','source':{'type':'repository','uri':'x','hash':'0'*64},'sensitivity':'INTERNAL','language':['en'],'last_verified':'not-date'})); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-knowledge'),'--root',str(d)]).returncode,0)
 def test_secret_rejected(self):
  d=copyroot(); p=d/'knowledge/intake/bad.json'; p.parent.mkdir(exist_ok=True); p.write_text('{"password":"synthetic-secret-value"}'); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-knowledge'),'--root',str(d)]).returncode,0)
 def test_unknown_supersession_rejected(self):
  d=copyroot(); p=d/'knowledge/intake/bad.json'; p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'id':'HN-KNOW-BAD','title':'x','domain':'x','owner':'HOUSE_NET_OWNER','status':'draft','source':{'type':'repository','uri':'x','hash':'0'*64},'sensitivity':'INTERNAL','language':['en'],'last_verified':'2026-09-16','supersedes':'HN-KNOW-MISSING'})); (d/'knowledge/index/catalog.json').write_text('{"version":1,"generated":true,"items":[{"id":"HN-KNOW-BAD"}]}'); self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-knowledge'),'--root',str(d)]).returncode,0)
if __name__=='__main__': unittest.main()
