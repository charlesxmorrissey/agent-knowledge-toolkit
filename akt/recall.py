"""Recall: rank INDEX.md entries against a free-text query.

This is the single seam behind which retrieval lives: query -> ranked story paths.
Today it is keyword overlap; it can later become vector search without changing
callers or artifacts.
"""
import re
from pathlib import Path

from akt.frontmatter import parse_frontmatter, split_keys
from akt.index import read_index_lines, parse_index_line
from akt.paths import rel_to_kb

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


def latest(kb_path, repo):
    """Most recently ACTIVE story entry for a repo, or None.

    Ranked by story.md mtime so an update-story append counts as recency —
    lexical path order alone picks the wrong story when two share a date
    prefix (issues #24/#25). Path is the tiebreak.
    # ponytail: mtime, not git commit time — a fresh clone flattens mtimes
    # and degrades to path order; switch to git log -1 --format=%ct if that bites.
    """
    entries = {
        e["path"]: e
        for e in (parse_index_line(ln) for ln in read_index_lines(kb_path))
        if e and e["repo"] == repo
    }
    # start-story never indexes (only finish-story does), so an open story is
    # absent from INDEX.md and resume landed on a stale one (issues #35/#37).
    # Union the on-disk stories for this repo; the index entry wins when both exist.
    for f in (Path(kb_path) / "stories" / repo).glob("*/story.md"):
        rel = rel_to_kb(kb_path, f)
        if rel not in entries:
            meta, _ = parse_frontmatter(f.read_text())
            entries[rel] = {
                "repo": repo,
                "slug": meta.get("slug", ""),
                "summary": meta.get("summary", ""),
                "keys": split_keys(meta.get("keys", "")),
                "path": rel,
            }
    entries = list(entries.values())

    def activity(entry):
        f = Path(kb_path) / entry["path"]
        try:
            return (f.stat().st_mtime, entry["path"])
        except OSError:
            return (0.0, entry["path"])

    return max(entries, key=activity) if entries else None


_UPDATE = re.compile(r"^## Update — (\d{4}-\d{2}-\d{2})[ \t]*$", re.M)


def digest(kb_path, since):
    """Stories across all repos with activity on/after `since` (ISO date), newest first.

    Activity = the story's date (frontmatter, else the dir-name prefix) or any
    `## Update — YYYY-MM-DD` heading. Scans story.md files, not INDEX.md, so
    open stories count. Each entry carries `updates`: [(date, first line)]
    for the qualifying updates.
    """
    out = []
    for f in (Path(kb_path) / "stories").glob("*/*/story.md"):
        meta, body = parse_frontmatter(f.read_text())
        created = meta.get("date", "") or f.parent.name[:10]
        parts = _UPDATE.split(body)  # [pre, date1, text1, date2, text2, ...]
        updates = []
        for d, text in zip(parts[1::2], parts[2::2]):
            if d >= since:
                first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
                updates.append((d, first))
        dates = [d for d, _ in updates]
        if created >= since:
            dates.append(created)
        if not dates:
            continue
        out.append({
            "repo": meta.get("repo", "") or f.parent.parent.name,
            "slug": meta.get("slug", ""),
            "summary": meta.get("summary", ""),
            "keys": split_keys(meta.get("keys", "")),
            "path": rel_to_kb(kb_path, f),
            "active": max(dates),
            "updates": updates,
        })
    out.sort(key=lambda e: (e["active"], e["path"]), reverse=True)
    return out


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
