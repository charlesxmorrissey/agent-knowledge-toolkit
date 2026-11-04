"""Build, parse, and maintain INDEX.md — the derived search cache."""
import os
import re
from pathlib import Path

from akt.frontmatter import parse_frontmatter, quote_value, set_frontmatter_line, split_keys, tags_from_keys

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


def _sync_frontmatter(story_md):
    """Repair the frontmatter lines a YAML reader depends on: `tags` derived
    from `keys` (issue #66) and a `summary` quoted where YAML needs it. A
    story that is already right is not rewritten, so its mtime and git
    history stay put (akt drift anchors on them). Returns True if written."""
    text = story_md.read_text()
    meta, _ = parse_frontmatter(text)
    new = text
    tags = tags_from_keys(meta.get("keys", ""))
    if tags or "tags" in meta:
        new = set_frontmatter_line(new, "tags", tags)
    if meta.get("summary", "").strip():
        new = set_frontmatter_line(new, "summary", quote_value(meta["summary"]))
    if new == text:
        return False
    st = story_md.stat()
    story_md.write_text(new)
    # A cache write, not an edit: keep the mtime `akt latest` ranks by.
    os.utime(story_md, ns=(st.st_atime_ns, st.st_mtime_ns))
    return True


def reindex(kb_path, with_written=False):
    """Rebuild INDEX.md from every story.md, repairing each story's `tags`
    and `summary` frontmatter lines on the way. With `with_written`, also
    return the KB-relative paths whose frontmatter was rewritten."""
    kb_path = Path(kb_path)
    lines, written = [], []
    for story_md in (kb_path / "stories").glob("*/*/story.md"):
        if _sync_frontmatter(story_md):
            written.append(str(story_md.relative_to(kb_path)))
        meta, _ = parse_frontmatter(story_md.read_text())
        if not meta.get("summary", "").strip():
            continue
        rel = str(story_md.relative_to(kb_path))
        lines.append(build_index_line(meta, rel))
    write_index(kb_path, lines)
    return (lines, sorted(written)) if with_written else lines
