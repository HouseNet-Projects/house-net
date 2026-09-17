import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest

p=Path(__file__).resolve().parents[1]/'bin/install-codex-bootstrap'
loader=importlib.machinery.SourceFileLoader('bootstrap',str(p))
spec=importlib.util.spec_from_loader(loader.name,loader)
m=importlib.util.module_from_spec(spec);loader.exec_module(m)

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='housenet-bootstrap-test-');self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/'codex';self.home.mkdir()
        self.control=Path(self.tmp.name)/'control';(self.control/'bin').mkdir(parents=True)
        (self.control/'bin/housenet-preflight').write_text('test fixture')
        self.initial='[tui]\nnotifications = true\n\n[projects."/example"]\ntrust_level = "trusted"\n'
        (self.home/'config.toml').write_text(self.initial)
        (self.home/'AGENTS.md').write_text('Existing unrelated user instruction.\n')
    def test_preserves_unrelated_and_is_idempotent(self):
        first=m.install(self.home,self.control)
        self.assertTrue(first['config_changed'])
        after=tomllib.loads((self.home/'config.toml').read_text())
        self.assertEqual(after['tui'],tomllib.loads(self.initial)['tui'])
        self.assertTrue((self.home/'AGENTS.md').read_text().startswith('Existing unrelated'))
        second=m.install(self.home,self.control)
        self.assertFalse(second['config_changed']);self.assertFalse(second['agents_changed'])
    def test_existing_override_fails_closed(self):
        (self.home/'AGENTS.override.md').write_text('unrelated policy')
        with self.assertRaises(ValueError):m.install(self.home,self.control)
        self.assertEqual((self.home/'config.toml').read_text(),self.initial)
    def test_ambiguous_block_fails_closed(self):
        (self.home/'AGENTS.md').write_text(m.BEGIN)
        with self.assertRaises(ValueError):m.install(self.home,self.control)
        self.assertEqual((self.home/'config.toml').read_text(),self.initial)
    def test_existing_developer_instructions_not_overwritten(self):
        (self.home/'config.toml').write_text('developer_instructions = "unrelated"\n'+self.initial)
        with self.assertRaises(ValueError):m.install(self.home,self.control)
