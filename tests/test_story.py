import tempfile
import unittest
from pathlib import Path

from akt.frontmatter import parse_frontmatter
from akt.index import read_index_lines, parse_index_line
from akt.story import start_story, end_session, finish_story


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
        self.assertTrue((d / "sessions" / "01.md").exists())
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


if __name__ == "__main__":
    unittest.main()
