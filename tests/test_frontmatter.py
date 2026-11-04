import unittest

from akt.frontmatter import tags_from_keys, set_frontmatter_line, parse_frontmatter, build_frontmatter, split_keys, quote_value


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
            "[web-assets-cdn, formjs, auth, asana-123, omnito]",
        )
        self.assertEqual(tags_from_keys(""), "")

    def test_tags_value_is_a_yaml_flow_list(self):
        # Obsidian reads a bare `tags: a, b` string as ONE tag named "a, b"
        # and flags it invalid; only a YAML list gives one tag per key.
        self.assertEqual(tags_from_keys("auth"), "[auth]")
        self.assertTrue(tags_from_keys("auth, token").startswith("["))

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


class YamlSafeValueTest(unittest.TestCase):
    # A summary is prose, and prose contains ": " and " #" all the time. A
    # YAML reader (Obsidian, GitHub) errors on the first and silently truncates
    # at the second; AKT's own line parser never cared. Quote only when needed
    # so a clean summary stays byte-identical to what it was.
    def test_quote_value_leaves_a_safe_value_alone(self):
        self.assertEqual(quote_value("Moved refresh to lazy-on-401"), "Moved refresh to lazy-on-401")
        self.assertEqual(quote_value("smb:// and 10:30 are fine"), "smb:// and 10:30 are fine")
        self.assertEqual(quote_value("it's fine (#1) and a\"b"), "it's fine (#1) and a\"b")

    def test_quote_value_quotes_mapping_and_comment_indicators(self):
        self.assertEqual(quote_value("Fix: quote it"), '"Fix: quote it"')
        self.assertEqual(quote_value("shipped in PR #67"), '"shipped in PR #67"')
        self.assertEqual(quote_value("ends with a colon:"), '"ends with a colon:"')

    def test_quote_value_quotes_a_leading_indicator_character(self):
        self.assertEqual(quote_value('"quoted" at the start'), '"\\"quoted\\" at the start"')
        self.assertEqual(quote_value("'single' at the start"), "\"'single' at the start\"")
        self.assertEqual(quote_value("[omnito] widget"), '"[omnito] widget"')
        self.assertEqual(quote_value("- not a list"), '"- not a list"')

    def test_quote_value_escapes_backslashes_and_quotes(self):
        self.assertEqual(quote_value('Fix: C:\\x says "hi"'), '"Fix: C:\\\\x says \\"hi\\""')

    def test_parse_unquotes_a_double_quoted_value(self):
        text = '---\nsummary: "Fix: it \\"works\\" on C:\\\\x"\nkeys: a\n---\n'
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["summary"], 'Fix: it "works" on C:\\x')
        self.assertEqual(meta["keys"], "a")

    def test_parse_leaves_a_value_with_a_lone_leading_quote_alone(self):
        meta, _ = parse_frontmatter('---\nsummary: "quoted" then more\n---\n')
        self.assertEqual(meta["summary"], '"quoted" then more')

    def test_build_quotes_the_summary_but_not_the_tags_list(self):
        meta = {"summary": "Fix: quote it", "keys": "a, b", "tags": "[a, b]"}
        out = build_frontmatter(meta)
        self.assertIn('summary: "Fix: quote it"\n', out)
        self.assertIn("tags: [a, b]\n", out)
        parsed, _ = parse_frontmatter(out + "\nbody")
        self.assertEqual(parsed["summary"], "Fix: quote it")
        self.assertEqual(parsed["tags"], "[a, b]")
