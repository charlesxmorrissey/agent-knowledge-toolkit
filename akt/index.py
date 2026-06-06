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
    if body:
        _index_file(kb_path).write_text(_HEADER + "\n" + body + "\n")
    else:
        _index_file(kb_path).write_text(_HEADER)


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
        if not meta.get("summary", "").strip():
            continue
        rel = str(story_md.relative_to(kb_path))
        lines.append(build_index_line(meta, rel))
    write_index(kb_path, lines)
    return lines
