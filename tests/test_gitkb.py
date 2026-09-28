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

    def test_status_entries_lists_untracked_files_individually(self):
        # Untracked dirs must not be collapsed to "?? stories/": the caller
        # needs per-file paths to tell an open story from stray files (issue #45).
        story = self.kb / "stories" / "webapp" / "2026-06-05-auth"
        story.mkdir(parents=True)
        (story / "story.md").write_text("x")
        (self.kb / "INDEX.md").write_text("i")
        _run("git", "add", "INDEX.md", cwd=self.kb)
        _run("git", "commit", "-q", "-m", "i", cwd=self.kb)
        (self.kb / "INDEX.md").write_text("changed")
        self.assertEqual(
            sorted(gitkb.status_entries(self.kb)),
            [(" M", "INDEX.md"), ("??", "stories/webapp/2026-06-05-auth/story.md")],
        )

    def test_non_repo_is_graceful(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(gitkb.is_repo(d))
            self.assertFalse(gitkb.is_dirty(d))
            self.assertEqual(gitkb.status_entries(d), [])
            self.assertIn("not a git repo", gitkb.commit_kb(d, "m"))


if __name__ == "__main__":
    unittest.main()
