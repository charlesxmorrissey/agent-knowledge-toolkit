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
    match,
    match_line,
    rules_for,
    set_load,
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
        e, block = graduate(self.kb, "l", core=True)
        self.assertEqual(e["status"], "graduated-global")
        agents = (self.kb / "AGENTS.md").read_text()
        self.assertIn("- Rule text", agents)
        self.assertIn("<!-- akt: l | 2 hits | webapp/2026-07-01-a, shop/2026-07-02-b -->", agents)
        self.assertEqual(block, rule_block(e))

    def test_graduate_global_without_core_stays_in_the_ledger(self):
        # issue #77: the always-loaded file must not grow with every rule.
        add(self.kb, "l", "Rule text", "webapp/2026-07-01-a", "2026-07-01")
        reinforce(self.kb, "l", "shop/2026-07-02-b", "2026-07-02", 3)
        e, block = graduate(self.kb, "l")
        self.assertEqual(e["status"], "graduated-recall")
        self.assertFalse((self.kb / "AGENTS.md").exists())
        self.assertIn("- Rule text", block)

    def test_graduate_repo_local_ignores_core(self):
        add(self.kb, "l", "Rule text", "webapp/2026-07-01-a", "2026-07-01")
        e, _ = graduate(self.kb, "l", core=True)
        self.assertEqual(e["status"], "graduated-repo")
        self.assertFalse((self.kb / "AGENTS.md").exists())

    def _two_core_rules(self):
        for lid in ("first", "second"):
            add(self.kb, lid, "Rule {}".format(lid), "webapp/2026-07-01-a", "2026-07-01")
            reinforce(self.kb, lid, "shop/2026-07-02-b", "2026-07-02", 3)
            graduate(self.kb, lid, core=True)
        return self.kb / "AGENTS.md"

    def test_load_recall_removes_only_that_block(self):
        agents = self._two_core_rules()
        e, found = set_load(self.kb, "first", "recall")
        self.assertTrue(found)
        self.assertEqual(e["status"], "graduated-recall")
        text = agents.read_text()
        self.assertNotIn("Rule first", text)
        self.assertNotIn("akt: first", text)
        self.assertIn("- Rule second\n  <!-- akt: second | 2 hits", text)
        self.assertNotIn("\n\n\n", text)

    def test_load_recall_finds_a_hand_trimmed_comment(self):
        agents = self._two_core_rules()
        agents.write_text(agents.read_text().replace(
            " | webapp/2026-07-01-a, shop/2026-07-02-b -->", " -->"))
        self.assertIn("<!-- akt: second | 2 hits -->", agents.read_text())
        _, found = set_load(self.kb, "second", "recall")
        self.assertTrue(found)
        self.assertNotIn("Rule second", agents.read_text())
        self.assertIn("Rule first", agents.read_text())

    def test_load_recall_does_not_take_an_id_that_only_starts_the_same(self):
        agents = self._two_core_rules()
        add(self.kb, "first-again", "Rule other", "webapp/2026-07-01-a", "2026-07-01")
        reinforce(self.kb, "first-again", "shop/2026-07-02-b", "2026-07-02", 3)
        graduate(self.kb, "first-again", core=True)
        set_load(self.kb, "first", "recall")
        self.assertIn("akt: first-again", agents.read_text())
        self.assertNotIn("Rule first\n", agents.read_text())

    def test_load_recall_with_no_block_still_changes_status(self):
        agents = self._two_core_rules()
        agents.write_text("# Global Rules\n")
        e, found = set_load(self.kb, "first", "recall")
        self.assertFalse(found)
        self.assertEqual(e["status"], "graduated-recall")

    def test_load_core_round_trips(self):
        agents = self._two_core_rules()
        set_load(self.kb, "first", "recall")
        e, _ = set_load(self.kb, "first", "core")
        self.assertEqual(e["status"], "graduated-global")
        self.assertEqual(agents.read_text().count("akt: first"), 1)
        self.assertIn("- Rule first", agents.read_text())

    def test_load_rejects_same_place_and_other_statuses(self):
        self._two_core_rules()
        add(self.kb, "cand", "Rule c", "webapp/2026-07-01-a", "2026-07-01")
        for lid, where in (("first", "core"), ("cand", "recall")):
            with self.assertRaises(ValueError):
                set_load(self.kb, lid, where)

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


class MatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        write_learnings(self.kb, [
            _entry(id="skip-prints-a-line",
                   rule="A step that skips an item must print one line for the item"),
            _entry(id="quote-yaml-values",
                   rule="Quote a YAML value that holds a colon before a parser reads the item",
                   status="graduated-global"),
            _entry(id="sort-keys-portable",
                   rule="Use portable sort keys in a script before the item is read"),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def _ids(self, *args, **kwargs):
        return [e["id"] for e in match(self.kb, *args, **kwargs)]

    def test_best_overlap_ranks_first(self):
        self.assertEqual(self._ids("the parser choked on a colon in a YAML value")[0],
                         "quote-yaml-values")

    def test_word_in_every_rule_counts_least(self):
        # "item" is in all three rules and "colon" in one, so "colon" decides.
        self.assertEqual(self._ids("item colon")[0], "quote-yaml-values")
        self.assertEqual(len(self._ids("item")), 3)

    def test_single_entry_ledger_can_match(self):
        # issue #76: with log(N / df) every word of a one-entry ledger scored 0.
        write_learnings(self.kb, [_entry(id="only", rule="Quote a YAML value")])
        self.assertEqual(self._ids("quote the yaml value"), ["only"])

    def test_id_words_count(self):
        self.assertEqual(self._ids("portable"), ["sort-keys-portable"])

    def test_no_shared_word_returns_nothing(self):
        self.assertEqual(self._ids("zzz qqq"), [])

    def test_limit_caps_the_result(self):
        # "before" is in two of the three rules, so both match without a cap.
        self.assertEqual(len(self._ids("before")), 2)
        self.assertEqual(len(self._ids("before", limit=1)), 1)

    def test_all_statuses_ranked_unless_one_is_named(self):
        self.assertIn("quote-yaml-values", self._ids("yaml colon"))
        self.assertEqual(self._ids("yaml colon", status="candidate"), [])

    def test_match_line_keeps_whole_rule_and_drops_stories(self):
        line = match_line(_entry(rule="R" * 200))
        self.assertIn("R" * 200, line)
        self.assertNotIn("webapp/", line)


class RulesForTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        fillers = [
            _entry(id="filler-{}".format(n),
                   rule="Before the deploy read the log and make a note of step {}".format(n))
            for n in range(30)
        ]
        write_learnings(self.kb, fillers + [
            _entry(id="sheet-paste", status="graduated-recall",
                   rule="Paste rows into a spreadsheet grid with a clipboard event before the deploy"),
            _entry(id="sheet-core", status="graduated-global",
                   rule="Paste rows into a spreadsheet grid with a clipboard event"),
            _entry(id="sheet-candidate",
                   rule="Paste rows into a spreadsheet grid with a clipboard event"),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def _ids(self, task):
        return [e["id"] for e in rules_for(self.kb, task)]

    def test_matching_task_prints_only_the_on_recall_rule(self):
        self.assertEqual(self._ids("paste rows into the spreadsheet grid"), ["sheet-paste"])

    def test_loose_overlap_prints_nothing(self):
        # Shares "before the deploy" with the rule, words most entries hold.
        self.assertEqual(self._ids("check the log before the deploy"), [])

    def test_no_shared_word_prints_nothing(self):
        self.assertEqual(self._ids("zzz qqq"), [])

    def test_empty_ledger_prints_nothing(self):
        write_learnings(self.kb, [])
        self.assertEqual(self._ids("paste rows"), [])
