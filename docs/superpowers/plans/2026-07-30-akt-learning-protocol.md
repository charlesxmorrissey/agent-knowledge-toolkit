# AKT Learning Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recurring lessons accrue evidence in a `LEARNINGS.md` ledger and graduate — through a human gate — into always-on `AGENTS.md` rules with provenance.

**Architecture:** A new `akt/learn.py` module owns the ledger (parse/build/read/write plus add/reinforce/graduate/wont/prune), following the `index.py` idiom; `cli.py` gains an `akt learn` subcommand family whose mutating commands commit the KB atomically via `gitkb`. Judgment (lesson matching, rule wording) lives in slash-command prose: `finish-story`/`update-story` gain a learnings pass, and a new `/mine-learnings` bootstraps the ledger from the existing corpus. `akt install` wires the KB's `AGENTS.md` into `~/.claude/CLAUDE.md` so graduated global rules auto-load.

**Tech Stack:** Python 3.9 stdlib only (`argparse`, `pathlib`, `re`, `datetime`, `unittest`). Run as `python3 -m akt`; test with `python3 -m unittest discover -s tests`.

**Spec:** `docs/superpowers/specs/2026-07-30-akt-learning-protocol-design.md`

## Global Constraints

- Python 3.9, stdlib only — no third-party deps.
- Absolute imports everywhere (`from akt.learn import ...`), in package and tests.
- The CLI never writes outside the knowledge base. Repo-local rule writes are the agent's job, in-repo, at capture time.
- Every mutating `learn` command commits (and pushes, if a remote exists) the KB via `gitkb.commit_kb` — same atomicity as `finish-story`.
- Config keys (in `~/.claude/akt-config.md`, `key: value` lines): `learn_threshold` (default 3), `prune_days` (default 90).
- Ledger entry statuses: `candidate` | `graduated-global` | `graduated-repo` | `wont-graduate`. Nothing is ever deleted from the ledger.
- Scope is derived, never stored: 1 distinct repo across `stories` → repo-local, ≥2 → global.
- Story references are `<repo>/<date>-<slug>` (story dir relative to `stories/`).
- Branching: Task 1 ships as its own PR first (`fix/index-hygiene`) — the learning layer mines the corpus and needs clean data. Task 2 operates on the private KB (no repo PR). Tasks 3–8 go on `feat/learning-protocol`.

---

## File Structure

- `akt/learn.py` — NEW: ledger parse/build/read/write, scope derivation, add/reinforce/graduate/wont/prune, rule-block builder.
- `akt/story.py` — MODIFY: `finish_story` and `update_story` validate non-empty `repo`/`slug`/`keys` frontmatter.
- `akt/index.py` — MODIFY: dedupe in `append_index_line` tolerates malformed lines.
- `akt/cli.py` — MODIFY: `learn` subcommand family dispatch.
- `akt/install.py` — MODIFY: generalize `_ensure_import`; add the KB `AGENTS.md` import.
- `.claude/commands/finish-story.md`, `.claude/commands/update-story.md` — MODIFY: learnings pass.
- `.claude/commands/mine-learnings.md` — NEW: bootstrap/re-sweep prompt.
- `claude/akt-rule.md` — MODIFY: learnings-pass lines in the capture section.
- `tests/test_learn.py` — NEW. `tests/test_story.py`, `tests/test_index.py`, `tests/test_cli.py`, `tests/test_install.py` — MODIFY.
- `README.md` — MODIFY: roadmap + usage.

---

### Task 1: Index hygiene — frontmatter validation + tolerant dedupe (own PR, ships first)

The KB index is degraded: entries like `- [/] ...` (empty repo/slug/keys) fail the index-line regex, so path-dedupe never matches them and identical lines accumulate. Fix the two code paths that allowed it.

**Files:**
- Modify: `akt/story.py` (`finish_story`, `update_story`)
- Modify: `akt/index.py` (`append_index_line`)
- Test: `tests/test_story.py`, `tests/test_index.py`

**Interfaces:**
- Consumes: `parse_frontmatter` from `akt.frontmatter`; existing `_REQUIRED_SECTIONS`.
- Produces: `finish_story` raises `ValueError` when frontmatter `repo`/`slug`/`keys` (or `summary`) is empty; `update_story` raises `ValueError` when the existing story's frontmatter is incomplete; `append_index_line(kb_path, line)` dedupes by the final `| <path>` field even for lines the regex can't parse.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b fix/index-hygiene
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_story.py` inside `class StoryTest`:

```python
    def test_finish_story_rejects_empty_repo_slug_keys(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        for missing in ("repo", "slug", "keys"):
            meta = {"repo": "webapp", "slug": "auth", "date": "2026-06-05",
                    "summary": "s", "keys": "a, b"}
            meta[missing] = ""
            bad = (
                "---\n" + "\n".join("{}: {}".format(k, v) for k, v in meta.items()) + "\n---\n"
                "## Problem\nx\n## Decisions\n- a\n## Outcome\nok\n"
            )
            with self.assertRaises(ValueError, msg=missing):
                finish_story(self.kb, d, bad)

    def test_update_story_rejects_incomplete_frontmatter(self):
        d = start_story(self.kb, "webapp", "Auth", "2026-06-05")
        (d / "story.md").write_text(
            "---\nsummary: legacy story with no repo/slug/keys\n---\n## Problem\nx\n"
        )
        with self.assertRaises(ValueError):
            update_story(d, "new info", "2026-07-30")
```

Update the import at the top of `tests/test_story.py` to include `update_story`:

```python
from akt.story import start_story, end_session, finish_story, update_story
```

(If it already imports `update_story`, leave it.)

Append to `tests/test_index.py` inside `class IndexTest`:

```python
    def test_append_dedupes_malformed_lines_by_path(self):
        # Legacy lines with empty repo/slug fail the parse regex; dedupe must
        # still match them on the trailing path field so they can't accumulate.
        p = "stories/heyflow/2026-07-29-overnight-batch/story.md"
        malformed = "- [/] Overnight batch | keys:  | " + p
        append_index_line(self.kb, malformed)
        append_index_line(self.kb, malformed)
        good = build_index_line(
            {"repo": "heyflow", "slug": "overnight-batch",
             "summary": "Overnight batch", "keys": "heyflow"}, p)
        append_index_line(self.kb, good)
        lines = read_index_lines(self.kb)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], good)
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m unittest tests.test_story tests.test_index -v`
Expected: the three new tests FAIL (no ValueError raised; 2 or 3 index lines instead of 1). All pre-existing tests PASS.

- [ ] **Step 4: Implement the validation in `akt/story.py`**

Add a helper above `finish_story` and use it in both functions:

```python
_REQUIRED_META = ["repo", "slug", "summary", "keys"]


def _validate_meta(meta):
    missing = [k for k in _REQUIRED_META if not meta.get(k, "").strip()]
    if missing:
        raise ValueError("story.md frontmatter missing: {}".format(missing))
```

In `finish_story`, replace the summary-only check:

```python
    meta, _ = parse_frontmatter(text)
    if not meta.get("summary"):
        raise ValueError("story.md frontmatter missing 'summary'")
```

with:

```python
    meta, _ = parse_frontmatter(text)
    _validate_meta(meta)
```

In `update_story`, after the `story_md.exists()` check and before writing, add:

```python
    meta, _ = parse_frontmatter(story_md.read_text())
    _validate_meta(meta)
```

(Keep the existing empty-body check; note `update_story` now reads the file once for validation — reuse that `text` for the append to avoid a second read.)

- [ ] **Step 5: Implement tolerant dedupe in `akt/index.py`**

Replace `append_index_line` with:

```python
def _line_path(line):
    """Dedupe key: the final `| <path>` field. Works even for legacy lines the
    parse regex rejects (e.g. empty repo/slug), so they can't accumulate."""
    line = line.strip()
    return line.rsplit(" | ", 1)[-1] if " | " in line else None


def append_index_line(kb_path, line):
    new_path = _line_path(line)
    kept = []
    for existing in read_index_lines(kb_path):
        if new_path and _line_path(existing) == new_path:
            continue
        kept.append(existing)
    kept.append(line)
    write_index(kb_path, kept)
```

- [ ] **Step 6: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests PASS (including the three new ones).

- [ ] **Step 7: Commit and open the PR**

```bash
git add akt/story.py akt/index.py tests/test_story.py tests/test_index.py
git commit -m "fix: validate story frontmatter + dedupe malformed index lines"
git push -u origin fix/index-hygiene
gh pr create --title "fix: index hygiene — frontmatter validation + tolerant dedupe" \
  --body "Prevents the '- [/]' malformed/duplicated INDEX.md lines: finish-story/update-story now require non-empty repo/slug/keys, and append dedupe matches on the trailing path field even for lines the regex can't parse. Precursor to the learning protocol (docs/superpowers/specs/2026-07-30-akt-learning-protocol-design.md §5)."
```

---

### Task 2: Repair the knowledge base corpus (operates on the KB, not this repo)

Fix the ~12 stories whose frontmatter lacks `repo`/`slug`/`keys`, then rebuild the index. Requires Task 1 merged (or checked out) so the fixed validation is what future captures hit.

**Files:** none in this repo. Edits happen in the KB at `knowledge_base_path` (read it from `~/.claude/akt-config.md`).

**Interfaces:**
- Consumes: `akt reindex` CLI; `gitkb`-style manual commit of the KB.
- Produces: an `INDEX.md` with zero `- [/]` lines and zero duplicate paths — the corpus `/mine-learnings` (Task 7) will mine.

- [ ] **Step 1: List the broken stories**

```bash
KB=$(grep knowledge_base_path ~/.claude/akt-config.md | cut -d' ' -f2)
grep -n '^- \[/\]' "$KB/INDEX.md"
```

Expected: ~12 lines; note each trailing story path.

- [ ] **Step 2: Fix each story's frontmatter**

For every listed `story.md`: set `repo` to the story dir's parent name, `slug` to the dir name minus the leading `YYYY-MM-DD-`, `date` to that leading date, keep the existing `summary`, and distill 5–15 comma-separated `keys` from the summary/body (this is judgment — read the story). Example: for `stories/sumo/2026-07-14-abandoned-cart-leadid-deep-link-through-booking-flow/story.md`:

```
---
repo: sumo
slug: abandoned-cart-leadid-deep-link-through-booking-flow
date: 2026-07-14
summary: <keep the existing summary line unchanged>
keys: sumo, abandoned-cart, leadid, formcrafts, salesforce, deep-link, url-param
---
```

Do not touch the story body.

- [ ] **Step 3: Rebuild the index and verify**

```bash
akt reindex
grep -c '^- \[/\]' "$KB/INDEX.md"            # expected: 0
awk -F' \\| ' '{print $NF}' "$KB/INDEX.md" | sort | uniq -d   # expected: empty
```

- [ ] **Step 4: Commit the KB**

```bash
git -C "$KB" add -A && git -C "$KB" commit -m "repair: restore repo/slug/keys frontmatter on legacy stories; reindex" && git -C "$KB" push
```

---

### Task 3: Ledger core — parse/build/read/write/scope (`akt/learn.py`)

**Files:**
- Create: `akt/learn.py`
- Test: `tests/test_learn.py`

**Interfaces:**
- Consumes: nothing beyond stdlib (`re`, `pathlib`).
- Produces (later tasks rely on these exact names):
  - `LEARNINGS_FILE = "LEARNINGS.md"`
  - `build_learning_line(entry) -> str`
  - `parse_learning_line(line) -> dict | None` — dict keys: `id`, `rule`, `hits` (int), `status`, `last` (ISO date str), `stories` (list of str)
  - `read_learnings(kb_path) -> list[dict]`
  - `write_learnings(kb_path, entries) -> None`
  - `scope(entry) -> "repo" | "global"`

- [ ] **Step 1: Create the branch**

```bash
git checkout main && git pull && git checkout -b feat/learning-protocol
```

- [ ] **Step 2: Write the failing tests**

`tests/test_learn.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m unittest tests.test_learn -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'akt.learn'`.

- [ ] **Step 4: Implement the core in `akt/learn.py`**

```python
"""LEARNINGS.md — the evidence ledger for the learning protocol.

Source of truth (NOT derived): hits and statuses can't be rebuilt from
stories. One parseable line per candidate, in the index.py idiom.
"""
import re
from pathlib import Path

LEARNINGS_FILE = "LEARNINGS.md"
_HEADER = "# Learnings\n\nOne entry per candidate. Managed by `akt learn` — do not hand-edit.\n"
_LINE = re.compile(
    r"^- \[([a-z0-9-]+)\] (.*) \| hits: (\d+) \| status: ([a-z-]+)"
    r" \| last: (\d{4}-\d{2}-\d{2}) \| stories: (.*)$"
)

STATUSES = ("candidate", "graduated-global", "graduated-repo", "wont-graduate")


def build_learning_line(entry):
    return "- [{}] {} | hits: {} | status: {} | last: {} | stories: {}".format(
        entry["id"], entry["rule"], entry["hits"], entry["status"],
        entry["last"], ", ".join(entry["stories"]),
    )


def parse_learning_line(line):
    m = _LINE.match(line.strip())
    if not m:
        return None
    return {
        "id": m.group(1),
        "rule": m.group(2),
        "hits": int(m.group(3)),
        "status": m.group(4),
        "last": m.group(5),
        "stories": [s.strip() for s in m.group(6).split(",") if s.strip()],
    }


def _ledger_file(kb_path):
    return Path(kb_path) / LEARNINGS_FILE


def read_learnings(kb_path):
    f = _ledger_file(kb_path)
    if not f.exists():
        return []
    entries = []
    for line in f.read_text().splitlines():
        parsed = parse_learning_line(line)
        if parsed:
            entries.append(parsed)
    return entries


def write_learnings(kb_path, entries):
    body = "\n".join(build_learning_line(e) for e in entries)
    _ledger_file(kb_path).write_text(_HEADER + "\n" + body + ("\n" if body else ""))


def scope(entry):
    """Derived, never stored: 1 distinct repo -> repo-local, >=2 -> global."""
    repos = {s.split("/", 1)[0] for s in entry["stories"]}
    return "global" if len(repos) >= 2 else "repo"
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m unittest tests.test_learn -v`
Expected: 6 tests PASS, OK.

- [ ] **Step 6: Commit**

```bash
git add akt/learn.py tests/test_learn.py
git commit -m "feat(akt): LEARNINGS.md ledger core — parse/build/read/write/scope"
```

---

### Task 4: Ledger operations — add / reinforce / graduate / wont / prune

**Files:**
- Modify: `akt/learn.py`
- Test: `tests/test_learn.py`

**Interfaces:**
- Consumes: Task 3's core functions.
- Produces (CLI in Task 5 calls these exact signatures; all raise `ValueError` on bad input):
  - `add(kb_path, learn_id, rule, story, today) -> dict` — new entry, hits 1.
  - `reinforce(kb_path, learn_id, story, today, threshold) -> (dict, str | None)` — updated entry + `PROPOSE:` line (or None).
  - `graduate(kb_path, learn_id) -> (dict, str)` — updated entry + rule block; global scope also appends the block to the KB's `AGENTS.md`.
  - `wont(kb_path, learn_id) -> dict`
  - `prune_report(kb_path, today, cutoff_days) -> (list[dict], list[dict])` — (stale candidates, stale graduated).
  - `rule_block(entry) -> str`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_learn.py` (add `add, reinforce, graduate, wont, prune_report, rule_block` to the `from akt.learn import (...)` list):

```python
class LedgerOpsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_starts_at_one(self):
        e = add(self.kb, "new-lesson", "Do the thing first", "heyflow/2026-07-30-x", "2026-07-30")
        self.assertEqual(e["hits"], 1)
        self.assertEqual(e["status"], "candidate")
        self.assertEqual(read_learnings(self.kb)[0]["id"], "new-lesson")

    def test_add_rejects_duplicate_id_and_pipe(self):
        add(self.kb, "new-lesson", "Do the thing", "heyflow/2026-07-30-x", "2026-07-30")
        with self.assertRaises(ValueError):
            add(self.kb, "new-lesson", "Again", "sumo/2026-07-30-y", "2026-07-30")
        with self.assertRaises(ValueError):
            add(self.kb, "piped", "bad | rule", "sumo/2026-07-30-y", "2026-07-30")

    def test_reinforce_bumps_and_dedupes(self):
        add(self.kb, "l", "Rule", "heyflow/2026-07-01-a", "2026-07-01")
        e, prop = reinforce(self.kb, "l", "heyflow/2026-07-02-b", "2026-07-02", 3)
        self.assertEqual((e["hits"], e["last"]), (2, "2026-07-02"))
        self.assertIsNone(prop)
        e, _ = reinforce(self.kb, "l", "heyflow/2026-07-02-b", "2026-07-03", 3)
        self.assertEqual(e["stories"].count("heyflow/2026-07-02-b"), 1)

    def test_reinforce_proposes_at_threshold_and_keeps_proposing(self):
        add(self.kb, "l", "Rule", "heyflow/2026-07-01-a", "2026-07-01")
        reinforce(self.kb, "l", "sumo/2026-07-02-b", "2026-07-02", 3)
        e, prop = reinforce(self.kb, "l", "webapp/2026-07-03-c", "2026-07-03", 3)
        self.assertIn("PROPOSE:", prop)
        self.assertIn("GLOBAL", prop)
        self.assertIn("akt learn graduate l", prop)
        _, again = reinforce(self.kb, "l", "api/2026-07-04-d", "2026-07-04", 3)
        self.assertIn("PROPOSE:", again)

    def test_reinforce_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            reinforce(self.kb, "nope", "heyflow/2026-07-30-x", "2026-07-30", 3)

    def test_graduate_global_appends_to_agents_md(self):
        add(self.kb, "l", "Rule text", "heyflow/2026-07-01-a", "2026-07-01")
        reinforce(self.kb, "l", "sumo/2026-07-02-b", "2026-07-02", 3)
        e, block = graduate(self.kb, "l")
        self.assertEqual(e["status"], "graduated-global")
        agents = (self.kb / "AGENTS.md").read_text()
        self.assertIn("- Rule text", agents)
        self.assertIn("<!-- akt: l | 2 hits | heyflow/2026-07-01-a, sumo/2026-07-02-b -->", agents)
        self.assertEqual(block, rule_block(e))

    def test_graduate_repo_local_writes_nothing_outside_ledger(self):
        add(self.kb, "l", "Rule text", "heyflow/2026-07-01-a", "2026-07-01")
        e, block = graduate(self.kb, "l")
        self.assertEqual(e["status"], "graduated-repo")
        self.assertFalse((self.kb / "AGENTS.md").exists())
        self.assertIn("- Rule text", block)

    def test_graduate_twice_raises(self):
        add(self.kb, "l", "Rule", "heyflow/2026-07-01-a", "2026-07-01")
        graduate(self.kb, "l")
        with self.assertRaises(ValueError):
            graduate(self.kb, "l")

    def test_wont_suppresses_proposals(self):
        add(self.kb, "l", "Rule", "heyflow/2026-07-01-a", "2026-07-01")
        e = wont(self.kb, "l")
        self.assertEqual(e["status"], "wont-graduate")
        _, prop = reinforce(self.kb, "l", "sumo/2026-07-02-b", "2026-07-02", 1)
        self.assertIsNone(prop)

    def test_prune_report_date_cutoff(self):
        add(self.kb, "old", "Old rule", "heyflow/2026-01-01-a", "2026-01-01")
        add(self.kb, "fresh", "Fresh rule", "sumo/2026-07-29-b", "2026-07-29")
        add(self.kb, "grad", "Grad rule", "heyflow/2026-01-01-c", "2026-01-01")
        graduate(self.kb, "grad")
        stale_candidates, stale_graduated = prune_report(self.kb, "2026-07-30", 90)
        self.assertEqual([e["id"] for e in stale_candidates], ["old"])
        self.assertEqual([e["id"] for e in stale_graduated], ["grad"])
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_learn -v`
Expected: `ImportError` on the new names.

- [ ] **Step 3: Implement the operations in `akt/learn.py`**

Append (add `from datetime import date as _date, timedelta` to the imports):

```python
AGENTS_FILE = "AGENTS.md"


def rule_block(entry):
    """The graduated-rule format: rule text agents read, provenance in a comment."""
    return "- {}\n  <!-- akt: {} | {} hits | {} -->".format(
        entry["rule"], entry["id"], entry["hits"], ", ".join(entry["stories"])
    )


def _find(entries, learn_id):
    for e in entries:
        if e["id"] == learn_id:
            return e
    raise ValueError("no learning with id '{}'".format(learn_id))


def add(kb_path, learn_id, rule, story, today):
    if "|" in rule:
        raise ValueError("rule text must not contain '|'")
    if not re.fullmatch(r"[a-z0-9-]+", learn_id):
        raise ValueError("id must be kebab-case: '{}'".format(learn_id))
    entries = read_learnings(kb_path)
    if any(e["id"] == learn_id for e in entries):
        raise ValueError("duplicate learning id '{}'".format(learn_id))
    entry = {"id": learn_id, "rule": rule, "hits": 1, "status": "candidate",
             "last": today, "stories": [story]}
    entries.append(entry)
    write_learnings(kb_path, entries)
    return entry


def _proposal(entry):
    sc = scope(entry)
    repos = {s.split("/", 1)[0] for s in entry["stories"]}
    where = "GLOBAL ({} hits across {} repos)".format(entry["hits"], len(repos)) \
        if sc == "global" else \
        "REPO-LOCAL to '{}' ({} hits in one repo)".format(next(iter(repos)), entry["hits"])
    return "PROPOSE: graduate '{}' as {} — run: akt learn graduate {}".format(
        entry["id"], where, entry["id"])


def reinforce(kb_path, learn_id, story, today, threshold):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    entry["hits"] += 1
    entry["last"] = today
    if story not in entry["stories"]:
        entry["stories"].append(story)
    write_learnings(kb_path, entries)
    proposal = _proposal(entry) \
        if entry["status"] == "candidate" and entry["hits"] >= threshold else None
    return entry, proposal


def graduate(kb_path, learn_id):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    if entry["status"] != "candidate":
        raise ValueError("'{}' is already {}".format(learn_id, entry["status"]))
    sc = scope(entry)
    entry["status"] = "graduated-global" if sc == "global" else "graduated-repo"
    block = rule_block(entry)
    write_learnings(kb_path, entries)
    if sc == "global":
        agents = Path(kb_path) / AGENTS_FILE
        existing = agents.read_text() if agents.exists() else ""
        prefix = existing.rstrip("\n") + "\n\n" if existing.strip() else ""
        agents.write_text(prefix + block + "\n")
    return entry, block


def wont(kb_path, learn_id):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    entry["status"] = "wont-graduate"
    write_learnings(kb_path, entries)
    return entry


def prune_report(kb_path, today, cutoff_days):
    """Print-only staleness report; never writes. Returns (candidates, graduated)."""
    cutoff = _date.fromisoformat(today) - timedelta(days=cutoff_days)
    stale_candidates, stale_graduated = [], []
    for e in read_learnings(kb_path):
        if _date.fromisoformat(e["last"]) >= cutoff:
            continue
        if e["status"] == "candidate":
            stale_candidates.append(e)
        elif e["status"].startswith("graduated"):
            stale_graduated.append(e)
    return stale_candidates, stale_graduated
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_learn -v`
Expected: 16 tests PASS, OK.

- [ ] **Step 5: Commit**

```bash
git add akt/learn.py tests/test_learn.py
git commit -m "feat(akt): ledger ops — add/reinforce/graduate/wont/prune with threshold proposals"
```

---

### Task 5: CLI — the `akt learn` subcommand family

**Files:**
- Modify: `akt/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 4's functions; `config.get`; `gitkb.commit_kb`; `_require_kb`, `_warn_if_dirty` (existing in `cli.py`).
- Produces: `akt learn add|reinforce|graduate|wont|list|prune` — mutating commands commit the KB; errors exit 2 with the message on stderr; `reinforce` prints the entry line then the `PROPOSE:` line (if any) on stdout.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py` inside `class CliTest` (the class already sets `AKT_CONFIG` and has `self._run`; note `_run` only captures stdout — that's all these assert on):

```python
    def test_learn_add_reinforce_propose_graduate(self):
        self._run(["init", str(self.kb)])
        rc, out = self._run(["learn", "add", "cm6-paste", "Verify bundle bytes after paste",
                             "--story", "heyflow/2026-07-01-a"])
        self.assertEqual(rc, 0)
        self.assertIn("hits: 1", out)

        rc, out = self._run(["learn", "reinforce", "cm6-paste", "--story", "sumo/2026-07-02-b"])
        self.assertEqual(rc, 0)
        self.assertNotIn("PROPOSE:", out)

        rc, out = self._run(["learn", "reinforce", "cm6-paste", "--story", "webapp/2026-07-03-c"])
        self.assertEqual(rc, 0)
        self.assertIn("PROPOSE: graduate 'cm6-paste' as GLOBAL", out)

        rc, out = self._run(["learn", "graduate", "cm6-paste"])
        self.assertEqual(rc, 0)
        self.assertIn("<!-- akt: cm6-paste", out)
        self.assertIn("- Verify bundle bytes after paste", (self.kb / "AGENTS.md").read_text())

    def test_learn_list_filters_by_status(self):
        self._run(["init", str(self.kb)])
        self._run(["learn", "add", "a", "Rule A", "--story", "x/2026-07-01-a"])
        self._run(["learn", "add", "b", "Rule B", "--story", "y/2026-07-01-b"])
        self._run(["learn", "wont", "b"])
        rc, out = self._run(["learn", "list", "--status", "candidate"])
        self.assertEqual(rc, 0)
        self.assertIn("[a]", out)
        self.assertNotIn("[b]", out)

    def test_learn_unknown_id_exits_2(self):
        self._run(["init", str(self.kb)])
        with self.assertRaises(SystemExit) as ctx:
            self._run(["learn", "graduate", "nope"])
        self.assertEqual(ctx.exception.code, 2)

    def test_learn_prune_prints_sections(self):
        self._run(["init", str(self.kb)])
        self._run(["learn", "add", "old", "Old rule", "--story", "x/2026-01-01-a",
                   "--date", "2026-01-01"])
        rc, out = self._run(["learn", "prune"])
        self.assertEqual(rc, 0)
        self.assertIn("stale candidates", out)
        self.assertIn("[old]", out)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_cli -v`
Expected: new tests FAIL — argparse exits with "invalid choice: 'learn'" (SystemExit 2 where 0 expected, or error before assertions).

- [ ] **Step 3: Implement in `akt/cli.py`**

Add the import:

```python
from akt import learn as learn_mod
```

In `build_parser()`, before `return p`:

```python
    plearn = sub.add_parser("learn", help="evidence ledger: add/reinforce/graduate/wont/list/prune")
    lsub = plearn.add_subparsers(dest="learn_cmd", required=True)

    la = lsub.add_parser("add", help="new candidate at hits 1")
    la.add_argument("id")
    la.add_argument("rule")
    la.add_argument("--story", required=True, help="<repo>/<date>-<slug>")
    la.add_argument("--date", default=None)

    lr = lsub.add_parser("reinforce", help="bump hits; prints PROPOSE: at threshold")
    lr.add_argument("id")
    lr.add_argument("--story", required=True)
    lr.add_argument("--date", default=None)

    lg = lsub.add_parser("graduate", help="promote; global scope also writes KB AGENTS.md")
    lg.add_argument("id")

    lw = lsub.add_parser("wont", help="mark wont-graduate; stops proposals")
    lw.add_argument("id")

    ll = lsub.add_parser("list", help="print the ledger")
    ll.add_argument("--status", default=None, choices=learn_mod.STATUSES)

    lsub.add_parser("prune", help="print-only staleness report")
```

In `main()`, before the final `return 1`:

```python
    if args.cmd == "learn":
        kb = _require_kb()
        _warn_if_dirty(kb)
        today = getattr(args, "date", None) or _date.today().isoformat()
        try:
            if args.learn_cmd == "add":
                entry = learn_mod.add(kb, args.id, args.rule, args.story, today)
                print(learn_mod.build_learning_line(entry))
                sys.stderr.write(gitkb.commit_kb(kb, "learn: add {}".format(args.id)) + "\n")
            elif args.learn_cmd == "reinforce":
                threshold = int(config.get("learn_threshold") or 3)
                entry, proposal = learn_mod.reinforce(kb, args.id, args.story, today, threshold)
                print(learn_mod.build_learning_line(entry))
                if proposal:
                    print(proposal)
                sys.stderr.write(gitkb.commit_kb(kb, "learn: reinforce {}".format(args.id)) + "\n")
            elif args.learn_cmd == "graduate":
                entry, block = learn_mod.graduate(kb, args.id)
                print(block)
                if entry["status"] == "graduated-repo":
                    print("(repo-local: append the block above to that repo's AGENTS.md/CLAUDE.md and commit it with the work)")
                sys.stderr.write(gitkb.commit_kb(kb, "learn: graduate {}".format(args.id)) + "\n")
            elif args.learn_cmd == "wont":
                entry = learn_mod.wont(kb, args.id)
                print(learn_mod.build_learning_line(entry))
                sys.stderr.write(gitkb.commit_kb(kb, "learn: wont-graduate {}".format(args.id)) + "\n")
            elif args.learn_cmd == "list":
                for entry in learn_mod.read_learnings(kb):
                    if args.status and entry["status"] != args.status:
                        continue
                    print(learn_mod.build_learning_line(entry))
            elif args.learn_cmd == "prune":
                cutoff = int(config.get("prune_days") or 90)
                stale_c, stale_g = learn_mod.prune_report(kb, today, cutoff)
                print("stale candidates (last reinforced > {} days ago):".format(cutoff))
                for entry in stale_c:
                    print("  " + learn_mod.build_learning_line(entry))
                print("graduated rules ripe for demotion review:")
                for entry in stale_g:
                    print("  " + learn_mod.build_learning_line(entry))
        except ValueError as err:
            sys.stderr.write(str(err) + "\n")
            sys.exit(2)
        return 0
```

(`prune` needs no `--date` flag; `today` falls back to the real date, which the test tolerates since the stale entry is dated 2026-01-01 via `add --date`.)

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_cli -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add akt/cli.py tests/test_cli.py
git commit -m "feat(akt): 'akt learn' CLI — atomic ledger ops with threshold proposals"
```

---

### Task 6: `akt install` wires the KB `AGENTS.md` import

**Files:**
- Modify: `akt/install.py`
- Test: `tests/test_install.py`

**Interfaces:**
- Consumes: existing `_ensure_import(claude_md)` and `install(home=None)`; `config.get("knowledge_base_path")`.
- Produces: `_ensure_import(claude_md, line)` (generalized to take the line); `install()` additionally ensures `@<kb>/AGENTS.md` when a KB is configured, and skips silently when not (graceful no-op).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_install.py` (match the file's existing fixture style — it already fakes `home`; use `AKT_CONFIG` pointing at a temp config, as `tests/test_cli.py` does):

```python
    def test_install_adds_kb_agents_import(self):
        import os
        cfg = Path(self.tmp.name) / "akt-config.md"
        os.environ["AKT_CONFIG"] = str(cfg)
        try:
            kb = Path(self.tmp.name) / "knowledge"
            config.set_value("knowledge_base_path", str(kb), cfg)
            install(home=self.home)
            before = (self.home / ".claude" / "CLAUDE.md").read_text()
            self.assertIn("@AKT.md", before)
            self.assertIn("@{}/AGENTS.md".format(kb), before)
            install(home=self.home)  # idempotent
            after = (self.home / ".claude" / "CLAUDE.md").read_text()
            self.assertEqual(before, after)
            self.assertEqual(after.count("@{}/AGENTS.md".format(kb)), 1)
        finally:
            os.environ.pop("AKT_CONFIG", None)

    def test_install_without_kb_skips_agents_import(self):
        import os
        os.environ["AKT_CONFIG"] = str(Path(self.tmp.name) / "missing-config.md")
        try:
            install(home=self.home)
            text = (self.home / ".claude" / "CLAUDE.md").read_text()
            self.assertIn("@AKT.md", text)
            self.assertNotIn("AGENTS.md", text)
        finally:
            os.environ.pop("AKT_CONFIG", None)
```

Add `from akt import config` to the test file's imports. Adjust `self.tmp` / `self.home` names to whatever the existing `setUp` uses — read the file first and keep its conventions.

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_install -v`
Expected: new tests FAIL (no KB AGENTS.md import written).

- [ ] **Step 3: Implement in `akt/install.py`**

Add `from akt import config` to the imports. Generalize `_ensure_import` to take the line:

```python
def _ensure_import(claude_md, line):
    text = claude_md.read_text() if claude_md.exists() else ""
    if line in [ln.strip() for ln in text.splitlines()]:
        return
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    prefix = text.rstrip("\n") + "\n" if text.strip() else ""
    claude_md.write_text(prefix + line + "\n")
    print("added {} import to {}".format(line, claude_md))
```

In `install()`, replace the `_ensure_import(home / ".claude" / "CLAUDE.md")` call with:

```python
    claude_md = home / ".claude" / "CLAUDE.md"
    _ensure_import(claude_md, IMPORT_LINE)
    kb = config.get("knowledge_base_path")
    if kb:
        # Graduated global rules auto-load in every session via this import.
        _ensure_import(claude_md, "@{}/AGENTS.md".format(kb))
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest tests.test_install -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add akt/install.py tests/test_install.py
git commit -m "feat(akt): install wires the KB AGENTS.md import — graduated rules auto-load"
```

---

### Task 7: Judgment layer — slash command + rule prompt updates

Prompt-only; no unit tests (Task 8 verifies end to end). The user's `~/.claude` copies are symlinks to these repo files, so editing the source is sufficient.

**Files:**
- Modify: `.claude/commands/finish-story.md`, `.claude/commands/update-story.md`
- Create: `.claude/commands/mine-learnings.md`
- Modify: `claude/akt-rule.md`

**Interfaces:**
- Consumes: the `akt learn` CLI (Task 5).
- Produces: prompts that drive the capture-time learnings pass and the bootstrap sweep.

- [ ] **Step 1: Add the learnings pass to `.claude/commands/finish-story.md`**

Append as step 4:

````markdown
4. **Learnings pass** — after the story commit:
   - Run `akt learn list --status candidate`.
   - For each transferable lesson in the story you just captured (a gotcha or
     decision that would help on a future task): if it matches an existing
     candidate — same lesson in different words counts — run
     `akt learn reinforce <id> --story <repo>/<date>-<slug>`; if it's new, run
     `akt learn add <kebab-id> "<rule as one instruction sentence, no '|'>" --story <repo>/<date>-<slug>`.
   - If any command printed a `PROPOSE:` line, relay it to the user verbatim
     and act on their answer: `akt learn graduate <id>` (for a REPO-LOCAL
     proposal, also append the printed rule block to *this* repo's
     `AGENTS.md`/`CLAUDE.md` and commit it with the work) or `akt learn wont <id>`.
   - Project-specific quirks with no transfer value get no entry. Skip the
     pass entirely if `akt` reports no ledger and no KB.
````

- [ ] **Step 2: Add the same pass to `.claude/commands/update-story.md`**

Append as step 3 (identical text to Step 1's block, renumbered).

- [ ] **Step 3: Create `.claude/commands/mine-learnings.md`**

````markdown
---
description: Sweep the knowledge base for recurring lessons and seed/refresh LEARNINGS.md
allowed-tools: Bash, Read
---

# Mine Learnings

Bootstrap or re-sweep the evidence ledger from the story corpus.

1. Resolve the KB path from `knowledge_base_path` in `~/.claude/akt-config.md`.
2. List every story, **oldest first** (dirs sort by date):
   ```bash
   ls -d <kb>/stories/*/*/ | sort -t/ -k+7
   ```
3. For each story, read `story.md` and extract transferable lessons — gotchas,
   decisions, and rules that would help on a future task ("would this help in
   another repo or task?"). Project-specific trivia gets no entry.
4. For each lesson, check the current ledger (`akt learn list`):
   - matches an existing entry (same lesson, any wording) →
     `akt learn reinforce <id> --story <repo>/<date>-<slug> --date <story date>`
   - new → `akt learn add <kebab-id> "<one instruction sentence, no '|'>" --story <repo>/<date>-<slug> --date <story date>`
5. **Batch proposals:** do NOT act on `PROPOSE:` lines mid-sweep. Collect them
   and present all of them to the user at the end; then run
   `akt learn graduate <id>` or `akt learn wont <id>` per their answers.
   For REPO-LOCAL graduations, tell the user the rule block will be added to
   that repo's `AGENTS.md` the next time work happens there (or paste it now
   if the repo is at hand).
````

- [ ] **Step 4: Update `claude/akt-rule.md`**

In the capture section ("When a meaningful chunk of work wraps up"), after item 2, add:

```markdown
3. Learnings pass: run `akt learn list --status candidate` and compare this story's transferable lessons — matches get `akt learn reinforce <id> --story <repo>/<date>-<slug>`, new ones get `akt learn add`. Relay any `PROPOSE:` line to the user verbatim and act on their answer (`akt learn graduate <id>` / `akt learn wont <id>`); a REPO-LOCAL graduation also means appending the printed rule block to this repo's `AGENTS.md`/`CLAUDE.md` and committing it with the work.
```

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/finish-story.md .claude/commands/update-story.md .claude/commands/mine-learnings.md claude/akt-rule.md
git commit -m "feat(akt): learnings pass in capture commands + /mine-learnings bootstrap"
```

---

### Task 8: End-to-end verification, docs, PR

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Full lifecycle against a temp KB**

```bash
export AKT_CONFIG="$(mktemp -d)/akt-config.md"
KB="$(mktemp -d)/knowledge"
python3 -m akt init "$KB"
git -C "$KB" init -q && git -C "$KB" add -A && git -C "$KB" commit -qm seed

python3 -m akt learn add cm6-paste "Verify live bundle bytes after CodeMirror-6 paste" --story heyflow/2026-07-01-a
python3 -m akt learn reinforce cm6-paste --story heyflow/2026-07-15-b
python3 -m akt learn reinforce cm6-paste --story sumo/2026-07-20-c
```

Expected: first two commands print the entry line and `knowledge base committed locally (no remote)` on stderr; the third also prints `PROPOSE: graduate 'cm6-paste' as GLOBAL (3 hits across 2 repos) — run: akt learn graduate cm6-paste`.

- [ ] **Step 2: Graduate and inspect**

```bash
python3 -m akt learn graduate cm6-paste
cat "$KB/AGENTS.md"
cat "$KB/LEARNINGS.md"
git -C "$KB" log --oneline
```

Expected: `AGENTS.md` ends with the rule block (rule line + `<!-- akt: cm6-paste | 3 hits | ... -->`); the ledger line shows `status: graduated-global`; git log shows one commit per mutating command (`learn: add ...`, `learn: reinforce ...` ×2, `learn: graduate ...`).

- [ ] **Step 3: wont, list, prune, error paths**

```bash
python3 -m akt learn add quirk "Some project quirk" --story heyflow/2026-01-01-x --date 2026-01-01
python3 -m akt learn wont quirk
python3 -m akt learn list --status wont-graduate
python3 -m akt learn prune
python3 -m akt learn graduate quirk; echo "exit: $?"
unset AKT_CONFIG
```

Expected: `list` shows only `[quirk]`; `prune` shows no stale candidates (quirk is wont, not candidate) and no stale graduated (cm6-paste is fresh); the final `graduate` prints `'quirk' is already wont-graduate` to stderr with `exit: 2`.

- [ ] **Step 4: Verify the install import**

```bash
akt install
grep AGENTS.md ~/.claude/CLAUDE.md
```

Expected: one `@<your-kb-path>/AGENTS.md` line (using the real configured KB). Run `akt install` again — no duplicate line, no output about it.

- [ ] **Step 5: Update `README.md`**

In "Status & roadmap": move the learning protocol from **Next** to **Shipped** with one line — `- Learning protocol — recurring lessons accrue evidence in LEARNINGS.md via a capture-time pass, and graduate (through a y/n gate, with provenance) into repo-local or global AGENTS.md rules that auto-load in every session; /mine-learnings bootstraps the ledger from existing stories.` Renumber the remaining **Next** items (planning/workflow toolkit, distribution). In the command reference section (wherever `finish-story`/`update-story` are documented), add an `akt learn` subsection listing the six subcommands with one line each, copied from the `--help` strings in Task 5. Add the design doc link `docs/superpowers/specs/2026-07-30-akt-learning-protocol-design.md` under "Design docs".

- [ ] **Step 6: Final full suite + PR**

```bash
python3 -m unittest discover -s tests -v
git add README.md
git commit -m "docs: learning protocol shipped — roadmap + akt learn reference"
git push -u origin feat/learning-protocol
gh pr create --title "feat: learning protocol — LEARNINGS.md ledger, akt learn CLI, graduation gate" \
  --body "Implements docs/superpowers/specs/2026-07-30-akt-learning-protocol-design.md: evidence ledger (LEARNINGS.md), akt learn add/reinforce/graduate/wont/list/prune with atomic KB commits and CLI-printed threshold proposals, capture-time learnings pass in finish-story/update-story, /mine-learnings bootstrap, and the KB AGENTS.md import wired by akt install."
```

Expected: all tests PASS; PR opens.

- [ ] **Step 7: Post-merge follow-ups (after the PR merges — note for the user, not automated)**

Run `/mine-learnings` once to seed the ledger from the ~30 existing stories, and re-run `akt install` so the `@<kb>/AGENTS.md` import lands in `~/.claude/CLAUDE.md`.

---

## Self-Review

**1. Spec coverage:**
- §1 data model (format, fields, derived scope, index.py idiom, atomic commits) → Tasks 3, 5.
- §2 CLI (six subcommands, threshold/config keys, proposal printed by CLI and repeated until resolved, graduate global writes AGENTS.md / repo-local prints only, no remove) → Tasks 4, 5.
- §3 judgment layer (learnings pass in finish/update, matching is the model's job, /mine-learnings oldest-first with batched proposals, AKT.md lines, no recall-time check) → Task 7; the "no recall-time check" non-goal requires no code.
- §4 rule delivery (install import idempotent + graceful no-op, rule block format with provenance comment, repo-local written by agent) → Tasks 4 (block format), 6 (import), 7 (agent instructions).
- §5 precursor (validation, tolerant dedupe, KB repair + reindex, separate PR first) → Tasks 1, 2.
- Error handling (loud failures exit 2, dirty-KB warning, graduate-twice error) → Tasks 4, 5.
- Testing section → mapped 1:1 onto Tasks 1, 3, 4, 5, 6; manual E2E → Task 8.

**2. Placeholder scan:** No TBDs; every code step has full content. Task 6's "adjust fixture names to the existing setUp" is a deliberate read-the-file instruction (the plan author verified `install(home=...)` exists but test fixture names must match the file on disk), not a placeholder — the test bodies are complete.

**3. Type/name consistency:** `build_learning_line`/`parse_learning_line`/`read_learnings`/`write_learnings`/`scope`/`rule_block`/`add`/`reinforce`/`graduate`/`wont`/`prune_report` are identical across Tasks 3–5. Entry dict keys (`id`, `rule`, `hits`, `status`, `last`, `stories`) match everywhere. `reinforce` returns `(entry, proposal|None)` and `graduate` returns `(entry, block)` in both definition (Task 4) and call sites (Task 5). Config keys `learn_threshold`/`prune_days` match the spec. `PROPOSE:` string format identical in Task 4 code, Task 5 test, and Task 8 expected output.
