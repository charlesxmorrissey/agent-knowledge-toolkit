import os
import tempfile
import unittest
from pathlib import Path

from akt.index import (
    build_index_line,
    parse_index_line,
    read_index_lines,
    write_index,
    append_index_line,
    reindex,
)


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _meta(self):
        return {
            "repo": "webapp",
            "slug": "auth-token-refresh",
            "summary": "Moved refresh to lazy-on-401",
            "keys": "auth, token, webapp",
        }

    def test_build_line(self):
        line = build_index_line(self._meta(), "stories/webapp/2026-06-05-auth-token-refresh/story.md")
        self.assertEqual(
            line,
            "- [webapp/auth-token-refresh] Moved refresh to lazy-on-401 | keys: auth, token, webapp | stories/webapp/2026-06-05-auth-token-refresh/story.md",
        )

    def test_parse_line_roundtrip(self):
        line = build_index_line(self._meta(), "stories/webapp/2026-06-05-auth-token-refresh/story.md")
        entry = parse_index_line(line)
        self.assertEqual(entry["repo"], "webapp")
        self.assertEqual(entry["slug"], "auth-token-refresh")
        self.assertEqual(entry["summary"], "Moved refresh to lazy-on-401")
        self.assertEqual(entry["keys"], ["auth", "token", "webapp"])
        self.assertEqual(entry["path"], "stories/webapp/2026-06-05-auth-token-refresh/story.md")

    def test_parse_non_index_line_returns_none(self):
        self.assertIsNone(parse_index_line("# Knowledge Index"))

    def test_append_dedupes_by_path(self):
        p = "stories/webapp/2026-06-05-auth-token-refresh/story.md"
        append_index_line(self.kb, build_index_line(self._meta(), p))
        m2 = self._meta()
        m2["summary"] = "Updated summary"
        append_index_line(self.kb, build_index_line(m2, p))
        lines = read_index_lines(self.kb)
        self.assertEqual(len(lines), 1)
        self.assertIn("Updated summary", lines[0])

    def test_reindex_scans_all_stories(self):
        for repo, slug in [("webapp", "auth"), ("api", "retry")]:
            d = self.kb / "stories" / repo / ("2026-06-05-" + slug)
            d.mkdir(parents=True)
            (d / "story.md").write_text(
                "---\nrepo: {}\nslug: {}\nsummary: did {}\nkeys: {}\n---\n## Problem\n".format(
                    repo, slug, slug, slug
                )
            )
        lines = reindex(self.kb)
        self.assertEqual(len(lines), 2)
        paths = sorted(parse_index_line(l)["path"] for l in read_index_lines(self.kb))
        self.assertEqual(
            paths,
            [
                "stories/api/2026-06-05-retry/story.md",
                "stories/webapp/2026-06-05-auth/story.md",
            ],
        )


    def _write_story(self, repo, slug, keys, tags=None):
        d = self.kb / "stories" / repo / ("2026-06-05-" + slug)
        d.mkdir(parents=True, exist_ok=True)
        fm = "---\nrepo: {}\nslug: {}\nsummary: did {}\nkeys: {}\n".format(repo, slug, slug, keys)
        if tags is not None:
            fm += "tags: {}\n".format(tags)
        (d / "story.md").write_text(fm + "---\n## Problem\n")
        return d / "story.md"

    def test_reindex_writes_tags_from_keys_into_untagged_stories(self):
        # issue #66: the backfill, and the repair after a hand-edited keys line.
        missing = self._write_story("webapp", "auth", "auth, google docs")
        stale = self._write_story("api", "retry", "retry, backoff", tags="[retry]")
        reindex(self.kb)
        self.assertIn("tags: [auth, google-docs]\n", missing.read_text())
        self.assertIn("tags: [retry, backoff]\n", stale.read_text())

    def test_reindex_leaves_a_story_with_current_tags_untouched(self):
        current = self._write_story("webapp", "auth", "auth, token", tags="[auth, token]")
        before = current.read_text()
        mtime = current.stat().st_mtime_ns
        reindex(self.kb)
        self.assertEqual(current.read_text(), before)
        self.assertEqual(current.stat().st_mtime_ns, mtime)

    def test_reindex_tags_write_preserves_story_mtime(self):
        # `akt latest` ranks by story.md mtime; a backfill that bumped every
        # mtime would make the newest story whichever file glob wrote last.
        story = self._write_story("webapp", "auth", "auth, token")
        os.utime(story, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
        reindex(self.kb)
        self.assertIn("tags: [auth, token]\n", story.read_text())
        self.assertEqual(story.stat().st_mtime_ns, 1_700_000_000_000_000_000)

    def test_reindex_does_not_add_an_empty_tags_line(self):
        skeleton = self._write_story("webapp", "auth", "")
        reindex(self.kb)
        self.assertNotIn("tags:", skeleton.read_text())

    def test_reindex_reports_tagged_count(self):
        self._write_story("webapp", "auth", "auth")
        self._write_story("api", "retry", "retry", tags="[retry]")
        lines, tagged = reindex(self.kb, with_tags=True)
        self.assertEqual(len(lines), 2)
        self.assertEqual(tagged, ["stories/webapp/2026-06-05-auth/story.md"])

    def test_reindex_skips_unfinished_stories(self):
        # Finished story — non-empty summary
        d_finished = self.kb / "stories" / "webapp" / "2026-06-05-auth"
        d_finished.mkdir(parents=True)
        (d_finished / "story.md").write_text(
            "---\nrepo: webapp\nslug: auth\nsummary: Moved refresh to lazy-on-401\nkeys: auth\n---\n"
        )
        # Unfinished story — empty summary
        d_unfinished = self.kb / "stories" / "webapp" / "2026-06-05-wip"
        d_unfinished.mkdir(parents=True)
        (d_unfinished / "story.md").write_text(
            "---\nrepo: webapp\nslug: wip\nsummary:\nkeys:\n---\n"
        )
        lines = reindex(self.kb)
        self.assertEqual(len(lines), 1)
        index_lines = read_index_lines(self.kb)
        self.assertEqual(len(index_lines), 1)
        self.assertIn("stories/webapp/2026-06-05-auth/story.md", index_lines[0])

    def test_write_index_empty_has_no_trailing_blank_line(self):
        write_index(self.kb, [])
        text = (self.kb / "INDEX.md").read_text()
        self.assertFalse(text.endswith("\n\n"), "empty index must not end with two newlines")
        self.assertTrue(text.endswith("\n"), "empty index must still end with a single newline")

    def test_write_index_nonempty_ends_with_single_newline(self):
        line = "- [a/b] s | keys: k | stories/a/x/story.md"
        write_index(self.kb, [line])
        text = (self.kb / "INDEX.md").read_text()
        self.assertFalse(text.endswith("\n\n"), "non-empty index must not end with two newlines")
        self.assertTrue(text.endswith("\n"), "non-empty index must end with a single newline")
        self.assertIn(line, text)

    def test_append_dedupes_malformed_lines_by_path(self):
        # Legacy lines with empty repo/slug fail the parse regex; dedupe must
        # still match them on the trailing path field so they can't accumulate.
        p = "stories/webapp/2026-07-29-overnight-batch/story.md"
        malformed = "- [/] Overnight batch | keys:  | " + p
        append_index_line(self.kb, malformed)
        append_index_line(self.kb, malformed)
        good = build_index_line(
            {"repo": "webapp", "slug": "overnight-batch",
             "summary": "Overnight batch", "keys": "webapp"}, p)
        append_index_line(self.kb, good)
        lines = read_index_lines(self.kb)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], good)


if __name__ == "__main__":
    unittest.main()
