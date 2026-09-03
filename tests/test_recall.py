import tempfile
import unittest
from pathlib import Path

from akt.index import append_index_line, build_index_line
from akt.recall import latest, recall, tokenize


class RecallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        self._add("webapp", "auth-token-refresh", "Lazy token refresh on 401", "auth, token")
        self._add("api", "login-retry", "Retry login backoff", "login, retry")
        self._add("foo", "csv-export", "Stream CSV export", "csv, export")

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, repo, slug, summary, keys):
        meta = {"repo": repo, "slug": slug, "summary": summary, "keys": keys}
        append_index_line(self.kb, build_index_line(meta, "stories/{}/2026-06-05-{}/story.md".format(repo, slug)))

    def test_tokenize(self):
        self.assertEqual(tokenize("Lazy token-refresh, 401!"), ["lazy", "token", "refresh", "401"])

    def test_recall_ranks_by_overlap(self):
        results = recall(self.kb, "how do I handle token auth", limit=3)
        self.assertEqual(results[0]["slug"], "auth-token-refresh")

    def test_recall_excludes_zero_score(self):
        results = recall(self.kb, "token auth", limit=5)
        slugs = [r["slug"] for r in results]
        self.assertIn("auth-token-refresh", slugs)
        self.assertNotIn("csv-export", slugs)

    def test_latest_picks_newest_story_for_repo(self):
        meta = {"repo": "webapp", "slug": "newer", "summary": "Newer story", "keys": "x"}
        append_index_line(self.kb, build_index_line(meta, "stories/webapp/2026-07-01-newer/story.md"))
        entry = latest(self.kb, "webapp")
        self.assertEqual(entry["slug"], "newer")

    def test_latest_none_for_unknown_repo(self):
        self.assertIsNone(latest(self.kb, "nope"))

    def test_latest_ranks_by_story_activity_not_slug(self):
        # issues #24/#25: two stories share a date prefix; the lexically
        # smaller slug got an update-story append later, so it must win.
        import os
        for slug in ("attribution-form", "enter-key"):
            meta = {"repo": "webapp", "slug": slug, "summary": "s", "keys": "k"}
            rel = "stories/webapp/2026-08-10-{}/story.md".format(slug)
            append_index_line(self.kb, build_index_line(meta, rel))
            f = self.kb / rel
            f.parent.mkdir(parents=True)
            f.write_text("story")
        os.utime(self.kb / "stories/webapp/2026-08-10-enter-key/story.md", (1000, 1000))
        os.utime(self.kb / "stories/webapp/2026-08-10-attribution-form/story.md", (2000, 2000))
        self.assertEqual(latest(self.kb, "webapp")["slug"], "attribution-form")

    def test_latest_includes_open_story_not_yet_indexed(self):
        # issues #35/#37: start-story doesn't index, so an open story that got
        # update-story appends after a finished one was invisible to resume.
        import os
        finished = "stories/webapp/2026-08-27-finished/story.md"
        self._add("webapp", "finished", "Finished story", "k")
        for rel, slug, summary in (
            (finished, "finished", "Finished story"),
            ("stories/webapp/2026-08-30-open/story.md", "open", ""),
        ):
            f = self.kb / rel
            f.parent.mkdir(parents=True)
            f.write_text("---\nrepo: webapp\nslug: {}\ndate: d\nsummary: {}\nkeys: \n---\nbody".format(slug, summary))
        os.utime(self.kb / finished, (1000, 1000))
        os.utime(self.kb / "stories/webapp/2026-08-30-open/story.md", (2000, 2000))
        entry = latest(self.kb, "webapp")
        self.assertEqual(entry["slug"], "open")
        self.assertEqual(entry["summary"], "")
        self.assertEqual(entry["path"], "stories/webapp/2026-08-30-open/story.md")

    def test_recall_respects_limit(self):
        results = recall(self.kb, "login token csv export retry", limit=2)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
