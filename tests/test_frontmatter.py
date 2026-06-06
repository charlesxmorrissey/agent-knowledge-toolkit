import unittest

from akt.frontmatter import parse_frontmatter, build_frontmatter, split_keys


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


if __name__ == "__main__":
    unittest.main()
