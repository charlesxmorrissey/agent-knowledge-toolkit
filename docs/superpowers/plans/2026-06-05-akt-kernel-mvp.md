# AKT Kernel MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the portable kernel of the Agent Knowledge Toolkit — recall + capture lifecycle over a git-backed personal knowledge base — as a zero-install Python CLI plus thin Claude Code slash commands.

**Architecture:** Markdown is the source of truth (`story.md` with minimal frontmatter); `INDEX.md` is a derived, regenerable search cache. A `python3 -m akt` CLI does all deterministic file/text work (scaffold stories, write session handoffs, parse/append/rebuild the index, keyword-scored recall, init + config). Thin `.claude/commands/*.md` slash commands wrap the CLI and carry the LLM judgment (distillation prose, final recall relevance). Recall hides behind one interface — *query → ranked story paths* — so keyword scoring can later be swapped for embeddings without touching artifacts.

**Tech Stack:** Python 3.9 (stdlib only: `argparse`, `pathlib`, `re`, `datetime`, `tempfile`, `unittest`). No third-party deps. Run as `python3 -m akt`; test with `python3 -m unittest discover -s tests`.

**Spec:** `docs/superpowers/specs/2026-06-05-agent-knowledge-toolkit-design.md`

**Conventions locked for this plan (all tasks must match exactly):**

- **Config file** (default `~/.claude/akt-config.md`, override via env `AKT_CONFIG`): lines of `key: value`. Keys used: `knowledge_base_path`, `install_mode`.
- **`story.md` frontmatter** (delimited by `---` lines):
  ```
  ---
  repo: webapp
  slug: auth-token-refresh
  date: 2026-06-05
  summary: Moved refresh from cron to lazy-on-401 to stop thundering-herd reauth
  keys: auth, token, rate-limit, webapp
  ---
  ```
  `keys` is a comma-separated string. `summary` is the one-line decision + because.
- **`INDEX.md` line** (one line per story, path relative to knowledge base root):
  ```
  - [webapp/auth-token-refresh] Moved refresh from cron to lazy-on-401 to stop thundering-herd reauth | keys: auth, token, rate-limit, webapp | stories/webapp/2026-06-05-auth-token-refresh/story.md
  ```
- **Story dir:** `stories/<repo>/<date>-<slug>/` containing `story.md` and `sessions/NN.md` (zero-padded 2-digit, starting `01`).
- **Imports:** absolute (`from akt.frontmatter import ...`) everywhere, in package and tests.

---

## File Structure

- `akt/__init__.py` — empty package marker.
- `akt/__main__.py` — entry point for `python3 -m akt`.
- `akt/frontmatter.py` — parse/serialize the minimal frontmatter; split keys.
- `akt/config.py` — read/write the `key: value` config file; `AKT_CONFIG` override.
- `akt/paths.py` — `slugify`, story dir builder, next session number, relative-to-kb.
- `akt/index.py` — build/parse index lines, read/write/append, `reindex`.
- `akt/recall.py` — tokenize, score index entries vs query, return ranked entries.
- `akt/story.py` — `start_story`, `end_session`, `finish_story`.
- `akt/init.py` — `init_kb` (scaffold KB + write config).
- `akt/cli.py` — argparse dispatch over all subcommands.
- `tests/test_frontmatter.py`, `test_config.py`, `test_paths.py`, `test_index.py`, `test_recall.py`, `test_story.py`, `test_init.py`, `test_cli.py`.
- `.claude/commands/{start-story,end-session,finish-story,recall}.md` — thin slash commands.

---

### Task 1: Project scaffold + test harness

**Files:**
- Create: `akt/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`

- [ ] **Step 1: Create the package and test markers**

```bash
mkdir -p akt tests
: > akt/__init__.py
: > tests/__init__.py
```

- [ ] **Step 2: Write a smoke test**

`tests/test_smoke.py`:

```python
import importlib
import unittest


class SmokeTest(unittest.TestCase):
    def test_package_imports(self):
        mod = importlib.import_module("akt")
        self.assertIsNotNone(mod)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it to verify it passes**

Run: `python3 -m unittest discover -s tests -v`
Expected: `test_package_imports` PASS, OK.

- [ ] **Step 4: Add `.gitignore`**

`.gitignore`:

```
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 5: Commit**

```bash
git add akt/__init__.py tests/__init__.py tests/test_smoke.py .gitignore
git commit -m "feat(akt): package scaffold + smoke test"
```

---

### Task 2: Frontmatter parser

**Files:**
- Create: `akt/frontmatter.py`
- Test: `tests/test_frontmatter.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_frontmatter.py`:

```python
import unittest

from akt.frontmatter import parse_frontmatter, build_frontmatter, split_keys


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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_frontmatter -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.frontmatter'`.

- [ ] **Step 3: Implement `akt/frontmatter.py`**

```python
"""Parse and build the minimal frontmatter used by story.md files."""


def parse_frontmatter(text):
    """Return (meta dict, body str). If no leading '---' block, meta is {} and body is text."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        i += 1
    body = "".join(lines[i + 1:]) if i < len(lines) else ""
    return meta, body


def build_frontmatter(meta):
    """Serialize a dict to a '---' delimited block (no trailing newline)."""
    out = ["---"]
    for key, value in meta.items():
        out.append("{}: {}".format(key, value))
    out.append("---")
    return "\n".join(out)


def split_keys(keys_value):
    """Split a comma-separated keys string into a clean list."""
    return [k.strip() for k in keys_value.split(",") if k.strip()]
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_frontmatter -v`
Expected: 4 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/frontmatter.py tests/test_frontmatter.py
git commit -m "feat(akt): minimal frontmatter parser"
```

---

### Task 3: Config read/write

**Files:**
- Create: `akt/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_config -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.config'`.

- [ ] **Step 3: Implement `akt/config.py`**

```python
"""Read/write the AKT config file (simple `key: value` lines)."""
import os
import re
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".claude" / "akt-config.md"
_LINE = re.compile(r"^([a-z_]+):\s*(.*)$")


def config_path():
    return Path(os.environ.get("AKT_CONFIG", str(DEFAULT_CONFIG)))


def read_config(path=None):
    path = Path(path) if path else config_path()
    cfg = {}
    if not path.exists():
        return cfg
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _LINE.match(stripped)
        if m:
            cfg[m.group(1)] = m.group(2).strip()
    return cfg


def write_config(cfg, path=None):
    path = Path(path) if path else config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["{}: {}".format(k, v) for k, v in sorted(cfg.items())]
    path.write_text("\n".join(lines) + "\n")


def get(key, path=None):
    return read_config(path).get(key)


def set_value(key, value, path=None):
    cfg = read_config(path)
    cfg[key] = value
    write_config(cfg, path)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_config -v`
Expected: 4 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/config.py tests/test_config.py
git commit -m "feat(akt): config read/write with AKT_CONFIG override"
```

---

### Task 4: Paths, slug, session numbering

**Files:**
- Create: `akt/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_paths.py`:

```python
import tempfile
import unittest
from pathlib import Path

from akt.paths import slugify, story_dir, next_session_number, rel_to_kb


class PathsTest(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Auth Token Refresh"), "auth-token-refresh")
        self.assertEqual(slugify("Fix  the   401!! bug"), "fix-the-401-bug")
        self.assertEqual(slugify("--Trim--"), "trim")

    def test_story_dir(self):
        d = story_dir("/kb", "webapp", "2026-06-05", "auth-token-refresh")
        self.assertEqual(str(d), "/kb/stories/webapp/2026-06-05-auth-token-refresh")

    def test_next_session_number_empty(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(next_session_number(Path(t) / "nope"), 1)

    def test_next_session_number_increments(self):
        with tempfile.TemporaryDirectory() as t:
            s = Path(t)
            (s / "01.md").write_text("x")
            (s / "02.md").write_text("x")
            self.assertEqual(next_session_number(s), 3)

    def test_rel_to_kb(self):
        self.assertEqual(
            rel_to_kb("/kb", "/kb/stories/webapp/2026-06-05-auth/story.md"),
            "stories/webapp/2026-06-05-auth/story.md",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_paths -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.paths'`.

- [ ] **Step 3: Implement `akt/paths.py`**

```python
"""Path helpers: slugify titles, build story dirs, number sessions."""
import re
from pathlib import Path

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_SESSION = re.compile(r"^(\d+)\.md$")


def slugify(title):
    s = _SLUG_STRIP.sub("-", title.lower())
    return s.strip("-")


def story_dir(kb_path, repo, date, slug):
    return Path(kb_path) / "stories" / repo / "{}-{}".format(date, slug)


def next_session_number(sessions_dir):
    sessions_dir = Path(sessions_dir)
    if not sessions_dir.exists():
        return 1
    nums = []
    for p in sessions_dir.glob("*.md"):
        m = _SESSION.match(p.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def rel_to_kb(kb_path, target):
    return str(Path(target).relative_to(Path(kb_path)))
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_paths -v`
Expected: 5 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/paths.py tests/test_paths.py
git commit -m "feat(akt): path/slug/session-number helpers"
```

---

### Task 5: Index build / parse / read / write / append / reindex

**Files:**
- Create: `akt/index.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_index.py`:

```python
import tempfile
import unittest
from pathlib import Path

from akt.index import (
    build_index_line,
    parse_index_line,
    read_index_lines,
    write_index,
    append_index_line,
    reindex,
)


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _meta(self):
        return {
            "repo": "webapp",
            "slug": "auth-token-refresh",
            "summary": "Moved refresh to lazy-on-401",
            "keys": "auth, token, webapp",
        }

    def test_build_line(self):
        line = build_index_line(self._meta(), "stories/webapp/2026-06-05-auth-token-refresh/story.md")
        self.assertEqual(
            line,
            "- [webapp/auth-token-refresh] Moved refresh to lazy-on-401 | keys: auth, token, webapp | stories/webapp/2026-06-05-auth-token-refresh/story.md",
        )

    def test_parse_line_roundtrip(self):
        line = build_index_line(self._meta(), "stories/webapp/2026-06-05-auth-token-refresh/story.md")
        entry = parse_index_line(line)
        self.assertEqual(entry["repo"], "webapp")
        self.assertEqual(entry["slug"], "auth-token-refresh")
        self.assertEqual(entry["summary"], "Moved refresh to lazy-on-401")
        self.assertEqual(entry["keys"], ["auth", "token", "webapp"])
        self.assertEqual(entry["path"], "stories/webapp/2026-06-05-auth-token-refresh/story.md")

    def test_parse_non_index_line_returns_none(self):
        self.assertIsNone(parse_index_line("# Knowledge Index"))

    def test_append_dedupes_by_path(self):
        p = "stories/webapp/2026-06-05-auth-token-refresh/story.md"
        append_index_line(self.kb, build_index_line(self._meta(), p))
        m2 = self._meta()
        m2["summary"] = "Updated summary"
        append_index_line(self.kb, build_index_line(m2, p))
        lines = read_index_lines(self.kb)
        self.assertEqual(len(lines), 1)
        self.assertIn("Updated summary", lines[0])

    def test_reindex_scans_all_stories(self):
        for repo, slug in [("webapp", "auth"), ("api", "retry")]:
            d = self.kb / "stories" / repo / ("2026-06-05-" + slug)
            d.mkdir(parents=True)
            (d / "story.md").write_text(
                "---\nrepo: {}\nslug: {}\nsummary: did {}\nkeys: {}\n---\n## Problem\n".format(
                    repo, slug, slug, slug
                )
            )
        lines = reindex(self.kb)
        self.assertEqual(len(lines), 2)
        paths = sorted(parse_index_line(l)["path"] for l in read_index_lines(self.kb))
        self.assertEqual(
            paths,
            [
                "stories/api/2026-06-05-retry/story.md",
                "stories/webapp/2026-06-05-auth/story.md",
            ],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_index -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.index'`.

- [ ] **Step 3: Implement `akt/index.py`**

```python
"""Build, parse, and maintain INDEX.md — the derived search cache."""
import re
from pathlib import Path

from akt.frontmatter import parse_frontmatter, split_keys

INDEX_FILE = "INDEX.md"
_HEADER = "# Knowledge Index\n\nOne line per story. Generated — do not hand-edit.\n"
_LINE = re.compile(r"^- \[([^/]+)/([^\]]+)\] (.*) \| keys: (.*) \| (.*)$")


def build_index_line(meta, rel_path):
    return "- [{}/{}] {} | keys: {} | {}".format(
        meta.get("repo", ""),
        meta.get("slug", ""),
        meta.get("summary", "").strip(),
        meta.get("keys", "").strip(),
        rel_path,
    )


def parse_index_line(line):
    m = _LINE.match(line.strip())
    if not m:
        return None
    return {
        "repo": m.group(1),
        "slug": m.group(2),
        "summary": m.group(3),
        "keys": split_keys(m.group(4)),
        "path": m.group(5),
    }


def _index_file(kb_path):
    return Path(kb_path) / INDEX_FILE


def read_index_lines(kb_path):
    f = _index_file(kb_path)
    if not f.exists():
        return []
    return [ln for ln in f.read_text().splitlines() if ln.strip().startswith("- [")]


def write_index(kb_path, lines):
    body = "\n".join(sorted(lines))
    _index_file(kb_path).write_text(_HEADER + "\n" + body + ("\n" if body else ""))


def append_index_line(kb_path, line):
    new_entry = parse_index_line(line)
    kept = []
    for existing in read_index_lines(kb_path):
        parsed = parse_index_line(existing)
        if parsed and new_entry and parsed["path"] == new_entry["path"]:
            continue
        kept.append(existing)
    kept.append(line)
    write_index(kb_path, kept)


def reindex(kb_path):
    kb_path = Path(kb_path)
    lines = []
    for story_md in (kb_path / "stories").glob("*/*/story.md"):
        meta, _ = parse_frontmatter(story_md.read_text())
        rel = str(story_md.relative_to(kb_path))
        lines.append(build_index_line(meta, rel))
    write_index(kb_path, lines)
    return lines
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_index -v`
Expected: 5 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/index.py tests/test_index.py
git commit -m "feat(akt): INDEX.md build/parse/append/reindex"
```

---

### Task 6: Recall (keyword-scored retrieval)

**Files:**
- Create: `akt/recall.py`
- Test: `tests/test_recall.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_recall.py`:

```python
import tempfile
import unittest
from pathlib import Path

from akt.index import append_index_line, build_index_line
from akt.recall import recall, tokenize


class RecallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        self._add("webapp", "auth-token-refresh", "Lazy token refresh on 401", "auth, token")
        self._add("api", "login-retry", "Retry login backoff", "login, retry")
        self._add("foo", "csv-export", "Stream CSV export", "csv, export")

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, repo, slug, summary, keys):
        meta = {"repo": repo, "slug": slug, "summary": summary, "keys": keys}
        append_index_line(self.kb, build_index_line(meta, "stories/{}/2026-06-05-{}/story.md".format(repo, slug)))

    def test_tokenize(self):
        self.assertEqual(tokenize("Lazy token-refresh, 401!"), ["lazy", "token", "refresh", "401"])

    def test_recall_ranks_by_overlap(self):
        results = recall(self.kb, "how do I handle token auth", limit=3)
        self.assertEqual(results[0]["slug"], "auth-token-refresh")

    def test_recall_excludes_zero_score(self):
        results = recall(self.kb, "token auth", limit=5)
        slugs = [r["slug"] for r in results]
        self.assertIn("auth-token-refresh", slugs)
        self.assertNotIn("csv-export", slugs)

    def test_recall_respects_limit(self):
        results = recall(self.kb, "login token csv export retry", limit=2)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_recall -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.recall'`.

- [ ] **Step 3: Implement `akt/recall.py`**

```python
"""Recall: rank INDEX.md entries against a free-text query.

This is the single seam behind which retrieval lives: query -> ranked story paths.
Today it is keyword overlap; it can later become vector search without changing
callers or artifacts.
"""
import re

from akt.index import read_index_lines, parse_index_line

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return _TOKEN.findall(text.lower())


def _haystack(entry):
    tokens = set(tokenize(entry["summary"]))
    tokens |= set(tokenize(entry["repo"]))
    tokens |= set(tokenize(entry["slug"]))
    for key in entry["keys"]:
        tokens |= set(tokenize(key))
    return tokens


def score(query_tokens, entry):
    hay = _haystack(entry)
    return sum(1 for qt in set(query_tokens) if qt in hay)


def recall(kb_path, query, limit=3):
    qtokens = tokenize(query)
    scored = []
    for line in read_index_lines(kb_path):
        entry = parse_index_line(line)
        if not entry:
            continue
        s = score(qtokens, entry)
        if s > 0:
            scored.append((s, entry))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["path"]))
    return [entry for _, entry in scored[:limit]]
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_recall -v`
Expected: 4 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/recall.py tests/test_recall.py
git commit -m "feat(akt): keyword-scored recall behind query->paths seam"
```

---

### Task 7: Story lifecycle (start / end-session / finish)

**Files:**
- Create: `akt/story.py`
- Test: `tests/test_story.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_story.py`:

```python
import tempfile
import unittest
from pathlib import Path

from akt.frontmatter import parse_frontmatter
from akt.index import read_index_lines, parse_index_line
from akt.story import start_story, end_session, finish_story


class StoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        (self.kb / "stories").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_story_scaffolds(self):
        d = start_story(self.kb, "webapp", "Auth Token Refresh", "2026-06-05")
        self.assertTrue((d / "story.md").exists())
        self.assertTrue((d / "sessions" / "01.md").exists())
        meta, _ = parse_frontmatter((d / "story.md").read_text())
        self.assertEqual(meta["repo"], "webapp")
        self.assertEqual(meta["slug"], "auth-token-refresh")
        self.assertEqual(meta["date"], "2026-06-05")

    def test_start_story_rejects_duplicate(self):
        start_story(self.kb, "webapp", "Auth Token Refresh", "2026-06-05")
        with self.assertRaises(FileExistsError):
            start_story(self.kb, "webapp", "Auth Token Refresh", "2026-06-05")

    def test_end_session_numbers_sequentially(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        f2 = end_session(d, "State: midway\nDone: x\nNext: y\nWatch out: z\n")
        self.assertEqual(f2.name, "02.md")
        self.assertIn("midway", f2.read_text())

    def test_finish_story_writes_body_and_indexes(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        body = (
            "---\nrepo: webapp\nslug: auth\ndate: 2026-06-05\n"
            "summary: Lazy refresh on 401\nkeys: auth, token\n---\n"
            "## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n## Links\n"
        )
        line = finish_story(self.kb, d, body)
        self.assertIn("[webapp/auth]", line)
        lines = read_index_lines(self.kb)
        self.assertEqual(len(lines), 1)
        self.assertEqual(parse_index_line(lines[0])["summary"], "Lazy refresh on 401")

    def test_finish_story_rejects_missing_sections(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        bad = "---\nrepo: webapp\nslug: auth\nsummary: s\nkeys: k\n---\n## Problem\nonly\n"
        with self.assertRaises(ValueError):
            finish_story(self.kb, d, bad)

    def test_finish_story_rejects_empty_summary(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        bad = "---\nrepo: webapp\nslug: auth\nsummary:\nkeys: k\n---\n## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n"
        with self.assertRaises(ValueError):
            finish_story(self.kb, d, bad)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_story -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.story'`.

- [ ] **Step 3: Implement `akt/story.py`**

```python
"""Story lifecycle: start, per-session handoff, finish (distill + index)."""
from pathlib import Path

from akt.frontmatter import build_frontmatter, parse_frontmatter
from akt.paths import slugify, story_dir, next_session_number, rel_to_kb
from akt.index import build_index_line, append_index_line

_STORY_TEMPLATE = """

## Problem
{title}

## Decisions
- <decision> — because <why> — rejected <alternative>

## Outcome
<gotchas, what to watch>

## Links
"""

_SESSION_TEMPLATE = """# Session {n}

State:
Done:
Next:
Watch out:
"""

_REQUIRED_SECTIONS = ["## Problem", "## Decisions", "## Outcome"]


def start_story(kb_path, repo, title, date):
    slug = slugify(title)
    d = story_dir(kb_path, repo, date, slug)
    if d.exists():
        raise FileExistsError(str(d))
    (d / "sessions").mkdir(parents=True)
    meta = {"repo": repo, "slug": slug, "date": date, "summary": "", "keys": ""}
    (d / "story.md").write_text(build_frontmatter(meta) + _STORY_TEMPLATE.format(title=title))
    (d / "sessions" / "01.md").write_text(_SESSION_TEMPLATE.format(n=1))
    return d


def end_session(story_path, body):
    sessions = Path(story_path) / "sessions"
    sessions.mkdir(exist_ok=True)
    n = next_session_number(sessions)
    f = sessions / "{:02d}.md".format(n)
    f.write_text(body if body and body.strip() else _SESSION_TEMPLATE.format(n=n))
    return f


def finish_story(kb_path, story_path, body=None):
    story_path = Path(story_path)
    story_md = story_path / "story.md"
    if body is not None:
        story_md.write_text(body)
    text = story_md.read_text()
    missing = [s for s in _REQUIRED_SECTIONS if s not in text]
    if missing:
        raise ValueError("story.md missing sections: {}".format(missing))
    meta, _ = parse_frontmatter(text)
    if not meta.get("summary"):
        raise ValueError("story.md frontmatter missing 'summary'")
    line = build_index_line(meta, rel_to_kb(kb_path, story_md))
    append_index_line(kb_path, line)
    return line
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_story -v`
Expected: 6 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/story.py tests/test_story.py
git commit -m "feat(akt): story lifecycle start/end-session/finish"
```

---

### Task 8: Knowledge base init

**Files:**
- Create: `akt/init.py`
- Test: `tests/test_init.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_init.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_init -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.init'`.

- [ ] **Step 3: Implement `akt/init.py`**

```python
"""Initialize a personal knowledge base and record it in config."""
from pathlib import Path

from akt import config
from akt.index import write_index

_AGENTS_SEED = "# Global Rules\n\nGraduated patterns (personal, cross-repo). Generated entries carry provenance.\n"


def init_kb(kb_path, config_path=None):
    kb = Path(kb_path)
    (kb / "stories").mkdir(parents=True, exist_ok=True)
    agents = kb / "AGENTS.md"
    if not agents.exists():
        agents.write_text(_AGENTS_SEED)
    if not (kb / "INDEX.md").exists():
        write_index(kb, [])
    config.set_value("knowledge_base_path", str(kb), config_path)
    config.set_value("install_mode", "minimal", config_path)
    return kb
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_init -v`
Expected: 3 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/init.py tests/test_init.py
git commit -m "feat(akt): knowledge base init + config bootstrap"
```

---

### Task 9: CLI dispatch + `__main__`

**Files:**
- Create: `akt/cli.py`
- Create: `akt/__main__.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_cli -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.cli'`.

- [ ] **Step 3: Implement `akt/cli.py`**

```python
"""Command-line dispatch for the AKT kernel."""
import argparse
import sys
from datetime import date as _date

from akt import config
from akt import story as story_mod
from akt import recall as recall_mod
from akt import index as index_mod
from akt import init as init_mod


def _require_kb():
    kb = config.get("knowledge_base_path")
    if not kb:
        sys.stderr.write("No knowledge_base_path configured. Run: python3 -m akt init <path>\n")
        sys.exit(2)
    return kb


def build_parser():
    p = argparse.ArgumentParser(prog="akt")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="create a knowledge base and record it in config")
    pi.add_argument("path")

    ps = sub.add_parser("start-story", help="scaffold a new story")
    ps.add_argument("repo")
    ps.add_argument("title")
    ps.add_argument("--date", default=None)

    pe = sub.add_parser("end-session", help="write a session handoff from stdin")
    pe.add_argument("story_path")

    pf = sub.add_parser("finish-story", help="distill story.md (from stdin) and index it")
    pf.add_argument("story_path")
    pf.add_argument("--stdin", action="store_true", help="read distilled story.md body from stdin")

    pr = sub.add_parser("recall", help="print ranked story paths for a query")
    pr.add_argument("query")
    pr.add_argument("--limit", type=int, default=3)

    sub.add_parser("reindex", help="rebuild INDEX.md from all story.md files")
    return p


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)

    if args.cmd == "init":
        print(init_mod.init_kb(args.path))
        return 0

    if args.cmd == "start-story":
        d = args.date or _date.today().isoformat()
        print(story_mod.start_story(_require_kb(), args.repo, args.title, d))
        return 0

    if args.cmd == "end-session":
        body = "" if sys.stdin.isatty() else sys.stdin.read()
        print(story_mod.end_session(args.story_path, body))
        return 0

    if args.cmd == "finish-story":
        body = sys.stdin.read() if args.stdin else None
        print(story_mod.finish_story(_require_kb(), args.story_path, body))
        return 0

    if args.cmd == "recall":
        for entry in recall_mod.recall(_require_kb(), args.query, args.limit):
            print(entry["path"])
        return 0

    if args.cmd == "reindex":
        lines = index_mod.reindex(_require_kb())
        print("{} stories indexed".format(len(lines)))
        return 0

    return 1
```

- [ ] **Step 4: Implement `akt/__main__.py`**

```python
from akt.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m unittest tests.test_cli -v`
Expected: 2 tests PASS, OK.

- [ ] **Step 6: Run the FULL suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests across all modules PASS, OK.

- [ ] **Step 7: Commit**

```bash
git add akt/cli.py akt/__main__.py tests/test_cli.py
git commit -m "feat(akt): CLI dispatch over all kernel subcommands"
```

---

### Task 10: Thin slash commands

These wrap the CLI and carry the LLM judgment. They are not unit-tested (they are prompts); Task 11 verifies them end-to-end.

**Files:**
- Create: `.claude/commands/start-story.md`
- Create: `.claude/commands/end-session.md`
- Create: `.claude/commands/finish-story.md`
- Create: `.claude/commands/recall.md`

- [ ] **Step 1: Write `.claude/commands/recall.md`**

````markdown
---
description: Surface relevant past stories before starting work
allowed-tools: Bash, Read
---

# Recall

Given the task you are about to start, surface relevant prior decisions.

1. Run:
   ```bash
   python3 -m akt recall "<one-line description of the task>"
   ```
   It prints up to 3 story paths (relative to the knowledge base).
2. Resolve each against `knowledge_base_path` (from `~/.claude/akt-config.md`) and Read the `story.md`.
3. Judge true relevance yourself — keyword overlap is only a prefilter. Summarize the prior decisions that actually bear on this task before proceeding.
````

- [ ] **Step 2: Write `.claude/commands/start-story.md`**

````markdown
---
description: Start a new story in the knowledge base
allowed-tools: Bash
---

# Start Story

1. Determine the current repo name (the basename of the repo root) and a short title for the task.
2. Run:
   ```bash
   python3 -m akt start-story <repo> "<short title>"
   ```
   It prints the created story directory and seeds `story.md` + `sessions/01.md`.
3. Keep brief notes as you work; you will hand them off with `/end-session`.
````

- [ ] **Step 3: Write `.claude/commands/end-session.md`**

````markdown
---
description: Write a session handoff so the next agent picks up cleanly
allowed-tools: Bash
---

# End Session

Write a concise handoff for the next agent on THIS story, then persist it.

Pipe the handoff (State / Done / Next / Watch out) into the CLI, which numbers the file:

```bash
python3 -m akt end-session <story_path> <<'EOF'
# Session N

State: <where things stand>
Done: <what this session accomplished>
Next: <immediate next steps>
Watch out: <blockers / open questions>
EOF
```
````

- [ ] **Step 4: Write `.claude/commands/finish-story.md`**

````markdown
---
description: Distill the finished story and add it to the index
allowed-tools: Bash, Read
---

# Finish Story

1. Read all `sessions/NN.md` under `<story_path>/sessions` and the work's diff.
2. Write the distilled `story.md` body. It MUST include frontmatter and the required sections:
   ```
   ---
   repo: <repo>
   slug: <slug>
   date: <YYYY-MM-DD>
   summary: <the key decision + because, one line — this is what recall matches on>
   keys: <comma, separated, keywords>
   ---
   ## Problem
   ## Decisions
   - <decision> — because <why> — rejected <alternative>
   ## Outcome
   ## Links
   ```
3. Pipe it in; the CLI validates required sections + non-empty summary, then appends the INDEX.md line:
   ```bash
   python3 -m akt finish-story <story_path> --stdin <<'EOF'
   <the full story.md content above>
   EOF
   ```
4. Commit the knowledge repo (the `knowledge_base_path`), e.g. `git -C <kb> add -A && git -C <kb> commit -m "story: <repo>/<slug>"`.
````

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/start-story.md .claude/commands/end-session.md .claude/commands/finish-story.md .claude/commands/recall.md
git commit -m "feat(akt): thin slash commands wrapping the kernel CLI"
```

---

### Task 11: End-to-end manual verification

Proves the kernel works as a whole against a throwaway knowledge base. No code; a verification script you run and observe.

**Files:** none (temporary KB under `/tmp`).

- [ ] **Step 1: Run the full lifecycle against a temp KB**

```bash
export AKT_CONFIG="$(mktemp -d)/akt-config.md"
KB="$(mktemp -d)/knowledge"
python3 -m akt init "$KB"
STORY=$(python3 -m akt start-story webapp "Auth Token Refresh" --date 2026-06-05)
echo "story dir: $STORY"
python3 -m akt end-session "$STORY" <<'EOF'
# Session 2
State: refactor done
Done: moved to lazy-on-401
Next: add tests
Watch out: token clock skew
EOF
python3 -m akt finish-story "$STORY" --stdin <<'EOF'
---
repo: webapp
slug: auth-token-refresh
date: 2026-06-05
summary: Moved refresh from cron to lazy-on-401 to stop thundering-herd reauth
keys: auth, token, rate-limit, webapp
---
## Problem
Cron-based refresh caused thundering-herd reauth.
## Decisions
- Lazy refresh on 401 — because cron drift synchronized clients — rejected fixed-interval cron
## Outcome
Reauth storms gone; watch clock skew.
## Links
EOF
```

Expected: `init` prints the KB path; `start-story` prints a path ending `2026-06-05-auth-token-refresh`; `finish-story` prints the index line `- [webapp/auth-token-refresh] Moved refresh ... | keys: ... | stories/...`.

- [ ] **Step 2: Verify recall surfaces it**

```bash
python3 -m akt recall "how do I refresh an auth token"
ls "$STORY/sessions"
cat "$KB/INDEX.md"
```

Expected: recall prints `stories/webapp/2026-06-05-auth-token-refresh/story.md`; `sessions/` contains `01.md` and `02.md`; `INDEX.md` has the one story line under the generated header.

- [ ] **Step 3: Verify reindex is stable**

```bash
python3 -m akt reindex
cat "$KB/INDEX.md"
```

Expected: `1 stories indexed`; `INDEX.md` identical to before (reindex from `story.md` reproduces the appended line).

- [ ] **Step 4: Clean up**

```bash
unset AKT_CONFIG
```

- [ ] **Step 5: Final full-suite run + tag**

```bash
python3 -m unittest discover -s tests -v
git tag kernel-mvp
```

Expected: all tests PASS. Kernel MVP complete.

---

## Self-Review

**1. Spec coverage (kernel-MVP scope):**
- Markdown-is-truth + derived disposable `INDEX.md` → Tasks 5, 8 (write_index header "Generated — do not hand-edit"), 11 (reindex stability).
- Cross-repo recall via `INDEX.md`, the `query → paths` seam → Task 6 (`recall.py`), Task 10 (`recall.md` does final relevance).
- Capture lifecycle `start-story` / `end-session` / `finish-story`, tight `story.md` (Problem/Decisions/Outcome/Links, decision→because→rejected) → Task 7, Task 10.
- Layout (`stories/<repo>/<date>-<slug>/story.md` + `sessions/NN.md`, `AGENTS.md`, `INDEX.md`) → Tasks 4, 7, 8.
- Config (`~/.claude/akt-config.md`, `knowledge_base_path`, `install_mode: minimal`) → Tasks 3, 8.
- Zero-infra, no install → `python3 -m akt`, stdlib only (header).
- Freshness via append-at-finish + `reindex` → Tasks 5, 9, 11.
- *Deferred (correctly out of kernel scope, per spec build order):* learning protocol / `AGENTS.md` graduation (Plan 2), swarm + workflow toolkit (Plan 3), plugin distribution + full install modes (Plan 4). `init` provides the minimal bootstrap the kernel needs.

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to" — every code and test step contains complete content. The template strings inside `story.py` (`<decision> — because ...`) are intentional file *content* the tool writes, not plan placeholders.

**3. Type/name consistency:** Verified across tasks — `parse_frontmatter`/`build_frontmatter`/`split_keys`, `build_index_line`/`parse_index_line`/`read_index_lines`/`write_index`/`append_index_line`/`reindex`, `recall`/`tokenize`/`score`, `start_story`/`end_session`/`finish_story`, `init_kb`, `read_config`/`write_config`/`get`/`set_value`. Index line format and frontmatter keys (`repo`/`slug`/`date`/`summary`/`keys`) are identical everywhere they appear. `recall` returns entry dicts with a `path` key, which `cli.py` prints — consistent.
