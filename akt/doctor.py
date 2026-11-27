"""`akt doctor`: one line per check of the install and the knowledge base (issue #81).

Read-only. Each check is `ok` or says what is wrong and the command that fixes
it. Problems used to be found by accident: a knowledge base `.git` of 87 MB for
2.6 MB of stories went unseen until someone ran `du` for another reason.
"""
from pathlib import Path

from akt import config, gitkb
from akt import index as index_mod
from akt import learn as learn_mod
from akt import story as story_mod
from akt.frontmatter import parse_frontmatter
from akt.install import IMPORT_LINE, REPO_ROOT

# Loose objects above this size get a `git gc` hint. The tool commits on every
# operation and nothing packs the objects, so the number only grows: a real
# knowledge base reached 87 MB before anyone saw it, and grew 8.8 MB in the day
# after a `git gc`. 50 MB is about a week of heavy use, so the hint is rare.
LOOSE_LIMIT_KIB = 50 * 1024


def _ok(text):
    return (True, text, None)


def _fail(text, fix=None):
    return (False, text, fix)


def _check_config(cfg_path):
    """(result, kb): kb is None when the later knowledge base checks cannot run."""
    if not cfg_path.exists():
        return _fail("config: {} does not exist".format(cfg_path), "akt init <path>"), None
    kb = config.get("knowledge_base_path", cfg_path)
    if not kb:
        return _fail("config: no knowledge_base_path in {}".format(cfg_path),
                     "akt init <path>"), None
    if not Path(kb).is_dir():
        return _fail("config: knowledge_base_path {} is not a directory".format(kb),
                     "akt init <path>"), None
    if not gitkb.is_repo(kb):
        return _fail("config: knowledge base {} is not a git repo".format(kb),
                     "git -C {} init".format(kb)), Path(kb)
    return _ok("config: knowledge base at {}".format(kb)), Path(kb)


def _expected_links(home, toolkit):
    links = [(toolkit / "bin" / "akt", home / ".local" / "bin" / "akt"),
             (toolkit / "claude" / "akt-rule.md", home / ".claude" / "AKT.md")]
    for cmd in sorted((toolkit / ".claude" / "commands").glob("*.md")):
        links.append((cmd, home / ".claude" / "commands" / cmd.name))
    return links


def _check_links(home, toolkit):
    links = _expected_links(home, toolkit)
    bad = []
    for source, dest in links:
        if not dest.is_symlink():
            bad.append("{} is {}".format(
                dest, "not a symlink" if dest.exists() else "missing"))
        elif dest.resolve() != source.resolve():
            bad.append("{} points at {}".format(dest, dest.resolve()))
    if bad:
        return [_fail("install: " + b, "akt install") for b in bad]
    return [_ok("install: {} links resolve into {}".format(len(links), toolkit))]


def _check_toolkit_branch(toolkit):
    ok, branch = gitkb._git(toolkit, "rev-parse", "--abbrev-ref", "HEAD")
    if not ok or not branch:
        return _ok("toolkit: {} is not a git repo, so no branch to check".format(toolkit))
    if branch != "main":
        return _fail("toolkit: {} has '{}' checked out, and the installed akt runs "
                     "whatever is checked out".format(toolkit, branch),
                     "git -C {} checkout main".format(toolkit))
    return _ok("toolkit: on main")


def _check_imports(home, kb):
    claude_md = home / ".claude" / "CLAUDE.md"
    have = [ln.strip() for ln in claude_md.read_text().splitlines()] \
        if claude_md.exists() else []
    wanted = [IMPORT_LINE] + (["@{}/AGENTS.md".format(kb)] if kb else [])
    missing = [w for w in wanted if w not in have]
    if missing:
        return _fail("imports: {} lacks {}".format(claude_md, ", ".join(missing)),
                     "akt install")
    return _ok("imports: {} has {}".format(claude_md, ", ".join(wanted)))


def _check_clean(kb):
    # An untracked open story is the normal mid-story state (issue #45).
    unsaved = [path for code, path in gitkb.status_entries(kb)
               if not (code == "??" and story_mod.is_open_story(kb, path))]
    if unsaved:
        return _fail("knowledge base: {} uncommitted path(s), first: {}".format(
            len(unsaved), unsaved[0]), "/finish-story, or commit in {}".format(kb))
    return _ok("knowledge base: no uncommitted changes")


def _check_pushed(kb):
    ok, count = gitkb._git(kb, "rev-list", "--count", "@{u}..HEAD")
    if not ok:
        return _ok("knowledge base: no upstream branch, so nothing to push")
    if count.strip() not in ("", "0"):
        return _fail("knowledge base: {} commit(s) not pushed".format(count.strip()),
                     "git -C {} push".format(kb))
    return _ok("knowledge base: every commit is pushed")


def _check_loose(kb):
    ok, out = gitkb._git(kb, "count-objects", "-v")
    stats = dict(ln.split(": ", 1) for ln in out.splitlines() if ": " in ln) if ok else {}
    try:
        count, size = int(stats["count"]), int(stats["size"])
    except (KeyError, ValueError):
        return _ok("git objects: could not be counted")
    text = "git objects: {} loose, {:.1f} MB".format(count, size / 1024)
    if size >= LOOSE_LIMIT_KIB:
        return _fail(text, "git -C {} gc".format(kb))
    return _ok(text)


def _check_index(kb):
    indexed = {index_mod._line_path(ln) for ln in index_mod.read_index_lines(kb)}
    finished = set()
    for story_md in sorted(Path(kb).glob("stories/*/*/story.md")):
        meta, _ = parse_frontmatter(story_md.read_text())
        if meta.get("summary", "").strip():  # an open story has no index line yet
            finished.add(story_md.relative_to(kb).as_posix())
    missing, gone = sorted(finished - indexed), sorted(p for p in indexed - finished
                                                       if p and not (Path(kb) / p).exists())
    if missing or gone:
        parts = []
        if missing:
            parts.append("{} finished story(ies) with no index line, first: {}".format(
                len(missing), missing[0]))
        if gone:
            parts.append("{} index line(s) for a story that is not on disk, first: {}".format(
                len(gone), gone[0]))
        return _fail("index: " + "; ".join(parts), "akt reindex")
    return _ok("index: {} finished stories, each with an index line".format(len(finished)))


def _check_ledger(kb):
    try:
        entries = learn_mod.read_learnings(kb)
    except ValueError as err:
        return _fail("ledger: {}".format(err),
                     "repair the line in {}".format(Path(kb) / learn_mod.LEARNINGS_FILE))
    return _ok("ledger: {} entries, every line parses".format(len(entries)))


def _check_agents_size(kb):
    agents = Path(kb) / learn_mod.AGENTS_FILE
    size = agents.stat().st_size if agents.exists() else 0
    # No limit yet: the number is printed so growth is seen, not judged.
    return _ok("rules: AGENTS.md is {:.1f} KB, loaded in every session".format(size / 1024))


def run(home=None, cfg_path=None, toolkit=None):
    """Every check, in order, as (ok, text, fix) tuples. Changes nothing."""
    home = Path(home) if home else Path.home()
    cfg_path = Path(cfg_path) if cfg_path else config.config_path()
    toolkit = Path(toolkit) if toolkit else REPO_ROOT
    cfg_result, kb = _check_config(cfg_path)
    results = [cfg_result]
    results += _check_links(home, toolkit)
    results.append(_check_toolkit_branch(toolkit))
    # The raw config string: `akt install` writes the import from it as typed.
    results.append(_check_imports(home, config.get("knowledge_base_path", cfg_path)))
    if kb is not None:
        if gitkb.is_repo(kb):
            results += [_check_clean(kb), _check_pushed(kb), _check_loose(kb)]
        results += [_check_index(kb), _check_ledger(kb), _check_agents_size(kb)]
    return results


def format_line(result):
    ok, text, fix = result
    if ok:
        return "ok    " + text
    return "FAIL  " + text + (" (fix: {})".format(fix) if fix else "")
