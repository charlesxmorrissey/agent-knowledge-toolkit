import tempfile
import unittest
from pathlib import Path

from akt.learn import (
    build_learning_line,
    parse_learning_line,
    read_learnings,
    write_learnings,
    scope,
)


def _entry(**over):
    e = {
        "id": "cm6-paste-appends",
        "rule": "Verify live bundle bytes after CodeMirror-6 paste — paste can silently APPEND",
        "hits": 3,
        "status": "candidate",
        "last": "2026-07-30",
        "stories": [
            "heyflow/2026-07-29-overnight-batch",
            "heyflow/2026-07-27-capture-method",
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
        write_learnings(self.kb, [_entry(), _entry(id="other-lesson", stories=["sumo/2026-07-14-x"])])
        entries = read_learnings(self.kb)
        self.assertEqual(len(entries), 2)
        self.assertEqual({e["id"] for e in entries}, {"cm6-paste-appends", "other-lesson"})

    def test_scope_single_repo_is_repo(self):
        self.assertEqual(scope(_entry()), "repo")

    def test_scope_multi_repo_is_global(self):
        e = _entry(stories=["heyflow/2026-07-29-a", "sumo/2026-07-14-b"])
        self.assertEqual(scope(e), "global")


if __name__ == "__main__":
    unittest.main()
