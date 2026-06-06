import tempfile
import unittest
from pathlib import Path

from akt.index import append_index_line, build_index_line
from akt.recall import recall, tokenize


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

    def test_recall_respects_limit(self):
        results = recall(self.kb, "login token csv export retry", limit=2)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
