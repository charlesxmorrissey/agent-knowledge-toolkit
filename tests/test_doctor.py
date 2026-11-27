import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from akt import doctor
from akt import install as install_mod
from akt.cli import main


def _git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.kb = Path(self.tmp.name) / "knowledge"
        self.cfg = Path(self.tmp.name) / "akt-config.md"
        os.environ["AKT_CONFIG"] = str(self.cfg)

    def tearDown(self):
        os.environ.pop("AKT_CONFIG", None)
        self.tmp.cleanup()

    def _quiet(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = main(argv)
        return rc, out.getvalue()

    def _setup(self):
        """A knowledge base in git with one finished story, and a full install."""
        self._quiet(["init", str(self.kb)])
        _, out = self._quiet(["start-story", "webapp", "Auth", "--date", "2026-06-05"])
        story = self.kb / out.strip() / "story.md"
        story.write_text(story.read_text().replace("summary:", "summary: token refresh"))
        self._quiet(["reindex"])
        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t.test"],
                     ["config", "user.name", "t"], ["add", "-A"],
                     ["commit", "-q", "-m", "init"]):
            _git(self.kb, *args)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            install_mod.install(home=self.home)
        return story

    def _toolkit_repo(self, branch):
        repo = Path(self.tmp.name) / "toolkit"
        repo.mkdir()
        for args in (["init", "-q", "-b", branch], ["config", "user.email", "t@t.test"],
                     ["config", "user.name", "t"],
                     ["commit", "-q", "--allow-empty", "-m", "init"]):
            _git(repo, *args)
        return repo

    def _results(self):
        return [r for r in doctor.run(home=self.home)
                if not r[1].startswith("toolkit:")]  # this repo's own branch varies

    def test_a_healthy_setup_passes_every_check(self):
        self._setup()
        results = self._results()
        self.assertEqual([r[1] for r in results if not r[0]], [])
        texts = "\n".join(r[1] for r in results)
        for word in ("config:", "install:", "imports:", "no uncommitted changes",
                     "nothing to push", "git objects:", "index: 1 finished",
                     "ledger: 0 entries", "rules: AGENTS.md"):
            self.assertIn(word, texts)

    def test_doctor_changes_nothing(self):
        self._setup()
        before = sorted((str(p), p.stat().st_mtime_ns) for p in Path(self.tmp.name).rglob("*")
                        if ".git" not in p.parts)
        doctor.run(home=self.home)
        after = sorted((str(p), p.stat().st_mtime_ns) for p in Path(self.tmp.name).rglob("*")
                       if ".git" not in p.parts)
        self.assertEqual(before, after)

    def test_missing_config_fails_and_skips_the_knowledge_base_checks(self):
        results = doctor.run(home=self.home)
        self.assertFalse(results[0][0])
        self.assertIn("does not exist", results[0][1])
        self.assertEqual(results[0][2], "akt init <path>")
        self.assertFalse(any(r[1].startswith(("index:", "ledger:")) for r in results))

    def test_a_link_that_is_a_real_file_or_missing_fails(self):
        self._setup()
        rule = self.home / ".claude" / "AKT.md"
        rule.unlink()
        rule.write_text("mine\n")
        (self.home / ".local" / "bin" / "akt").unlink()
        failed = [r for r in self._results() if not r[0]]
        self.assertEqual(len(failed), 2)
        self.assertIn("is missing", failed[0][1])
        self.assertIn("is not a symlink", failed[1][1])
        self.assertEqual(failed[0][2], "akt install")

    def test_a_branch_that_is_not_main_fails(self):
        ok, text, fix = doctor._check_toolkit_branch(self._toolkit_repo("fix-foo"))
        self.assertFalse(ok)
        self.assertIn("'fix-foo'", text)
        self.assertTrue(fix.endswith("checkout main"))

    def test_main_passes_and_a_plain_directory_is_not_judged(self):
        self.assertTrue(doctor._check_toolkit_branch(self._toolkit_repo("main"))[0])
        plain = Path(self.tmp.name) / "plain"
        plain.mkdir()
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": self.tmp.name}):
            self.assertTrue(doctor._check_toolkit_branch(plain)[0])

    def test_a_missing_import_fails(self):
        self._setup()
        claude_md = self.home / ".claude" / "CLAUDE.md"
        claude_md.write_text("@AKT.md\n")
        failed = [r for r in self._results() if not r[0]]
        self.assertEqual(len(failed), 1)
        self.assertIn("@{}/AGENTS.md".format(self.kb), failed[0][1])

    def test_uncommitted_changes_fail_but_an_open_story_does_not(self):
        self._setup()
        self._quiet(["start-story", "webapp", "Open one", "--date", "2026-06-06"])
        self.assertEqual([r for r in self._results() if not r[0]], [])
        (self.kb / "stray.md").write_text("x\n")
        failed = [r for r in self._results() if not r[0]]
        self.assertEqual(len(failed), 1)
        self.assertIn("1 uncommitted path(s), first: stray.md", failed[0][1])

    def test_commits_that_are_not_pushed_fail(self):
        self._setup()
        remote = Path(self.tmp.name) / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        _git(self.kb, "remote", "add", "origin", str(remote))
        _git(self.kb, "push", "-q", "-u", "origin", "main")
        self.assertTrue(doctor._check_pushed(self.kb)[0])
        _git(self.kb, "commit", "-q", "--allow-empty", "-m", "more")
        ok, text, fix = doctor._check_pushed(self.kb)
        self.assertFalse(ok)
        self.assertIn("1 commit(s) not pushed", text)

    def test_loose_objects_above_the_limit_fail(self):
        self._setup()
        self.assertTrue(doctor._check_loose(self.kb)[0])
        with mock.patch.object(doctor, "LOOSE_LIMIT_KIB", 0):
            ok, text, fix = doctor._check_loose(self.kb)
        self.assertFalse(ok)
        self.assertIn("loose", text)
        self.assertTrue(fix.endswith(" gc"))

    def test_a_finished_story_with_no_index_line_fails(self):
        self._setup()
        (self.kb / "INDEX.md").write_text("# Knowledge Index\n")
        ok, text, fix = doctor._check_index(self.kb)
        self.assertFalse(ok)
        self.assertIn("1 finished story(ies) with no index line", text)
        self.assertEqual(fix, "akt reindex")

    def test_an_index_line_for_a_story_that_is_gone_fails(self):
        story = self._setup()
        story.unlink()
        ok, text, _ = doctor._check_index(self.kb)
        self.assertFalse(ok)
        self.assertIn("1 index line(s) for a story that is not on disk", text)

    def test_a_ledger_line_that_does_not_parse_fails(self):
        self._setup()
        (self.kb / "LEARNINGS.md").write_text("# Learnings\n\n- [broken] no fields\n")
        ok, text, _ = doctor._check_ledger(self.kb)
        self.assertFalse(ok)
        self.assertIn("malformed ledger line", text)

    def test_cli_prints_a_line_per_check_and_exits_1_on_a_failure(self):
        canned = [(True, "config: fine", None), (False, "index: 1 missing", "akt reindex")]
        with mock.patch.object(doctor, "run", return_value=canned):
            rc, out = self._quiet(["doctor"])
            self.assertEqual(rc, 1)
            self.assertEqual(out.splitlines(), [
                "ok    config: fine", "FAIL  index: 1 missing (fix: akt reindex)"])
            rc, out = self._quiet(["doctor", "--quiet"])
            self.assertEqual(rc, 1)
            self.assertEqual(out.splitlines(), ["FAIL  index: 1 missing (fix: akt reindex)"])

    def test_cli_quiet_prints_nothing_and_exits_0_when_every_check_passes(self):
        with mock.patch.object(doctor, "run", return_value=[(True, "config: fine", None)]):
            rc, out = self._quiet(["doctor", "--quiet"])
        self.assertEqual((rc, out), (0, ""))


if __name__ == "__main__":
    unittest.main()
