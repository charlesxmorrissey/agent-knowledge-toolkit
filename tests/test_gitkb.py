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


class RepoRootTest(unittest.TestCase):
    """issue #73: the repo name and the sibling root came from the worktree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.main = Path(self.tmp.name).resolve() / "webapp"
        self.main.mkdir()
        _run("git", "init", "-q", cwd=self.main)
        _run("git", "config", "user.email", "t@t.test", cwd=self.main)
        _run("git", "config", "user.name", "t", cwd=self.main)
        _run("git", "commit", "-q", "--allow-empty", "-m", "init", cwd=self.main)
        self.wt = self.main / ".claude" / "worktrees" / "fix-foo"
        _run("git", "worktree", "add", "-q", str(self.wt), "-b", "fix-foo", cwd=self.main)

    def tearDown(self):
        self.tmp.cleanup()

    def test_main_checkout(self):
        self.assertEqual(gitkb.repo_root(self.main), self.main)

    def test_subdirectory_of_main_checkout(self):
        sub = self.main / "src" / "deep"
        sub.mkdir(parents=True)
        self.assertEqual(gitkb.repo_root(sub), self.main)

    def test_worktree_names_the_main_checkout(self):
        self.assertEqual(gitkb.repo_root(self.wt), self.main)
        self.assertEqual(gitkb.repo_root(self.wt).name, "webapp")

    def test_subdirectory_of_worktree(self):
        sub = self.wt / "src"
        sub.mkdir()
        self.assertEqual(gitkb.repo_root(sub), self.main)

    def test_outside_a_repo_is_none(self):
        plain = Path(self.tmp.name).resolve() / "plain"
        plain.mkdir()
        self.assertIsNone(gitkb.repo_root(plain))
