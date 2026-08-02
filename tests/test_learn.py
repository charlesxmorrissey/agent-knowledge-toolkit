import tempfile
import unittest
from pathlib import Path

from akt.learn import (
    build_learning_line,
    parse_learning_line,
    read_learnings,
    write_learnings,
    scope,
    add,
    reinforce,
    graduate,
    wont,
    prune_report,
    rule_block,
)


def _entry(**over):
    e = {
        "id": "cm6-paste-appends",
        "rule": "Verify live bundle bytes after CodeMirror-6 paste — paste can silently APPEND",
        "hits": 3,
        "status": "candidate",
        "last": "2026-07-30",
        "stories": [
            "webapp/2026-07-29-overnight-batch",
            "webapp/2026-07-27-capture-method",
        ],
    }
    e.update(over)
    return e


class LedgerCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_line_roundtrip(self):
        line = build_learning_line(_entry())
        parsed = parse_learning_line(line)
        self.assertEqual(parsed, _entry())

    def test_parse_non_entry_returns_none(self):
        self.assertIsNone(parse_learning_line("# Learnings"))
        self.assertIsNone(parse_learning_line(""))

    def test_read_missing_file_returns_empty(self):
        self.assertEqual(read_learnings(self.kb), [])

    def test_write_then_read(self):
        write_learnings(self.kb, [_entry(), _entry(id="other-lesson", stories=["shop/2026-07-14-x"])])
        entries = read_learnings(self.kb)
        self.assertEqual(len(entries), 2)
        self.assertEqual({e["id"] for e in entries}, {"cm6-paste-appends", "other-lesson"})

    def test_read_raises_on_malformed_bracket_line(self):
        bad_line = "- [x] Rule | hits: NaN | status: candidate | last: 2026-07-30 | stories: a/b"
        (self.kb / "LEARNINGS.md").write_text("# Learnings\n\n" + bad_line + "\n")
        with self.assertRaises(ValueError) as cm:
            read_learnings(self.kb)
        self.assertIn(bad_line, str(cm.exception))

    def test_scope_single_repo_is_repo(self):
        self.assertEqual(scope(_entry()), "repo")

    def test_scope_multi_repo_is_global(self):
        e = _entry(stories=["webapp/2026-07-29-a", "shop/2026-07-14-b"])
        self.assertEqual(scope(e), "global")


class LedgerOpsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_starts_at_one(self):
        e = add(self.kb, "new-lesson", "Do the thing first", "webapp/2026-07-30-x", "2026-07-30")
        self.assertEqual(e["hits"], 1)
        self.assertEqual(e["status"], "candidate")
        self.assertEqual(read_learnings(self.kb)[0]["id"], "new-lesson")

    def test_add_rejects_duplicate_id_and_pipe(self):
        add(self.kb, "new-lesson", "Do the thing", "webapp/2026-07-30-x", "2026-07-30")
        with self.assertRaises(ValueError):
            add(self.kb, "new-lesson", "Again", "shop/2026-07-30-y", "2026-07-30")
        with self.assertRaises(ValueError):
            add(self.kb, "piped", "bad | rule", "shop/2026-07-30-y", "2026-07-30")

    def test_reinforce_bumps_and_dedupes(self):
        add(self.kb, "l", "Rule", "webapp/2026-07-01-a", "2026-07-01")
        e, prop = reinforce(self.kb, "l", "webapp/2026-07-02-b", "2026-07-02", 3)
        self.assertEqual((e["hits"], e["last"]), (2, "2026-07-02"))
        self.assertIsNone(prop)
        e, _ = reinforce(self.kb, "l", "webapp/2026-07-02-b", "2026-07-03", 3)
        self.assertEqual(e["stories"].count("webapp/2026-07-02-b"), 1)

    def test_reinforce_proposes_at_threshold_and_keeps_proposing(self):
        add(self.kb, "l", "Rule", "webapp/2026-07-01-a", "2026-07-01")
        reinforce(self.kb, "l", "shop/2026-07-02-b", "2026-07-02", 3)
        e, prop = reinforce(self.kb, "l", "webapp/2026-07-03-c", "2026-07-03", 3)
        self.assertIn("PROPOSE:", prop)
        self.assertIn("GLOBAL", prop)
        self.assertIn("akt learn graduate l", prop)
        _, again = reinforce(self.kb, "l", "api/2026-07-04-d", "2026-07-04", 3)
        self.assertIn("PROPOSE:", again)

    def test_reinforce_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            reinforce(self.kb, "nope", "webapp/2026-07-30-x", "2026-07-30", 3)

    def test_graduate_global_appends_to_agents_md(self):
        add(self.kb, "l", "Rule text", "webapp/2026-07-01-a", "2026-07-01")
        reinforce(self.kb, "l", "shop/2026-07-02-b", "2026-07-02", 3)
        e, block = graduate(self.kb, "l")
        self.assertEqual(e["status"], "graduated-global")
        agents = (self.kb / "AGENTS.md").read_text()
        self.assertIn("- Rule text", agents)
        self.assertIn("<!-- akt: l | 2 hits | webapp/2026-07-01-a, shop/2026-07-02-b -->", agents)
        self.assertEqual(block, rule_block(e))

    def test_graduate_repo_local_writes_nothing_outside_ledger(self):
        add(self.kb, "l", "Rule text", "webapp/2026-07-01-a", "2026-07-01")
        e, block = graduate(self.kb, "l")
        self.assertEqual(e["status"], "graduated-repo")
        self.assertFalse((self.kb / "AGENTS.md").exists())
        self.assertIn("- Rule text", block)

    def test_graduate_twice_raises(self):
        add(self.kb, "l", "Rule", "webapp/2026-07-01-a", "2026-07-01")
        graduate(self.kb, "l")
        with self.assertRaises(ValueError):
            graduate(self.kb, "l")

    def test_wont_suppresses_proposals(self):
        add(self.kb, "l", "Rule", "webapp/2026-07-01-a", "2026-07-01")
        e = wont(self.kb, "l")
        self.assertEqual(e["status"], "wont-graduate")
        _, prop = reinforce(self.kb, "l", "shop/2026-07-02-b", "2026-07-02", 1)
        self.assertIsNone(prop)

    def test_prune_report_date_cutoff(self):
        add(self.kb, "old", "Old rule", "webapp/2026-01-01-a", "2026-01-01")
        add(self.kb, "fresh", "Fresh rule", "shop/2026-07-29-b", "2026-07-29")
        add(self.kb, "grad", "Grad rule", "webapp/2026-01-01-c", "2026-01-01")
        graduate(self.kb, "grad")
        stale_candidates, stale_graduated = prune_report(self.kb, "2026-07-30", 90)
        self.assertEqual([e["id"] for e in stale_candidates], ["old"])
        self.assertEqual([e["id"] for e in stale_graduated], ["grad"])


if __name__ == "__main__":
    unittest.main()
