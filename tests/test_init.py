import tempfile
import unittest
from pathlib import Path

from akt import config
from akt.init import init_kb


class InitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name) / "knowledge"
        self.cfg = Path(self.tmp.name) / "akt-config.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_creates_skeleton(self):
        init_kb(self.kb, self.cfg)
        self.assertTrue((self.kb / "stories").is_dir())
        self.assertTrue((self.kb / "AGENTS.md").exists())
        self.assertTrue((self.kb / "INDEX.md").exists())

    def test_init_writes_config(self):
        init_kb(self.kb, self.cfg)
        self.assertEqual(config.get("knowledge_base_path", self.cfg), str(self.kb))
        self.assertEqual(config.get("install_mode", self.cfg), "minimal")

    def test_init_is_idempotent(self):
        init_kb(self.kb, self.cfg)
        (self.kb / "AGENTS.md").write_text("# my rules\nkeep me\n")
        init_kb(self.kb, self.cfg)
        self.assertIn("keep me", (self.kb / "AGENTS.md").read_text())


if __name__ == "__main__":
    unittest.main()
