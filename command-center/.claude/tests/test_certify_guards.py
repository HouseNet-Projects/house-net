import importlib
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills"))
import certify


class CertificationGuardTests(unittest.TestCase):
    def test_certification_suites_follow_test_discovery(self):
        expected = sorted(p.stem for p in HERE.glob("test_*.py") if p.is_file())
        self.assertEqual(certify.SUITES, expected)

    def test_empty_evaluations_are_not_a_pass(self):
        self.assertFalse(certify.evaluations_pass({}))
        self.assertFalse(certify.evaluations_pass({"scenarios": []}))
        self.assertFalse(certify.evaluations_pass({"scenarios": [{"pass": False}]}))
        self.assertTrue(certify.evaluations_pass({"scenarios": [{"pass": True}]}))


if __name__ == "__main__":
    unittest.main()
