import unittest

from akt.frontmatter import tags_from_keys, set_frontmatter_line, parse_frontmatter, build_frontmatter, split_keys


class FrontmatterTest(unittest.TestCase):
    def test_parse_extracts_meta_and_body(self):
        text = "---\nrepo: webapp\nsummary: did a thing\n---\n## Problem\nbody here\n"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["repo"], "webapp")
        self.assertEqual(meta["summary"], "did a thing")
        self.assertEqual(body, "## Problem\nbody here\n")

    def test_parse_no_frontmatter_returns_empty_meta(self):
        text = "## Problem\nno frontmatter\n"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_build_roundtrips(self):
        meta = {"repo": "webapp", "slug": "auth", "summary": "x"}
        out = build_frontmatter(meta)
        parsed, _ = parse_frontmatter(out + "\nbody")
        self.assertEqual(parsed["repo"], "webapp")
        self.assertEqual(parsed["slug"], "auth")

    def test_split_keys(self):
        self.assertEqual(split_keys("auth, token , rate-limit"), ["auth", "token", "rate-limit"])
        self.assertEqual(split_keys(""), [])

    def test_tags_from_keys_shapes_keys_into_obsidian_tags(self):
        # Obsidian ends a tag at a space and allows only [A-Za-z0-9_/-];
        # a purely numeric tag is not a tag at all.
        self.assertEqual(
            tags_from_keys("web-assets cdn, form.js, 1217471298675137, auth, asana-123, [omnito, ,"),
            "web-assets-cdn, formjs, auth, asana-123, omnito",
        )
        self.assertEqual(tags_from_keys(""), "")

    def test_set_frontmatter_line_replaces_or_inserts_after_keys(self):
        text = "---\nrepo: a\nkeys: x, y\n---\n\n## Problem\n"
        out = set_frontmatter_line(text, "tags", "x, y")
        self.assertEqual(out, "---\nrepo: a\nkeys: x, y\ntags: x, y\n---\n\n## Problem\n")
        out2 = set_frontmatter_line(out, "tags", "z")
        self.assertEqual(out2, "---\nrepo: a\nkeys: x, y\ntags: z\n---\n\n## Problem\n")
        # No keys line: the new line goes last in the block.
        self.assertEqual(set_frontmatter_line("---\nrepo: a\n---\nb", "tags", "t"),
                         "---\nrepo: a\ntags: t\n---\nb")


if __name__ == "__main__":
    unittest.main()
