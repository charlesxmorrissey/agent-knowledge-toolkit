import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from akt import config
from akt.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name) / "knowledge"
        self.cfg = Path(self.tmp.name) / "akt-config.md"
        import os
        os.environ["AKT_CONFIG"] = str(self.cfg)

    def tearDown(self):
        import os
        os.environ.pop("AKT_CONFIG", None)
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue().strip()

    def test_init_and_start_and_reindex(self):
        rc, _ = self._run(["init", str(self.kb)])
        self.assertEqual(rc, 0)
        self.assertEqual(config.get("knowledge_base_path", self.cfg), str(self.kb))

        rc, out = self._run(["start-story", "webapp", "Auth Token Refresh", "--date", "2026-06-05"])
        self.assertEqual(rc, 0)
        self.assertTrue(Path(out).joinpath("story.md").exists())

        rc, out = self._run(["reindex"])
        self.assertEqual(rc, 0)
        self.assertIn("indexed", out)

    def test_recall_prints_paths(self):
        self._run(["init", str(self.kb)])
        story = self.kb / "stories" / "webapp" / "2026-06-05-auth"
        (story).mkdir(parents=True)
        (story / "story.md").write_text(
            "---\nrepo: webapp\nslug: auth\nsummary: token refresh\nkeys: auth, token\n---\n## Problem\n"
        )
        self._run(["reindex"])
        rc, out = self._run(["recall", "token auth"])
        self.assertEqual(rc, 0)
        self.assertIn("stories/webapp/2026-06-05-auth/story.md", out)


if __name__ == "__main__":
    unittest.main()
