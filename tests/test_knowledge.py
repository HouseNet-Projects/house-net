import json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class KnowledgeTests(unittest.TestCase):
 def test_empty_catalog_passes(self): subprocess.check_call([str(ROOT/'bin/validate-knowledge')])
 def test_plaintext_secret_fixture_rejected(self):
  p=ROOT/'knowledge/intake'/'bad.json'; p.write_text('{"id":"HN-KNOW-BAD","title":"password=plaintextsecret","domain":"x","owner":"HOUSE_NET_OWNER","status":"draft","source":{"type":"repository","uri":"x","hash":"'+'0'*64+'"},"sensitivity":"INTERNAL","language":["en"],"last_verified":"2026-09-16"}')
  try:
   self.assertNotEqual(subprocess.run([str(ROOT/'bin/validate-knowledge')],capture_output=True).returncode,0)
  finally: p.unlink()
if __name__=='__main__': unittest.main()
