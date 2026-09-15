import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.validate_design_system import Invalid, validate

class DesignSystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)/'repo'
        shutil.copytree(Path(__file__).resolve().parents[1], self.root, ignore=shutil.ignore_patterns('.git','__pycache__'))
    def tearDown(self): self.tmp.cleanup()
    def test_valid_system(self): self.assertEqual(validate(self.root)['version'], '1.0.0')
    def test_invalid_color_fails(self):
        p=self.root/'tokens/brand-tokens.json'; d=json.loads(p.read_text()); d['color']['primary']['value']='#bad'; p.write_text(json.dumps(d))
        with self.assertRaisesRegex(Invalid,'Invalid color'): validate(self.root)
    def test_unknown_reference_fails(self):
        p=self.root/'tokens/document-tokens.json'; d=json.loads(p.read_text()); d['document']['body-font']['value']='{missing.token}'; p.write_text(json.dumps(d))
        with self.assertRaisesRegex(Invalid,'Unknown token'): validate(self.root)
    def test_missing_provenance_fails(self):
        (self.root/'assets/brand/original/housenet-main-logo.svg').write_text('changed')
        with self.assertRaisesRegex(Invalid,'checksum'): validate(self.root)
    def test_human_doc_requires_bilingual(self):
        p=self.root/'docs/UI-SYSTEM.md'; p.write_text('# English only\n\n## English\n\nText\n')
        with self.assertRaisesRegex(Invalid,'Armenian'): validate(self.root)

if __name__ == '__main__': unittest.main()
