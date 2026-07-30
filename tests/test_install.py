import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from akt import install as install_mod

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS = sorted(p.name for p in (REPO_ROOT / ".claude" / "commands").glob("*.md"))


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = install_mod.install(home=self.home)
        return rc, out.getvalue(), err.getvalue()

    def test_fresh_install_creates_all_links_and_import(self):
        rc, out, _ = self._run()
        self.assertEqual(rc, 0)
        launcher = self.home / ".local" / "bin" / "akt"
        self.assertTrue(launcher.is_symlink())
        self.assertEqual(launcher.resolve(), (REPO_ROOT / "bin" / "akt").resolve())
        for name in COMMANDS:
            link = self.home / ".claude" / "commands" / name
            self.assertTrue(link.is_symlink(), name)
        rule = self.home / ".claude" / "AKT.md"
        self.assertTrue(rule.is_symlink())
        self.assertEqual(rule.resolve(), (REPO_ROOT / "claude" / "akt-rule.md").resolve())
        claude_md = (self.home / ".claude" / "CLAUDE.md").read_text()
        self.assertIn("@AKT.md", claude_md)

    def test_second_run_is_a_noop(self):
        self._run()
        before = (self.home / ".claude" / "CLAUDE.md").read_text()
        rc, out, err = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertEqual((self.home / ".claude" / "CLAUDE.md").read_text(), before)
        self.assertEqual(before.count("@AKT.md"), 1)

    def test_real_file_is_left_untouched_with_warning(self):
        rule = self.home / ".claude" / "AKT.md"
        rule.parent.mkdir(parents=True)
        rule.write_text("hand-written\n")
        rc, _, err = self._run()
        self.assertEqual(rc, 0)
        self.assertFalse(rule.is_symlink())
        self.assertEqual(rule.read_text(), "hand-written\n")
        self.assertIn("AKT.md", err)

    def test_stale_symlink_is_replaced(self):
        launcher = self.home / ".local" / "bin" / "akt"
        launcher.parent.mkdir(parents=True)
        launcher.symlink_to(self.home / "elsewhere")
        rc, _, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(launcher.resolve(), (REPO_ROOT / "bin" / "akt").resolve())

    def test_existing_import_line_is_not_duplicated(self):
        claude_md = self.home / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True)
        claude_md.write_text("# mine\n@AKT.md\n")
        self._run()
        self.assertEqual(claude_md.read_text().count("@AKT.md"), 1)


if __name__ == "__main__":
    unittest.main()
