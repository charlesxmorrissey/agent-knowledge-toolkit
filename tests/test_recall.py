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

    def test_latest_includes_active_story_without_summary(self):
        import os

        finished = self.kb / "stories/webapp/2026-08-30-finished/story.md"
        active = self.kb / "stories/webapp/2026-08-30-active/story.md"
        for story, summary in ((finished, "finished"), (active, "")):
            story.parent.mkdir(parents=True)
            story.write_text(
                "---\nrepo: webapp\nslug: {}\nsummary: {}\nkeys: auth\n---\n".format(
                    story.parent.name.rsplit("-", 1)[-1], summary
                )
            )
        os.utime(finished, (1000, 1000))
        os.utime(active, (2000, 2000))

        self.assertEqual(latest(self.kb, "webapp")["slug"], "active")

    def test_latest_uses_git_activity_after_clone(self):
        import os
        import subprocess
        subprocess.run(["git", "init", "-q", str(self.kb)], check=True)
        stories = []
        for i, slug in enumerate(("older", "newer"), 1):
            rel = "stories/webapp/2026-08-10-{}/story.md".format(slug)
            append_index_line(self.kb, build_index_line({"repo": "webapp", "slug": slug, "summary": "s", "keys": "k"}, rel))
            f = self.kb / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(slug)
            stories.append(f)
            subprocess.run(["git", "-C", str(self.kb), "add", "."], check=True)
            env = os.environ.copy()
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "2026-08-10T00:0{}:00Z".format(i)
            subprocess.run(["git", "-C", str(self.kb), "commit", "-qm", slug], env=env, check=True)
        os.utime(stories[0], (3000, 3000))
        os.utime(stories[1], (1000, 1000))
        self.assertEqual(latest(self.kb, "webapp")["slug"], "newer")

    def test_recall_respects_limit(self):
        results = recall(self.kb, "login token csv export retry", limit=2)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
