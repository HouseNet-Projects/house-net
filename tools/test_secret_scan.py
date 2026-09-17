import unittest
from secret_scan import contains_secret
class SecretScanTests(unittest.TestCase):
 def test_path_classes_are_scanned(self):
  samples=[b'ghp_'+b'A'*32,b'AKIA'+b'A'*16,b'-----BEGIN RSA '+b'PRIVATE KEY-----',b'Authorization: Bearer '+b'A'*24,b'token: '+b'A'*40]
  for sample in samples: self.assertTrue(contains_secret(sample))
if __name__=='__main__': unittest.main()
