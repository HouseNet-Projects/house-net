import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).parent.parent


class InstallPreflightTests(unittest.TestCase):
    def test_installer_parses(self):
        subprocess.run(["bash", "-n", "deploy/install.sh"], cwd=ROOT, check=True)

    def test_lfs_preflight_runs_before_service_install(self):
        text = (ROOT / "deploy/install.sh").read_text()
        self.assertIn("lfs pull", text)
        self.assertIn("lfs ls-files", text)
        self.assertIn("LFS pointer was not materialized", text)
        self.assertLess(text.index("preflight_lfs_inputs"), text.index("systemctl daemon-reload"))


if __name__ == "__main__":
    unittest.main()
