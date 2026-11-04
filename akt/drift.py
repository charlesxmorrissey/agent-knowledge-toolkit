"""Drift: which sibling repos moved past a story's last change (issue #61).

One story often holds the record for work that lands in several repos. A
session started in a sibling repo runs `akt latest <sibling>` and finds a
story that stopped days earlier, while the detail sits in the main story.
`drift` compares each sibling's latest story and git head against the main
story's last change and names the gap; `pointer` appends a short update to
each stale sibling story so the next session there finds the main story.
"""
import subprocess
from pathlib import Path

from akt.recall import _UPDATE, latest
from akt.frontmatter import parse_frontmatter
from akt.story import update_story


def _git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args],
                           capture_output=True, text=True)
        return r.returncode == 0, r.stdout.rstrip("\n")
    except (OSError, ValueError):
        return False, ""


def _story_md(kb_path, story_rel):
    p = Path(kb_path) / story_rel
    return p if p.name == "story.md" else p / "story.md"


def story_changed_at(kb_path, story_rel):
    """Epoch seconds of the knowledge base's last commit touching the story's
    story.md; file mtime when the KB is not a git repo or the file is not yet
    committed. `## Update` headings carry only a date, so the commit time is
    the clock that tells two same-day sessions apart."""
    f = _story_md(kb_path, story_rel)
    ok, out = _git(kb_path, "log", "-1", "--format=%ct", "--", str(f))
    if ok and out.strip().isdigit():
        return int(out.strip())
    try:
        return int(f.stat().st_mtime)
    except OSError:
        return 0


def repo_head(repo_dir):
    """{'sha', 'time', 'subject'} of HEAD in `repo_dir`, or None when the
    directory is missing or not a git repo."""
    repo_dir = Path(repo_dir)
    if not repo_dir.is_dir():
        return None
    ok, out = _git(repo_dir, "log", "-1", "--format=%h%x00%ct%x00%s")
    if not ok or not out:
        return None
    sha, ts, subject = out.split("\x00", 2)
    return {"sha": sha, "time": int(ts), "subject": subject}


def last_update(kb_path, story_rel):
    """(date, first line) of the story's newest `## Update`, or None."""
    f = _story_md(kb_path, story_rel)
    try:
        _, body = parse_frontmatter(f.read_text())
    except OSError:
        return None
    parts = _UPDATE.split(body)
    if len(parts) < 3:
        return None
    date, text = parts[-2], parts[-1]
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return date, first


def drift(kb_path, main_story_rel, repos, root):
    """One row per sibling repo: its latest story (with last-update line and
    change time), its git head, and flags against the main story's anchor.

    'newer': the sibling's story or head postdates the anchor (read it at resume).
    'stale': the sibling's story predates the anchor (pointer it at wrap).
    Both can hold at once: that is the case the issue describes."""
    anchor = story_changed_at(kb_path, main_story_rel)
    rows = []
    for repo in repos:
        entry = latest(kb_path, repo)
        story = None
        if entry:
            rel = entry["path"]
            story = {
                "path": rel,
                "changed": story_changed_at(kb_path, rel),
                "update": last_update(kb_path, rel),
            }
        head = repo_head(Path(root) / repo)
        flags = []
        if (story and story["changed"] > anchor) or (head and head["time"] > anchor):
            flags.append("newer")
        if story and story["changed"] < anchor:
            flags.append("stale")
        rows.append({"repo": repo, "story": story, "head": head,
                     "flags": flags, "anchor": anchor})
    return rows


# The main story is a relative markdown link from the sibling story's
# directory (stories/<repo>/<slug>/ -> ../../<main_repo>/<main_slug>/story.md)
# so it resolves in Obsidian, on GitHub, and in any editor; the KB path stays
# as the link text so the dedupe check in pointer() still matches (issue #66).
_POINTER = (
    "{date} pointer. Work on this repo since {since} is recorded in the main "
    "story, [{main}]({href}); read its updates from that date on. Appended by "
    "`akt drift --pointer`."
)


def _link_href(main):
    """Relative path from any stories/<repo>/<slug>/ dir to main's story.md."""
    parts = main.split("/")
    if parts and parts[0] == "stories":
        parts = parts[1:]
    return "../../" + "/".join(parts) + "/story.md"


def pointer(kb_path, main_story_rel, rows, date):
    """Append the templated pointer update to every stale row's story.
    Returns the KB-relative story.md paths written. Does not commit."""
    main = main_story_rel.rstrip("/")
    if main.endswith("/story.md"):
        main = main[: -len("/story.md")]
    written = []
    for row in rows:
        if "stale" not in row["flags"] or not row["story"]:
            continue
        rel = row["story"]["path"]
        upd = row["story"]["update"]
        if upd and main in upd[1]:
            continue  # its newest update already points here; do not stack pointers
        story_dir = (Path(kb_path) / rel).parent
        since = story_dir.name[:10]
        update_story(story_dir, _POINTER.format(date=date, since=since, main=main,
                                                 href=_link_href(main)), date)
        written.append(rel)
    return written
