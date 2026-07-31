import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from akt import config
from akt.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name) / "knowledge"
        self.cfg = Path(self.tmp.name) / "akt-config.md"
        import os
        os.environ["AKT_CONFIG"] = str(self.cfg)

    def tearDown(self):
        import os
        os.environ.pop("AKT_CONFIG", None)
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue().strip()

    def test_init_and_start_and_reindex(self):
        rc, _ = self._run(["init", str(self.kb)])
        self.assertEqual(rc, 0)
        self.assertEqual(config.get("knowledge_base_path", self.cfg), str(self.kb))

        rc, out = self._run(["start-story", "webapp", "Auth Token Refresh", "--date", "2026-06-05"])
        self.assertEqual(rc, 0)
        self.assertTrue(Path(out).joinpath("story.md").exists())

        rc, out = self._run(["reindex"])
        self.assertEqual(rc, 0)
        self.assertIn("indexed", out)

    def _seed_story(self, date="2026-06-05", slug="auth", summary="token refresh"):
        story = self.kb / "stories" / "webapp" / "{}-{}".format(date, slug)
        story.mkdir(parents=True)
        (story / "story.md").write_text(
            "---\nrepo: webapp\nslug: {}\nsummary: {}\nkeys: auth, token\n---\n## Problem\n".format(slug, summary)
        )
        return story

    def test_recall_prints_paths_with_summaries(self):
        self._run(["init", str(self.kb)])
        self._seed_story()
        self._run(["reindex"])
        rc, out = self._run(["recall", "token auth"])
        self.assertEqual(rc, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "stories/webapp/2026-06-05-auth/story.md")
        self.assertEqual(lines[1], "    token refresh")

    def test_latest_prints_newest_story_for_repo(self):
        self._run(["init", str(self.kb)])
        self._seed_story(date="2026-06-05", slug="auth")
        self._seed_story(date="2026-07-01", slug="newer", summary="newer work")
        self._run(["reindex"])
        rc, out = self._run(["latest", "webapp"])
        self.assertEqual(rc, 0)
        self.assertIn("stories/webapp/2026-07-01-newer/story.md", out)
        rc, out = self._run(["latest", "nope"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def _run_stdin(self, argv, text):
        import io as _io
        import sys as _sys
        _sys.stdin = _io.StringIO(text)
        try:
            return self._run(argv)
        finally:
            _sys.stdin = _sys.__stdin__

    def test_update_story_resolves_kb_relative_path(self):
        self._run(["init", str(self.kb)])
        story = self._seed_story()
        rc, _ = self._run_stdin(
            ["update-story", "stories/webapp/2026-06-05-auth", "--stdin", "--date", "2026-06-06"],
            "KB-relative update.\n",
        )
        self.assertEqual(rc, 0)
        self.assertIn("KB-relative update.", (story / "story.md").read_text())

    def test_update_story_accepts_recall_style_story_md_path(self):
        self._run(["init", str(self.kb)])
        story = self._seed_story()
        rc, _ = self._run_stdin(
            ["update-story", "stories/webapp/2026-06-05-auth/story.md", "--stdin", "--date", "2026-06-06"],
            "Recall-style path update.\n",
        )
        self.assertEqual(rc, 0)
        self.assertIn("Recall-style path update.", (story / "story.md").read_text())

    def test_finish_story_resolves_kb_relative_path(self):
        self._run(["init", str(self.kb)])
        story = self._seed_story()
        body = (
            "---\nrepo: webapp\nslug: auth\ndate: 2026-06-05\nsummary: token refresh\nkeys: auth\n---\n"
            "## Problem\nx\n## Decisions\nx\n## Outcome\nx\n"
        )
        rc, out = self._run_stdin(
            ["finish-story", "stories/webapp/2026-06-05-auth", "--stdin"], body
        )
        self.assertEqual(rc, 0)
        self.assertIn("token refresh", (story / "story.md").read_text())

    def test_missing_story_path_exits_cleanly(self):
        self._run(["init", str(self.kb)])
        with self.assertRaises(SystemExit) as cm:
            self._run_stdin(["update-story", "stories/nope/2026-01-01-gone", "--stdin"], "x\n")
        self.assertEqual(cm.exception.code, 2)

    def test_update_story_appends_from_stdin(self):
        import io as _io
        import sys as _sys
        self._run(["init", str(self.kb)])
        story = self._seed_story()
        _sys.stdin = _io.StringIO("Rotated the refresh tokens.\n")
        try:
            rc, out = self._run(["update-story", str(story), "--stdin", "--date", "2026-06-06"])
        finally:
            _sys.stdin = _sys.__stdin__
        self.assertEqual(rc, 0)
        text = (story / "story.md").read_text()
        self.assertIn("## Update — 2026-06-06", text)
        self.assertIn("Rotated the refresh tokens.", text)

    def test_learn_add_reinforce_propose_graduate(self):
        self._run(["init", str(self.kb)])
        rc, out = self._run(["learn", "add", "cm6-paste", "Verify bundle bytes after paste",
                             "--story", "heyflow/2026-07-01-a"])
        self.assertEqual(rc, 0)
        self.assertIn("hits: 1", out)

        rc, out = self._run(["learn", "reinforce", "cm6-paste", "--story", "sumo/2026-07-02-b"])
        self.assertEqual(rc, 0)
        self.assertNotIn("PROPOSE:", out)

        rc, out = self._run(["learn", "reinforce", "cm6-paste", "--story", "webapp/2026-07-03-c"])
        self.assertEqual(rc, 0)
        self.assertIn("PROPOSE: graduate 'cm6-paste' as GLOBAL", out)

        rc, out = self._run(["learn", "graduate", "cm6-paste"])
        self.assertEqual(rc, 0)
        self.assertIn("<!-- akt: cm6-paste", out)
        self.assertIn("- Verify bundle bytes after paste", (self.kb / "AGENTS.md").read_text())

    def test_learn_list_filters_by_status(self):
        self._run(["init", str(self.kb)])
        self._run(["learn", "add", "a", "Rule A", "--story", "x/2026-07-01-a"])
        self._run(["learn", "add", "b", "Rule B", "--story", "y/2026-07-01-b"])
        self._run(["learn", "wont", "b"])
        rc, out = self._run(["learn", "list", "--status", "candidate"])
        self.assertEqual(rc, 0)
        self.assertIn("[a]", out)
        self.assertNotIn("[b]", out)

    def test_learn_add_invalid_date_exits_2_and_no_write(self):
        self._run(["init", str(self.kb)])
        with self.assertRaises(SystemExit) as ctx:
            self._run(["learn", "add", "x", "Rule", "--story", "a/2026-07-01-b",
                       "--date", "07/30/2026"])
        self.assertEqual(ctx.exception.code, 2)
        ledger = self.kb / "LEARNINGS.md"
        if ledger.exists():
            self.assertNotIn("x", ledger.read_text())

    def test_learn_unknown_id_exits_2(self):
        self._run(["init", str(self.kb)])
        with self.assertRaises(SystemExit) as ctx:
            self._run(["learn", "graduate", "nope"])
        self.assertEqual(ctx.exception.code, 2)

    def test_learn_prune_prints_sections(self):
        self._run(["init", str(self.kb)])
        self._run(["learn", "add", "old", "Old rule", "--story", "x/2026-01-01-a",
                   "--date", "2026-01-01"])
        rc, out = self._run(["learn", "prune"])
        self.assertEqual(rc, 0)
        self.assertIn("stale candidates", out)
        self.assertIn("[old]", out)


if __name__ == "__main__":
    unittest.main()
