import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from akt import drift as drift_mod
from akt.cli import main


def _git(cwd, *args, when=None):
    env = dict(os.environ)
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", "-C", str(cwd), *args], check=True, env=env,
                   capture_output=True, text=True)


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@t.test")
    _git(path, "config", "user.name", "t")


def _commit_all(path, msg, when):
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", msg, when=when)


T_OLD = "2026-10-28T12:00:00-04:00"    # sibling story written
T_MAIN = "2026-10-30T12:00:00-04:00"   # main story's last change (the anchor)
T_NEW = "2026-11-01T12:00:00-04:00"    # after the anchor


class DriftModuleTest(unittest.TestCase):
    """drift() compares each sibling's latest story and git head against the
    knowledge base's last commit time for the main story (issue #61)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.kb = root / "knowledge"
        _init_repo(self.kb)
        self.root = root / "repos"
        self.main = "stories/webapp/2026-10-26-checkout-plan"
        self._story(self.main, "checkout plan", T_OLD)
        self._story("stories/components/2026-10-28-checkout-build", "checkout build", T_OLD)
        self._story("stories/assets/2026-10-18-dependabot", "deps", T_OLD)
        self._story("stories/fresh/2026-10-31-newer-story", "newer", T_NEW)
        # the main story moves last among the OLD ones -> anchor = T_MAIN
        self._append(self.main, "## Update — 2026-10-30\n\nmain moved on\n", T_MAIN)
        # sibling repos on disk
        self.cc = self.root / "components"
        _init_repo(self.cc)
        (self.cc / "f").write_text("1")
        _commit_all(self.cc, "checkout: PR 23 merged", T_NEW)
        self.wa = self.root / "assets"
        _init_repo(self.wa)
        (self.wa / "f").write_text("1")
        _commit_all(self.wa, "deps bump", T_OLD)

    def tearDown(self):
        self.tmp.cleanup()

    def _story(self, rel, summary, when):
        d = self.kb / rel
        d.mkdir(parents=True)
        (d / "story.md").write_text(
            "---\nrepo: {}\nslug: {}\ndate: {}\nsummary: {}\nkeys: k\n---\n\n"
            "## Problem\nx\n".format(rel.split("/")[1], rel.split("/")[2][11:], rel.split("/")[2][:10], summary))
        _commit_all(self.kb, "story: " + rel, when)

    def _append(self, rel, text, when):
        f = self.kb / rel / "story.md"
        f.write_text(f.read_text() + "\n" + text)
        _commit_all(self.kb, "update: " + rel, when)

    def test_story_changed_at_uses_kb_commit_time(self):
        t = drift_mod.story_changed_at(self.kb, self.main)
        self.assertEqual(t, 1793376000)  # 2026-10-30T12:00:00-04:00

    def test_story_changed_at_falls_back_to_mtime_outside_git(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "stories/x/2026-01-01-a/story.md"
            f.parent.mkdir(parents=True)
            f.write_text("s")
            os.utime(f, (1234, 1234))
            self.assertEqual(drift_mod.story_changed_at(d, "stories/x/2026-01-01-a"), 1234)

    def test_repo_head_reads_time_sha_and_subject(self):
        head = drift_mod.repo_head(self.cc)
        self.assertEqual(head["time"], 1793548800)  # T_NEW
        self.assertEqual(head["subject"], "checkout: PR 23 merged")
        self.assertRegex(head["sha"], r"^[0-9a-f]{7,}$")

    def test_repo_head_none_when_dir_missing(self):
        self.assertIsNone(drift_mod.repo_head(self.root / "nope"))

    def test_sibling_with_old_story_and_new_head_is_stale_and_newer(self):
        # the issue's case: the components story a week behind, main moved
        rows = drift_mod.drift(self.kb, self.main, ["components"], self.root)
        row = rows[0]
        self.assertEqual(row["repo"], "components")
        self.assertEqual(row["flags"], ["newer", "stale"])
        self.assertEqual(row["story"]["path"], "stories/components/2026-10-28-checkout-build/story.md")
        self.assertEqual(row["head"]["subject"], "checkout: PR 23 merged")

    def test_sibling_with_old_story_and_old_head_is_stale_only(self):
        row = drift_mod.drift(self.kb, self.main, ["assets"], self.root)[0]
        self.assertEqual(row["flags"], ["stale"])

    def test_sibling_whose_story_moved_after_anchor_is_newer_only(self):
        fresh = self.root / "fresh"
        _init_repo(fresh)
        (fresh / "f").write_text("1")
        _commit_all(fresh, "old", T_OLD)
        row = drift_mod.drift(self.kb, self.main, ["fresh"], self.root)[0]
        self.assertEqual(row["flags"], ["newer"])

    def test_sibling_with_no_repo_dir_and_no_story_reports_both_missing(self):
        row = drift_mod.drift(self.kb, self.main, ["ghost"], self.root)[0]
        self.assertIsNone(row["head"])
        self.assertIsNone(row["story"])
        self.assertEqual(row["flags"], [])

    def test_last_update_returns_date_and_first_line(self):
        self.assertEqual(drift_mod.last_update(self.kb, self.main), ("2026-10-30", "main moved on"))
        self.assertIsNone(drift_mod.last_update(self.kb, "stories/assets/2026-10-18-dependabot"))

    def test_pointer_appends_to_stale_stories_only(self):
        rows = drift_mod.drift(self.kb, self.main, ["components", "fresh"], self.root)
        written = drift_mod.pointer(self.kb, self.main, rows, "2026-11-01")
        self.assertEqual(written, ["stories/components/2026-10-28-checkout-build/story.md"])
        text = (self.kb / "stories/components/2026-10-28-checkout-build/story.md").read_text()
        self.assertIn("## Update — 2026-11-01", text)
        self.assertIn(self.main, text)
        self.assertIn("since 2026-10-28", text)
        self.assertNotIn("pointer", (self.kb / "stories/fresh/2026-10-31-newer-story/story.md").read_text())


    def test_pointer_skips_a_story_that_already_points_at_the_main_story(self):
        # Tonight's hand-written pointers would otherwise be stacked on every wrap.
        rows = drift_mod.drift(self.kb, self.main, ["components"], self.root)
        first = drift_mod.pointer(self.kb, self.main, rows, "2026-11-01")
        self.assertEqual(len(first), 1)
        rows = drift_mod.drift(self.kb, self.main, ["components"], self.root)
        again = drift_mod.pointer(self.kb, self.main, rows, "2026-11-02")
        self.assertEqual(again, [])
        text = (self.kb / "stories/components/2026-10-28-checkout-build/story.md").read_text()
        self.assertEqual(text.count("pointer."), 1)


class DriftCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.kb = root / "knowledge"
        _init_repo(self.kb)
        self.cfg = root / "akt-config.md"
        self.cfg.write_text("knowledge_base_path: {}\n".format(self.kb))
        os.environ["AKT_CONFIG"] = str(self.cfg)
        self.repos = root / "repos"
        (self.repos / "webapp").mkdir(parents=True)
        self.main = "stories/webapp/2026-10-26-checkout-plan"
        for rel, when in ((self.main, T_OLD),
                          ("stories/components/2026-10-28-checkout-build", T_OLD)):
            d = self.kb / rel
            d.mkdir(parents=True)
            (d / "story.md").write_text(
                "---\nrepo: {}\nslug: s\ndate: {}\nsummary: sum\nkeys: k\n---\n\n## Problem\nx\n".format(
                    rel.split("/")[1], rel.split("/")[2][:10]))
            _commit_all(self.kb, "story", when)
        f = self.kb / self.main / "story.md"
        f.write_text(f.read_text() + "\n## Update — 2026-10-30\n\nmain moved on\n")
        _commit_all(self.kb, "update", T_MAIN)
        self.cc = self.repos / "components"
        _init_repo(self.cc)
        (self.cc / "f").write_text("1")
        _commit_all(self.cc, "checkout: PR 23 merged", T_NEW)
        self._cwd = os.getcwd()
        os.chdir(self.repos / "webapp")  # siblings resolve as ../<repo>

    def tearDown(self):
        os.chdir(self._cwd)
        os.environ.pop("AKT_CONFIG", None)
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_drift_prints_one_block_per_repo_with_flags(self):
        rc, out = self._run(["drift", self.main, "--repos", "components,ghost"])
        self.assertEqual(rc, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "components: newer, stale")
        self.assertIn("stories/components/2026-10-28-checkout-build/story.md", lines[1])
        self.assertIn("2026-10-28", lines[1])
        self.assertIn("checkout: PR 23 merged", lines[2])
        self.assertIn("2026-11-01", lines[2])
        self.assertEqual(lines[3], "ghost: no story, no repo at ../ghost")

    def test_drift_without_pointer_writes_nothing(self):
        before = (self.kb / "stories/components/2026-10-28-checkout-build/story.md").read_text()
        self._run(["drift", self.main, "--repos", "components"])
        self.assertEqual((self.kb / "stories/components/2026-10-28-checkout-build/story.md").read_text(), before)

    def test_drift_pointer_appends_and_commits(self):
        rc, out = self._run(["drift", self.main, "--repos", "components", "--pointer", "--date", "2026-11-01"])
        self.assertEqual(rc, 0)
        self.assertIn("pointer appended: stories/components/2026-10-28-checkout-build/story.md", out)
        text = (self.kb / "stories/components/2026-10-28-checkout-build/story.md").read_text()
        self.assertIn("## Update — 2026-11-01", text)
        self.assertIn(self.main, text)
        status = subprocess.run(["git", "-C", str(self.kb), "status", "--porcelain"],
                                capture_output=True, text=True).stdout
        self.assertEqual(status, "")

    def test_drift_truncates_a_long_update_line(self):
        f = self.kb / "stories/components/2026-10-28-checkout-build/story.md"
        f.write_text(f.read_text() + "\n## Update — 2026-10-29\n\n" + "word " * 80 + "\n")
        _commit_all(self.kb, "long", T_OLD)
        _, out = self._run(["drift", self.main, "--repos", "components"])
        story_line = out.splitlines()[1]
        self.assertLess(len(story_line), 320)
        self.assertIn("…", story_line)

    def test_drift_pointer_rejects_bad_date(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run(["drift", self.main, "--repos", "components", "--pointer", "--date", "11/01/2026"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
