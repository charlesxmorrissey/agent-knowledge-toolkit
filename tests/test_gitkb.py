import subprocess
import tempfile
import unittest
from pathlib import Path

from akt import gitkb


def _run(*args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True,
                   capture_output=True, text=True)


class GitkbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        _run("git", "init", cwd=self.kb)
        _run("git", "config", "user.email", "t@t.test", cwd=self.kb)
        _run("git", "config", "user.name", "t", cwd=self.kb)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dirty_then_commit_then_clean(self):
        self.assertFalse(gitkb.is_dirty(self.kb))  # fresh repo, no changes
        (self.kb / "story.md").write_text("hi")
        self.assertTrue(gitkb.is_dirty(self.kb))
        status = gitkb.commit_kb(self.kb, "story: x/y")
        self.assertIn("committed", status)
        self.assertIn("no remote", status)  # no origin configured
        self.assertFalse(gitkb.is_dirty(self.kb))

    def test_commit_when_clean_is_noop(self):
        self.assertIn("nothing to commit", gitkb.commit_kb(self.kb, "m"))

    def test_non_repo_is_graceful(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(gitkb.is_repo(d))
            self.assertFalse(gitkb.is_dirty(d))
            self.assertIn("not a git repo", gitkb.commit_kb(d, "m"))


if __name__ == "__main__":
    unittest.main()
