import json
import os
import tempfile
import unittest
from pathlib import Path

from akt import matchlog


def _match(lesson, *results):
    return {"op": "match", "lesson": lesson, "results": [list(r) for r in results]}


class MatchLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AKT_CONFIG"] = str(Path(self.tmp.name) / "akt-config.md")

    def tearDown(self):
        os.environ.pop("AKT_CONFIG", None)
        self.tmp.cleanup()

    def test_log_sits_beside_the_config_file(self):
        self.assertEqual(matchlog.log_path(), Path(self.tmp.name) / "akt-match-log.jsonl")

    def test_records_round_trip(self):
        matchlog.log_match("yaml colon", [({"id": "quote-yaml"}, 2.04), ({"id": "b"}, 0.5)])
        matchlog.log_action("reinforce", "quote-yaml")
        records = matchlog.read_log()
        self.assertEqual([r["op"] for r in records], ["match", "reinforce"])
        self.assertEqual(records[0]["results"], [["quote-yaml", 2.04], ["b", 0.5]])
        self.assertEqual(records[1]["id"], "quote-yaml")
        self.assertIn("t", records[0])

    def test_a_broken_line_is_skipped(self):
        matchlog.log_action("add", "a")
        with matchlog.log_path().open("a") as fh:
            fh.write("not json\n[1]\n" + json.dumps({"op": "other"}) + "\n")
        self.assertEqual(len(matchlog.read_log()), 1)

    def test_a_log_that_cannot_be_written_does_not_raise(self):
        os.environ["AKT_CONFIG"] = str(Path(self.tmp.name) / "akt-config.md" / "x" / "cfg")
        (Path(self.tmp.name) / "akt-config.md").write_text("a file where a directory is needed\n")
        matchlog.log_action("add", "a")  # no exception

    def test_reinforce_marks_a_true_match_and_add_a_loose_one(self):
        records = [
            _match("first", ("a", 1.0), ("b", 4.1)),
            _match("second", ("c", 2.2), ("d", 1.0)),
            {"op": "reinforce", "id": "b"},
            {"op": "add", "id": "new"},
        ]
        true, loose, unresolved = matchlog.outcomes(records)
        self.assertEqual(true, [(4.1, "b", "first")])
        self.assertEqual(loose, [(2.2, "c", "second")])
        self.assertEqual(unresolved, 0)

    def test_a_lesson_with_no_result_that_is_added_scores_zero(self):
        records = [_match("zzz"), {"op": "add", "id": "new"}]
        self.assertEqual(matchlog.outcomes(records)[1], [(0.0, None, "zzz")])

    def test_fewer_adds_than_leftover_lessons_is_unresolved(self):
        records = [_match("one", ("a", 1.0)), _match("two", ("b", 2.0)),
                   {"op": "add", "id": "new"}]
        true, loose, unresolved = matchlog.outcomes(records)
        self.assertEqual((true, loose, unresolved), ([], [], 2))

    def test_an_add_that_names_its_lesson_pairs_when_another_lesson_was_dropped(self):
        records = [_match("one", ("a", 1.0)), _match("two", ("b", 2.0)),
                   _match("three", ("c", 4.0)),
                   {"op": "reinforce", "id": "c"},
                   {"op": "add", "id": "new", "lesson": "  TWO "}]
        true, loose, unresolved = matchlog.outcomes(records)
        self.assertEqual(true, [(4.0, "c", "three")])
        self.assertEqual(loose, [(2.0, "b", "two")])
        self.assertEqual(unresolved, 1)

    def test_named_and_unnamed_adds_in_one_pass(self):
        records = [_match("one", ("a", 1.0)), _match("two", ("b", 2.0)),
                   {"op": "add", "id": "n1", "lesson": "two"}, {"op": "add", "id": "n2"}]
        true, loose, unresolved = matchlog.outcomes(records)
        self.assertEqual(sorted(loose), [(1.0, "a", "one"), (2.0, "b", "two")])
        self.assertEqual(unresolved, 0)

    def test_a_named_add_does_not_count_toward_the_other_leftovers(self):
        records = [_match("one", ("a", 1.0)), _match("two", ("b", 2.0)),
                   _match("three", ("c", 3.0)),
                   {"op": "add", "id": "n1", "lesson": "two"}, {"op": "add", "id": "n2"}]
        true, loose, unresolved = matchlog.outcomes(records)
        self.assertEqual(loose, [(2.0, "b", "two")])
        self.assertEqual(unresolved, 2)

    def test_a_name_that_is_no_lesson_in_the_pass_pairs_nothing(self):
        records = [_match("one", ("a", 1.0)), _match("two", ("b", 2.0)),
                   {"op": "add", "id": "n1", "lesson": "reworded two"}]
        self.assertEqual(matchlog.outcomes(records), ([], [], 2))

    def test_lesson_in_last_pass_reads_only_the_newest_pass(self):
        records = [_match("old", ("a", 1.0)), {"op": "add", "id": "n"},
                   _match("New  Lesson", ("b", 2.0))]
        self.assertTrue(matchlog.lesson_in_last_pass("new lesson", records))
        self.assertFalse(matchlog.lesson_in_last_pass("old", records))
        self.assertFalse(matchlog.lesson_in_last_pass("anything", []))

    def test_the_unresolved_line_covers_an_add_that_named_no_lesson(self):
        records = [_match("one", ("a", 1.0)), _match("two", ("b", 2.0)),
                   {"op": "add", "id": "n"}]
        self.assertEqual(matchlog.report(records)[-1],
                         "unresolved (not reinforced, and no add names the lesson): 2")

    def test_a_reinforced_id_credits_only_the_lesson_where_it_scored_highest(self):
        records = [_match("the real one", ("a", 4.0), ("b", 1.0)),
                   _match("another lesson", ("c", 1.5), ("a", 0.8)),
                   {"op": "reinforce", "id": "a"},
                   {"op": "add", "id": "n", "lesson": "another lesson"}]
        true, loose, unresolved = matchlog.outcomes(records)
        self.assertEqual(true, [(4.0, "a", "the real one")])
        self.assertEqual(loose, [(1.5, "c", "another lesson")])
        self.assertEqual(unresolved, 0)

    def test_a_match_after_an_action_starts_a_new_pass(self):
        records = [
            _match("one", ("a", 3.0)),
            {"op": "reinforce", "id": "a"},
            _match("two", ("a", 1.0)),
            {"op": "add", "id": "new"},
        ]
        true, loose, _ = matchlog.outcomes(records)
        self.assertEqual(true, [(3.0, "a", "one")])
        self.assertEqual(loose, [(1.0, "a", "two")])

    def test_report_ends_with_the_gap_between_true_and_loose(self):
        records = [
            _match("first", ("b", 4.1)), _match("second", ("c", 2.2)),
            {"op": "reinforce", "id": "b"}, {"op": "add", "id": "new"},
        ]
        self.assertEqual(matchlog.report(records), [
            "true matches (a result id was reinforced after the match): 1",
            "  4.1  [b]  first",
            "no match (the lesson was added as a new entry): 1",
            "  2.2  [c]  second",
            "lowest true match: 4.1 | highest loose result: 2.2",
        ])


if __name__ == "__main__":
    unittest.main()
