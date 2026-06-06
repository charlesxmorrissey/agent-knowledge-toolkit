import tempfile
import unittest
from pathlib import Path

from akt import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "akt-config.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_missing_returns_empty(self):
        self.assertEqual(config.read_config(self.path), {})

    def test_set_then_get(self):
        config.set_value("knowledge_base_path", "/tmp/kb", self.path)
        self.assertEqual(config.get("knowledge_base_path", self.path), "/tmp/kb")

    def test_set_preserves_other_keys(self):
        config.set_value("knowledge_base_path", "/tmp/kb", self.path)
        config.set_value("install_mode", "minimal", self.path)
        self.assertEqual(config.get("knowledge_base_path", self.path), "/tmp/kb")
        self.assertEqual(config.get("install_mode", self.path), "minimal")

    def test_ignores_comments_and_blanks(self):
        self.path.write_text("# comment\n\nknowledge_base_path: /tmp/kb\n")
        self.assertEqual(config.get("knowledge_base_path", self.path), "/tmp/kb")


if __name__ == "__main__":
    unittest.main()
