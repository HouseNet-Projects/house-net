import io
import unittest
import zipfile
from secret_scan import contains_secret, archive_findings
class SecretScanTests(unittest.TestCase):
 def test_path_classes_are_scanned(self):
  samples=[b'ghp_'+b'A'*32,b'AKIA'+b'A'*16,b'-----BEGIN RSA '+b'PRIVATE KEY-----',b'Authorization: Bearer '+b'A'*24,b'token: '+b'A'*40]
  for sample in samples: self.assertTrue(contains_secret(sample))

 def test_office_zip_payload_is_scanned_without_unbounded_extraction(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('word/document.xml', b'<w:t>Authorization: Bearer '+b'A'*24+b'</w:t>')
  self.assertTrue(archive_findings('synthetic.docx',buf.getvalue()))

 def test_non_zip_binary_is_not_treated_as_archive(self):
  self.assertFalse(archive_findings('synthetic.docx', b'not a zip'))
if __name__=='__main__': unittest.main()
