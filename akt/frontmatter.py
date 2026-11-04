"""Parse and build the minimal frontmatter used by story.md files."""
import re

# Obsidian tag characters: letters, digits, underscore, hyphen, slash. A tag
# ends at a space, and a purely numeric tag is not a tag (issue #66).
_TAG_DROP = re.compile(r"[^A-Za-z0-9_/-]")


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


def tags_from_keys(keys_value):
    """Shape a comma-separated keys string into an Obsidian-safe `tags` value.
    `keys` stays the source of truth; this is a derived, lossy copy."""
    tags = []
    for key in split_keys(keys_value or ""):
        tag = _TAG_DROP.sub("", "-".join(key.split()))
        if tag and not tag.isdigit() and tag not in tags:
            tags.append(tag)
    return ", ".join(tags)


def set_frontmatter_line(text, key, value):
    """Return `text` with `key: value` replaced in its leading '---' block, or
    inserted after the `keys:` line (else last). Everything else is kept
    byte-for-byte, so a backfill never rewrites what it did not touch."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    new = "{}: {}\n".format(key, value)
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return text
    for i in range(1, end):
        if lines[i].partition(":")[0].strip() == key:
            lines[i] = new
            return "".join(lines)
    at = next((i + 1 for i in range(1, end) if lines[i].partition(":")[0].strip() == "keys"), end)
    lines.insert(at, new)
    return "".join(lines)
