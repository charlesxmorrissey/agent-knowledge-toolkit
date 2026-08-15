import tempfile
import unittest
from pathlib import Path

from akt.frontmatter import parse_frontmatter
from akt.index import read_index_lines, parse_index_line
from akt.story import start_story, end_session, finish_story, update_story


class StoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        (self.kb / "stories").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_story_scaffolds(self):
        d = start_story(self.kb, "webapp", "Auth Token Refresh", "2026-06-05")
        self.assertTrue((d / "story.md").exists())
        # sessions/ exists but holds NO placeholder — handoffs are created by end_session
        self.assertTrue((d / "sessions").is_dir())
        self.assertFalse((d / "sessions" / "01.md").exists())
        meta, _ = parse_frontmatter((d / "story.md").read_text())
        self.assertEqual(meta["repo"], "webapp")
        self.assertEqual(meta["slug"], "auth-token-refresh")
        self.assertEqual(meta["date"], "2026-06-05")

    def test_start_story_rejects_duplicate(self):
        start_story(self.kb, "webapp", "Auth Token Refresh", "2026-06-05")
        with self.assertRaises(FileExistsError):
            start_story(self.kb, "webapp", "Auth Token Refresh", "2026-06-05")

    def test_end_session_numbers_sequentially(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        # First handoff is 01.md (no placeholder pre-exists), next is 02.md
        f1 = end_session(d, "State: first\n")
        self.assertEqual(f1.name, "01.md")
        self.assertIn("first", f1.read_text())
        f2 = end_session(d, "State: midway\nDone: x\nNext: y\nWatch out: z\n")
        self.assertEqual(f2.name, "02.md")
        self.assertIn("midway", f2.read_text())

    def test_finish_story_writes_body_and_indexes(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        body = (
            "---\nrepo: webapp\nslug: auth\ndate: 2026-06-05\n"
            "summary: Lazy refresh on 401\nkeys: auth, token\n---\n"
            "## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n## Links\n"
        )
        line = finish_story(self.kb, d, body)
        self.assertIn("[webapp/auth]", line)
        lines = read_index_lines(self.kb)
        self.assertEqual(len(lines), 1)
        self.assertEqual(parse_index_line(lines[0])["summary"], "Lazy refresh on 401")

    def test_update_story_appends_dated_section(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        # Initialize the story with required frontmatter before updating
        story_md = d / "story.md"
        story_md.write_text(
            "---\nrepo: webapp\nslug: auth\ndate: 2026-06-05\n"
            "summary: Lazy refresh on 401\nkeys: auth, token\n---\n"
            "## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n"
        )
        f = update_story(d, "Switched to rotating refresh tokens.\n", "2026-06-06")
        text = f.read_text()
        self.assertIn("## Update — 2026-06-06", text)
        self.assertTrue(text.endswith("Switched to rotating refresh tokens.\n"))

    def test_update_story_rejects_missing_story_and_empty_body(self):
        with self.assertRaises(FileNotFoundError):
            update_story(self.kb / "stories" / "nope", "body", "2026-06-06")
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        with self.assertRaises(ValueError):
            update_story(d, "  \n", "2026-06-06")

    def test_finish_story_rejects_missing_sections(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        bad = "---\nrepo: webapp\nslug: auth\nsummary: s\nkeys: k\n---\n## Problem\nonly\n"
        with self.assertRaises(ValueError):
            finish_story(self.kb, d, bad)

    def test_finish_story_rejects_empty_summary(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        bad = "---\nrepo: webapp\nslug: auth\nsummary:\nkeys: k\n---\n## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n"
        with self.assertRaises(ValueError):
            finish_story(self.kb, d, bad)

    def test_finish_story_rejects_empty_repo_slug_keys(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        for missing in ("repo", "slug", "keys"):
            meta = {"repo": "webapp", "slug": "auth", "date": "2026-06-05",
                    "summary": "s", "keys": "a, b"}
            meta[missing] = ""
            bad = (
                "---\n" + "\n".join("{}: {}".format(k, v) for k, v in meta.items()) + "\n---\n"
                "## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n"
            )
            with self.assertRaises(ValueError, msg=missing):
                finish_story(self.kb, d, bad)

    def test_update_story_accepts_fresh_skeleton(self):
        # issue #23: start-story then update-story is the natural flow and
        # must work even though the skeleton's summary/keys are still empty.
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        f = update_story(d, "First findings.\n", "2026-06-05")
        self.assertIn("## Update — 2026-06-05", f.read_text())

    def test_finish_story_bad_body_keeps_skeleton(self):
        # issue #26: validation must run BEFORE the write, so a body that
        # fails validation leaves the skeleton untouched.
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        before = (d / "story.md").read_text()
        with self.assertRaises(ValueError):
            finish_story(self.kb, d, "no frontmatter, no sections")
        self.assertEqual((d / "story.md").read_text(), before)

    def test_finish_story_merges_skeleton_frontmatter(self):
        # issue #26: repo/slug/date come from the skeleton when the body's
        # frontmatter only carries summary/keys.
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        body = (
            "---\nsummary: Lazy refresh on 401\nkeys: auth, token\n---\n"
            "## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n"
        )
        line = finish_story(self.kb, d, body)
        self.assertIn("[webapp/auth]", line)
        meta, _ = parse_frontmatter((d / "story.md").read_text())
        self.assertEqual(meta["repo"], "webapp")
        self.assertEqual(meta["date"], "2026-06-05")
        self.assertEqual(meta["summary"], "Lazy refresh on 401")


if __name__ == "__main__":
    unittest.main()
