import tempfile
import unittest
from pathlib import Path

from akt.paths import slugify, story_dir, next_session_number, rel_to_kb


class PathsTest(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Auth Token Refresh"), "auth-token-refresh")
        self.assertEqual(slugify("Fix  the   401!! bug"), "fix-the-401-bug")
        self.assertEqual(slugify("--Trim--"), "trim")

    def test_story_dir(self):
        d = story_dir("/kb", "webapp", "2026-06-05", "auth-token-refresh")
        self.assertEqual(str(d), "/kb/stories/webapp/2026-06-05-auth-token-refresh")

    def test_next_session_number_empty(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(next_session_number(Path(t) / "nope"), 1)

    def test_next_session_number_increments(self):
        with tempfile.TemporaryDirectory() as t:
            s = Path(t)
            (s / "01.md").write_text("x")
            (s / "02.md").write_text("x")
            self.assertEqual(next_session_number(s), 3)

    def test_rel_to_kb(self):
        self.assertEqual(
            rel_to_kb("/kb", "/kb/stories/webapp/2026-06-05-auth/story.md"),
            "stories/webapp/2026-06-05-auth/story.md",
        )


if __name__ == "__main__":
    unittest.main()
