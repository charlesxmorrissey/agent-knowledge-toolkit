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
