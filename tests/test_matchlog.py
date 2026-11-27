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
