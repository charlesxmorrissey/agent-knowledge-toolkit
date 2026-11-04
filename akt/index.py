"""Build, parse, and maintain INDEX.md — the derived search cache."""
import os
import re
from pathlib import Path

from akt.frontmatter import parse_frontmatter, set_frontmatter_line, split_keys, tags_from_keys

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
    if body:
        _index_file(kb_path).write_text(_HEADER + "\n" + body + "\n")
    else:
        _index_file(kb_path).write_text(_HEADER)


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


def _sync_tags(story_md):
    """Write `tags` derived from `keys` when the two disagree (issue #66).
    A story whose tags are current is not rewritten, so its mtime and git
    history stay put (akt drift anchors on them). Returns True if written."""
    text = story_md.read_text()
    meta, _ = parse_frontmatter(text)
    want = tags_from_keys(meta.get("keys", ""))
    if want == meta.get("tags", "") or (not want and "tags" not in meta):
        return False
    st = story_md.stat()
    story_md.write_text(set_frontmatter_line(text, "tags", want))
    # A cache write, not an edit: keep the mtime `akt latest` ranks by.
    os.utime(story_md, ns=(st.st_atime_ns, st.st_mtime_ns))
    return True


def reindex(kb_path, with_tags=False):
    """Rebuild INDEX.md from every story.md, syncing each story's `tags`
    from its `keys` on the way. With `with_tags`, also return the
    KB-relative paths whose tags line was written."""
    kb_path = Path(kb_path)
    lines, tagged = [], []
    for story_md in (kb_path / "stories").glob("*/*/story.md"):
        if _sync_tags(story_md):
            tagged.append(str(story_md.relative_to(kb_path)))
        meta, _ = parse_frontmatter(story_md.read_text())
        if not meta.get("summary", "").strip():
            continue
        rel = str(story_md.relative_to(kb_path))
        lines.append(build_index_line(meta, rel))
    write_index(kb_path, lines)
    return (lines, sorted(tagged)) if with_tags else lines
